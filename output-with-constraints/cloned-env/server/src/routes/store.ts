import { Router, Request, Response } from 'express';
import db from '../lib/db';
import { authMiddleware, AuthRequest } from '../lib/auth';

const router = Router();

// GET /api/v3/store/inventory - Returns pet inventories by status (NO AUTH per spec)
router.get('/inventory', (req: Request, res: Response) => {
  try {
    const inventory = db.prepare(`
      SELECT status, COUNT(*) as count 
      FROM pets 
      GROUP BY status
    `).all() as any[];

    const result: Record<string, number> = {};
    inventory.forEach(item => {
      result[item.status] = item.count;
    });

    // API spec expects object with additionalProperties integer, not wrapped in data
    res.json(result);
  } catch (error) {
    console.error('Get inventory error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// GET /api/v3/store/order/{orderId} - Find order by ID (NO AUTH per spec)
router.get('/order/:orderId', (req: Request, res: Response) => {
  try {
    const orderId = parseInt(req.params.orderId);
    if (isNaN(orderId)) {
      return res.status(400).json({ error: 'Invalid order ID' });
    }

    const order = db.prepare(`
      SELECT * FROM orders WHERE id = ?
    `).get(orderId) as any;

    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    const result = {
      id: order.id,
      petId: order.pet_id,
      quantity: order.quantity,
      shipDate: order.ship_date,
      status: order.status,
      complete: Boolean(order.complete)
    };

    // API spec expects order object directly, not wrapped in data
    res.json(result);
  } catch (error) {
    console.error('Get order error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// POST /api/v3/store/order - Place order (NO AUTH per spec)
router.post('/order', (req: Request, res: Response) => {
  try {
    const { petId, quantity, shipDate, status } = req.body;

    if (!petId) {
      return res.status(400).json({ error: 'Pet ID is required' });
    }

    // Check if pet exists
    const pet = db.prepare('SELECT status FROM pets WHERE id = ?').get(petId) as any;
    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // Insert order (without user_id since no auth)
    const insertOrder = db.prepare(`
      INSERT INTO orders (pet_id, user_id, quantity, ship_date, status, complete) 
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    const result = insertOrder.run(
      petId,
      1, // Default user_id since we don't have auth context
      quantity || 1,
      shipDate,
      status || 'placed',
      0
    );

    const orderId = result.lastInsertRowid;

    const newOrder = {
      id: orderId,
      petId: petId,
      quantity: quantity || 1,
      shipDate: shipDate,
      status: status || 'placed',
      complete: false
    };

    // API spec expects order object directly, not wrapped in data
    res.status(201).json(newOrder);
  } catch (error) {
    console.error('Create order error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// DELETE /api/v3/store/order/{orderId} - Delete order (NO AUTH per spec)
router.delete('/order/:orderId', (req: Request, res: Response) => {
  try {
    const orderId = parseInt(req.params.orderId);
    if (isNaN(orderId)) {
      return res.status(400).json({ error: 'Invalid order ID' });
    }

    const result = db.prepare('DELETE FROM orders WHERE id = ?').run(orderId);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // No response body expected for this endpoint
    res.status(200).send();
  } catch (error) {
    console.error('Delete order error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

export default router;