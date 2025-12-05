import express from 'express';
import db from '../lib/db';
import { authenticateToken, requireRoles, checkOwnership, AuthRequest } from '../lib/auth';

const router = express.Router();

// GET /api/v3/store/inventory
router.get('/inventory', authenticateToken, (req: AuthRequest, res) => {
  try {
    const inventory = db.prepare(`
      SELECT 
        status,
        COUNT(*) as count
      FROM pets
      GROUP BY status
    `).all();

    const result: { [key: string]: number } = {
      available: 0,
      pending: 0,
      sold: 0
    };

    inventory.forEach((item: any) => {
      result[item.status] = item.count;
    });

    res.json({ data: result });
  } catch (error) {
    console.error('Get inventory error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/store/order
router.post('/order', authenticateToken, requireRoles(['customer', 'store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const { petId, quantity, shipDate, status, complete } = req.body;

    if (!petId) {
      return res.status(400).json({ error: 'Pet ID is required' });
    }

    // Validation: quantity must be 1
    if (quantity !== undefined && quantity !== 1) {
      return res.status(400).json({ error: 'Quantity must be 1 for live animals' });
    }

    // Check if pet exists and is available
    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);
    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    if ((pet as any).status !== 'available') {
      return res.status(400).json({ error: 'Pet is not available for purchase' });
    }

    const transaction = db.transaction(() => {
      // Create order
      const insertOrder = db.prepare(`
        INSERT INTO orders (pet_id, user_id, quantity, ship_date, status, complete)
        VALUES (?, ?, ?, ?, ?, ?)
      `);

      const orderResult = insertOrder.run(
        petId,
        req.user!.id,
        quantity || 1,
        shipDate || null,
        status || 'placed',
        complete ? 1 : 0
      );

      // Update pet status to pending (state transition)
      db.prepare('UPDATE pets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
        .run('pending', petId);

      return orderResult.lastInsertRowid;
    });

    const orderId = transaction();

    // Get the created order
    const order = db.prepare(`
      SELECT id, pet_id, quantity, ship_date, status, complete, created_at
      FROM orders WHERE id = ?
    `).get(orderId);

    res.status(201).json({
      data: {
        id: (order as any).id,
        petId: (order as any).pet_id,
        quantity: (order as any).quantity,
        shipDate: (order as any).ship_date,
        status: (order as any).status,
        complete: (order as any).complete === 1
      }
    });
  } catch (error) {
    console.error('Create order error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/store/order/:orderId
router.get('/order/:orderId', authenticateToken, checkOwnership('order', 'user_id', ['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const orderId = parseInt(req.params.orderId);

    if (isNaN(orderId)) {
      return res.status(400).json({ error: 'Invalid order ID' });
    }

    const order = db.prepare(`
      SELECT id, pet_id, quantity, ship_date, status, complete, created_at
      FROM orders WHERE id = ?
    `).get(orderId);

    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    res.json({
      data: {
        id: (order as any).id,
        petId: (order as any).pet_id,
        quantity: (order as any).quantity,
        shipDate: (order as any).ship_date,
        status: (order as any).status,
        complete: (order as any).complete === 1
      }
    });
  } catch (error) {
    console.error('Get order error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/store/order/:orderId
router.delete('/order/:orderId', authenticateToken, checkOwnership('order', 'user_id', ['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const orderId = parseInt(req.params.orderId);

    if (isNaN(orderId)) {
      return res.status(400).json({ error: 'Invalid order ID' });
    }

    // Get order details before deletion
    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId);

    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Validation: can only cancel orders with 'placed' status
    if ((order as any).status !== 'placed') {
      return res.status(400).json({ error: 'Can only cancel orders with \'placed\' status' });
    }

    const transaction = db.transaction(() => {
      // Delete order
      const deleteResult = db.prepare('DELETE FROM orders WHERE id = ?').run(orderId);

      if (deleteResult.changes === 0) {
        throw new Error('Order not found');
      }

      // State transition: return pet to available status
      db.prepare('UPDATE pets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
        .run('available', (order as any).pet_id);
    });

    transaction();

    res.json({ data: { message: 'Order cancelled successfully' } });
  } catch (error) {
    console.error('Delete order error:', error);
    if ((error as Error).message === 'Order not found') {
      res.status(404).json({ error: 'Order not found' });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

export default router;