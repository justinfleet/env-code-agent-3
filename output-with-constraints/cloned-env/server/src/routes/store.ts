import { Router } from 'express';
import db from '../lib/db.js';
import { verifyAuth, requireRole, checkOwnership, AuthRequest } from '../lib/auth.js';

const router = Router();

// GET /api/v3/store/inventory
router.get('/inventory', verifyAuth, (req, res) => {
  try {
    const inventory = db.prepare(`
      SELECT 
        status,
        COUNT(*) as count
      FROM pets 
      GROUP BY status
    `).all() as any[];

    const response: { [key: string]: number } = {
      available: 0,
      pending: 0,
      sold: 0
    };

    inventory.forEach(item => {
      response[item.status] = item.count;
    });

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/store/order
router.post('/order', verifyAuth, requireRole(['customer', 'store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const { petId, quantity, shipDate, status, complete } = req.body;
    
    if (!petId) {
      return res.status(400).json({ error: 'Pet ID is required' });
    }

    // Validation: quantity must be 1
    if (quantity !== 1) {
      return res.status(400).json({ error: 'Quantity must be 1 for live animals' });
    }

    // Get pet and validate
    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId) as any;
    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // Validation: pet must be available
    if (pet.status !== 'available') {
      return res.status(400).json({ error: 'Pet is not available for purchase' });
    }

    // Pre-condition: check for existing active orders
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count 
      FROM orders 
      WHERE pet_id = ? AND status IN ('placed', 'approved')
    `).get(petId) as any;

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ error: 'Pet already has an active order' });
    }

    // Create order
    const insertOrder = db.prepare(`
      INSERT INTO orders (pet_id, user_id, quantity, ship_date, status, complete) 
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    const result = insertOrder.run(
      petId, 
      req.user!.user_id, 
      quantity || 1, 
      shipDate || null, 
      status || 'placed', 
      complete ? 1 : 0
    );
    const orderId = result.lastInsertRowid as number;

    // State transition: change pet status to pending
    db.prepare('UPDATE pets SET status = ? WHERE id = ?').run('pending', petId);

    // Return the created order
    const createdOrder = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    
    const response = {
      id: createdOrder.id,
      petId: createdOrder.pet_id,
      quantity: createdOrder.quantity,
      shipDate: createdOrder.ship_date,
      status: createdOrder.status,
      complete: createdOrder.complete === 1
    };

    res.status(201).json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/store/order/{orderId}
router.get('/order/:orderId', verifyAuth, checkOwnership('order', 'user_id', ['store_owner', 'admin']), (req, res) => {
  try {
    const orderId = parseInt(req.params.orderId);
    
    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    const response = {
      id: order.id,
      petId: order.pet_id,
      quantity: order.quantity,
      shipDate: order.ship_date,
      status: order.status,
      complete: order.complete === 1
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/v3/store/order/{orderId}
router.put('/order/:orderId', verifyAuth, (req: AuthRequest, res) => {
  try {
    const orderId = parseInt(req.params.orderId);
    const { status, shipDate, complete } = req.body;

    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Check ownership unless store_owner or admin
    if (!['store_owner', 'admin'].includes(req.user!.role)) {
      if (order.user_id !== req.user!.user_id) {
        return res.status(403).json({ error: 'Cannot access this order' });
      }
    }

    // Validation: cannot modify delivered orders
    if (order.status === 'delivered') {
      return res.status(400).json({ error: 'Delivered orders cannot be modified' });
    }

    // Special checks for status changes
    if (status === 'approved' || status === 'delivered') {
      if (!['store_owner', 'admin'].includes(req.user!.role)) {
        return res.status(403).json({ error: 'Only store staff can approve or deliver orders' });
      }
    }

    // Update order
    const updateOrder = db.prepare(`
      UPDATE orders 
      SET status = ?, ship_date = ?, complete = ?
      WHERE id = ?
    `);
    updateOrder.run(
      status || order.status,
      shipDate || order.ship_date,
      complete !== undefined ? (complete ? 1 : 0) : order.complete,
      orderId
    );

    // State transition: if status becomes 'delivered', mark pet as sold
    if (status === 'delivered') {
      db.prepare('UPDATE pets SET status = ? WHERE id = ?').run('sold', order.pet_id);
    }

    const updatedOrder = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    
    const response = {
      id: updatedOrder.id,
      petId: updatedOrder.pet_id,
      quantity: updatedOrder.quantity,
      shipDate: updatedOrder.ship_date,
      status: updatedOrder.status,
      complete: updatedOrder.complete === 1
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/store/order/{orderId}
router.delete('/order/:orderId', verifyAuth, checkOwnership('order', 'user_id', ['store_owner', 'admin']), (req, res) => {
  try {
    const orderId = parseInt(req.params.orderId);
    
    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Validation: can only cancel placed orders
    if (order.status !== 'placed') {
      return res.status(400).json({ error: 'Only placed orders can be cancelled' });
    }

    // Validation: cannot cancel delivered orders
    if (order.status === 'delivered') {
      return res.status(400).json({ error: 'Delivered orders cannot be cancelled' });
    }

    // State transition: return pet to available if order was placed
    if (order.status === 'placed') {
      db.prepare('UPDATE pets SET status = ? WHERE id = ?').run('available', order.pet_id);
    }

    const deleteOrder = db.prepare('DELETE FROM orders WHERE id = ?');
    deleteOrder.run(orderId);

    res.json({ message: 'Order deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;