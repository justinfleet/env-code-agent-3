import express, { Request, Response } from 'express';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import db from '../lib/db';
import { authenticateToken, requireRoles, checkOwnership, AuthenticatedRequest } from './auth';

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

// POST /api/v3/user - Create user (register)
router.post('/', (req: Request, res: Response) => {
  try {
    const { username, firstName, lastName, email, password, phone, userStatus } = req.body;

    if (!username || !password) {
      return res.status(400).json({ code: 400, type: 'error', message: 'Username and password are required' });
    }

    // Check if username already exists
    const existingUser = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
    if (existingUser) {
      return res.status(400).json({ code: 400, type: 'error', message: 'Username already exists' });
    }

    // Check if email already exists
    if (email) {
      const existingEmail = db.prepare('SELECT id FROM users WHERE email = ?').get(email);
      if (existingEmail) {
        return res.status(400).json({ code: 400, type: 'error', message: 'Email already exists' });
      }
    }

    // Hash password
    const saltRounds = 10;
    const hashedPassword = bcrypt.hashSync(password, saltRounds);

    // Insert user
    const insertUser = db.prepare(`
      INSERT INTO users (username, first_name, last_name, email, password, phone, user_status, role)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    insertUser.run(
      username,
      firstName || null,
      lastName || null,
      email || null,
      hashedPassword,
      phone || null,
      userStatus || 0,
      'customer' // Default role
    );

    res.json({ code: 200, type: 'success', message: 'User created successfully' });

  } catch (error) {
    console.error('Error creating user:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

// POST /api/v3/user/createWithList
router.post('/createWithList', (req: Request, res: Response) => {
  try {
    const { users } = req.body;

    if (!users || !Array.isArray(users)) {
      return res.status(400).json({ code: 400, type: 'error', message: 'Users array is required' });
    }

    const transaction = db.transaction(() => {
      const insertUser = db.prepare(`
        INSERT INTO users (username, first_name, last_name, email, password, phone, user_status, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `);

      for (const user of users) {
        if (user.username && user.password) {
          // Check for duplicates
          const existing = db.prepare('SELECT id FROM users WHERE username = ?').get(user.username);
          if (!existing) {
            const hashedPassword = bcrypt.hashSync(user.password, 10);
            insertUser.run(
              user.username,
              user.firstName || null,
              user.lastName || null,
              user.email || null,
              hashedPassword,
              user.phone || null,
              user.userStatus || 0,
              'customer'
            );
          }
        }
      }
    });

    transaction();

    res.json({ code: 200, type: 'success', message: 'Users created successfully' });

  } catch (error) {
    console.error('Error creating users:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

// GET /api/v3/user/login
router.get('/login', (req: Request, res: Response) => {
  try {
    const { username, password } = req.query;

    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username as string) as any;
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const isValidPassword = bcrypt.compareSync(password as string, user.password);
    if (!isValidPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Generate JWT token
    const tokenPayload = {
      user_id: user.id,
      username: user.username,
      role: user.role
    };

    const token = jwt.sign(tokenPayload, JWT_SECRET, { expiresIn: '24h' });
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

    res.json({
      token,
      expires: expiresAt
    });

  } catch (error) {
    console.error('Error during login:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/user/logout
router.get('/logout', authenticateToken, (req: AuthenticatedRequest, res: Response) => {
  try {
    // In a real implementation, you might maintain a blacklist of tokens
    // For this demo, we'll just return success
    res.json({ code: 200, type: 'success', message: 'Logged out successfully' });
  } catch (error) {
    console.error('Error during logout:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

// GET /api/v3/user/:username - Business requirements specify auth required with ownership check
router.get('/:username', authenticateToken, checkOwnership('user', 'username', ['admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { username } = req.params;
    
    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Check ownership if not admin
    if ((req as any).ownershipCheck && user.username !== req.user!.username) {
      return res.status(403).json({ error: 'You can only view your own profile' });
    }

    const response = {
      id: user.id,
      username: user.username,
      firstName: user.first_name,
      lastName: user.last_name,
      email: user.email,
      password: user.password, // Note: In production, never return passwords
      phone: user.phone,
      userStatus: user.user_status
    };

    res.json(response);

  } catch (error) {
    console.error('Error getting user:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/v3/user/:username
router.put('/:username', authenticateToken, checkOwnership('user', 'username', ['admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { username } = req.params;
    const { firstName, lastName, email, password, phone, userStatus, role } = req.body;
    
    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ code: 404, type: 'error', message: 'User not found' });
    }

    // Check ownership if not admin
    if ((req as any).ownershipCheck && user.username !== req.user!.username) {
      return res.status(403).json({ code: 403, type: 'error', message: 'You can only edit your own profile' });
    }

    // Special check: Only admin can change roles
    if (role && role !== user.role && req.user!.role !== 'admin') {
      return res.status(403).json({ 
        code: 403, 
        type: 'error', 
        message: 'Only admin can change user roles' 
      });
    }

    // Hash password if provided
    let hashedPassword = user.password;
    if (password) {
      hashedPassword = bcrypt.hashSync(password, 10);
    }

    // Update user
    const updateUser = db.prepare(`
      UPDATE users 
      SET first_name = ?, last_name = ?, email = ?, password = ?, phone = ?, user_status = ?, role = ?
      WHERE username = ?
    `);

    updateUser.run(
      firstName !== undefined ? firstName : user.first_name,
      lastName !== undefined ? lastName : user.last_name,
      email !== undefined ? email : user.email,
      hashedPassword,
      phone !== undefined ? phone : user.phone,
      userStatus !== undefined ? userStatus : user.user_status,
      role !== undefined ? role : user.role,
      username
    );

    res.json({ code: 200, type: 'success', message: 'User updated successfully' });

  } catch (error) {
    console.error('Error updating user:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

// DELETE /api/v3/user/:username
router.delete('/:username', authenticateToken, requireRoles(['admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { username } = req.params;
    
    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ code: 404, type: 'error', message: 'User not found' });
    }

    // Pre-condition: Cannot delete user with active orders
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count FROM orders 
      WHERE user_id = ? AND status IN ('placed', 'approved')
    `).get(user.id) as any;

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ 
        code: 400, 
        type: 'error', 
        message: 'Cannot delete user with active orders' 
      });
    }

    // Delete user
    db.prepare('DELETE FROM users WHERE username = ?').run(username);

    res.json({ code: 200, type: 'success', message: 'User deleted successfully' });

  } catch (error) {
    console.error('Error deleting user:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

export default router;