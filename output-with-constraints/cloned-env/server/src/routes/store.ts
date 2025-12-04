import express, { Request, Response } from 'express';
import db from '../lib/db';
import { authenticateToken, requireRoles, checkOwnership, AuthenticatedRequest } from './auth';

const router = express.Router();

// GET /api/v3/store/inventory - Business requirements specify auth required
router.get('/inventory', authenticateToken, (req: AuthenticatedRequest, res: Response) => {
  try {
    const inventory = db.prepare(`
      SELECT 
        status,
        COUNT(*) as count
      FROM pets 
      GROUP BY status
    `).all();

    const result: any = {
      available: 0,
      pending: 0,
      sold: 0
    };

    inventory.forEach((item: any) => {
      result[item.status] = item.count;
    });

    res.json(result);

  } catch (error) {
    console.error('Error getting inventory:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/store/order
router.post('/order', authenticateToken, requireRoles(['customer', 'store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { petId, quantity, shipDate, status, complete } = req.body;

    if (!petId) {
      return res.status(400).json({ message: 'Pet ID is required' });
    }

    // Get the pet to validate
    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);
    if (!pet) {
      return res.status(400).json({ message: 'Pet not found' });
    }

    // Validation: Pet must be available (exact message from business requirements)
    if (pet.status !== 'available') {
      return res.status(400).json({ message: 'Pet is not available for purchase' });
    }

    // Validation: Quantity must be exactly 1 (exact message from business requirements)
    if (quantity !== 1) {
      return res.status(400).json({ message: 'Quantity must be 1 for live animals' });
    }

    // Validation: Check for existing active orders for this pet (exact message from business requirements)
    const existingOrder = db.prepare(`
      SELECT COUNT(*) as count FROM orders 
      WHERE pet_id = ? AND status IN ('placed', 'approved')
    `).get(petId) as any;

    if (existingOrder.count > 0) {
      return res.status(400).json({ message: 'Pet already has an active order' });
    }

    const transaction = db.transaction(() => {
      // Create the order
      const insertOrder = db.prepare(`
        INSERT INTO orders (pet_id, user_id, quantity, ship_date, status, complete)
        VALUES (?, ?, ?, ?, ?, ?)
      `);
      
      const orderResult = insertOrder.run(
        petId,
        req.user!.user_id,
        quantity || 1,
        shipDate,
        status || 'placed',
        complete ? 1 : 0
      );

      // State transition: Change pet status to pending
      db.prepare('UPDATE pets SET status = ? WHERE id = ?').run('pending', petId);

      return orderResult.lastInsertRowid;
    });

    const orderId = transaction();

    // Return the created order
    const newOrder = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    
    const response = {
      id: newOrder.id,
      petId: newOrder.pet_id,
      quantity: newOrder.quantity,
      shipDate: newOrder.ship_date,
      status: newOrder.status,
      complete: newOrder.complete === 1
    };

    res.json(response);

  } catch (error) {
    console.error('Error creating order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/store/order/:orderId
router.get('/order/:orderId', authenticateToken, checkOwnership('order', 'user_id', ['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { orderId } = req.params;
    
    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Check ownership if not admin/store_owner
    if ((req as any).ownershipCheck && order.user_id !== req.user!.user_id) {
      return res.status(403).json({ error: 'You can only view your own orders' });
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
    console.error('Error getting order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/v3/store/order/:orderId (for status updates by store owner)
router.put('/order/:orderId', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { orderId } = req.params;
    const { status } = req.body;

    // Get current order
    const currentOrder = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    if (!currentOrder) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Pre-condition: Cannot modify delivered orders (exact message from business requirements)
    if (currentOrder.status === 'delivered') {
      return res.status(400).json({ message: 'Cannot modify delivered orders' });
    }

    const transaction = db.transaction(() => {
      // Update order status
      db.prepare('UPDATE orders SET status = ? WHERE id = ?').run(status, orderId);

      // State transition: If order is delivered, mark pet as sold
      if (status === 'delivered') {
        db.prepare('UPDATE pets SET status = ? WHERE id = ?').run('sold', currentOrder.pet_id);
      }
    });

    transaction();

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
    console.error('Error updating order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/store/order/:orderId
router.delete('/order/:orderId', authenticateToken, checkOwnership('order', 'user_id', ['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { orderId } = req.params;
    
    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId) as any;
    if (!order) {
      return res.status(404).json({ code: 404, type: 'error', message: 'Order not found' });
    }

    // Check ownership if not admin/store_owner
    if ((req as any).ownershipCheck && order.user_id !== req.user!.user_id) {
      return res.status(403).json({ code: 403, type: 'error', message: 'You can only cancel your own orders' });
    }

    // Validation: Can only cancel placed orders (exact message from business requirements)
    if (order.status !== 'placed') {
      return res.status(400).json({ 
        code: 400, 
        type: 'error', 
        message: 'Cannot cancel order that has been approved or delivered' 
      });
    }

    const transaction = db.transaction(() => {
      // Delete the order
      db.prepare('DELETE FROM orders WHERE id = ?').run(orderId);

      // State transition: Return pet to available if it was pending
      const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(order.pet_id) as any;
      if (pet && pet.status === 'pending') {
        db.prepare('UPDATE pets SET status = ? WHERE id = ?').run('available', order.pet_id);
      }
    });

    transaction();

    res.json({ code: 200, type: 'success', message: 'Order cancelled successfully' });

  } catch (error) {
    console.error('Error deleting order:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

export default router;