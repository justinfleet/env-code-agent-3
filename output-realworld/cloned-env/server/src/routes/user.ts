import { Router, Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import db from '../lib/db';

const router = Router();
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

// Middleware to authenticate user
function authenticateToken(req: any, res: Response, next: any) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, JWT_SECRET, (err: any, user: any) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid token' });
    }
    req.user = user;
    next();
  });
}

// Helper to get user by id
function getUserById(id: number) {
  return db.prepare('SELECT * FROM users WHERE id = ?').get(id) as any;
}

// Helper to format user response
function formatUser(user: any, token?: string) {
  return {
    email: user.email,
    token: token || jwt.sign({ userId: user.id }, JWT_SECRET, { expiresIn: '30d' }),
    username: user.username,
    bio: user.bio || '',
    image: user.image || ''
  };
}

// GET /api/user - Get current user
router.get('/', authenticateToken, (req: any, res: Response) => {
  try {
    const user = getUserById(req.user.userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    res.json({ user: formatUser(user) });
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/user - Update user
router.put('/', authenticateToken, async (req: any, res: Response) => {
  try {
    const { user: updateData } = req.body;
    const userId = req.user.userId;

    const currentUser = getUserById(userId);
    if (!currentUser) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Build update query dynamically
    const updates: string[] = [];
    const values: any[] = [];

    if (updateData.email) {
      // Check if email is already taken by another user
      const existingUser = db.prepare('SELECT id FROM users WHERE email = ? AND id != ?').get(updateData.email, userId);
      if (existingUser) {
        return res.status(422).json({ 
          errors: { body: ['email already taken'] } 
        });
      }
      updates.push('email = ?');
      values.push(updateData.email);
    }

    if (updateData.username) {
      // Check if username is already taken by another user
      const existingUser = db.prepare('SELECT id FROM users WHERE username = ? AND id != ?').get(updateData.username, userId);
      if (existingUser) {
        return res.status(422).json({ 
          errors: { body: ['username already taken'] } 
        });
      }
      updates.push('username = ?');
      values.push(updateData.username);
    }

    if (updateData.password) {
      const passwordHash = await bcrypt.hash(updateData.password, 10);
      updates.push('password_hash = ?');
      values.push(passwordHash);
    }

    if (updateData.bio !== undefined) {
      updates.push('bio = ?');
      values.push(updateData.bio);
    }

    if (updateData.image !== undefined) {
      updates.push('image = ?');
      values.push(updateData.image);
    }

    if (updates.length > 0) {
      updates.push('updated_at = CURRENT_TIMESTAMP');
      values.push(userId);

      const query = `UPDATE users SET ${updates.join(', ')} WHERE id = ?`;
      db.prepare(query).run(...values);
    }

    const updatedUser = getUserById(userId);
    res.json({ user: formatUser(updatedUser) });
  } catch (error) {
    console.error('Update user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;