import express from 'express';
import db from '../lib/db';
import { authenticateToken, requireRoles, checkOwnership, AuthRequest, hashPassword, verifyPassword, generateToken } from '../lib/auth';

const router = express.Router();

// POST /api/v3/user
router.post('/', (req, res) => {
  try {
    const { username, firstName, lastName, email, password, phone, userStatus } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }

    // Check if username already exists
    const existingUser = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
    if (existingUser) {
      return res.status(400).json({ error: 'Username already exists' });
    }

    const hashedPassword = hashPassword(password);

    const insertUser = db.prepare(`
      INSERT INTO users (username, first_name, last_name, email, password, phone, user_status, role)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const result = insertUser.run(
      username,
      firstName || null,
      lastName || null,
      email || null,
      hashedPassword,
      phone || null,
      userStatus || 0,
      'customer'
    );

    const userId = result.lastInsertRowid;
    const user = db.prepare(`
      SELECT id, username, first_name, last_name, email, phone, user_status, role 
      FROM users WHERE id = ?
    `).get(userId);

    res.status(201).json({
      data: {
        id: (user as any).id,
        username: (user as any).username,
        firstName: (user as any).first_name,
        lastName: (user as any).last_name,
        email: (user as any).email,
        password: '[PROTECTED]', // Don't return actual password
        phone: (user as any).phone,
        userStatus: (user as any).user_status
      }
    });
  } catch (error) {
    console.error('Create user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/user/createWithList
router.post('/createWithList', (req, res) => {
  try {
    const users = req.body;

    if (!Array.isArray(users) || users.length === 0) {
      return res.status(400).json({ error: 'Array of users is required' });
    }

    const transaction = db.transaction(() => {
      const results = [];
      
      for (const userData of users) {
        const { username, firstName, lastName, email, password, phone, userStatus } = userData;

        if (!username || !password) {
          throw new Error('Username and password are required for all users');
        }

        // Check if username already exists
        const existingUser = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
        if (existingUser) {
          throw new Error(`Username ${username} already exists`);
        }

        const hashedPassword = hashPassword(password);

        const insertUser = db.prepare(`
          INSERT INTO users (username, first_name, last_name, email, password, phone, user_status, role)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `);

        const result = insertUser.run(
          username,
          firstName || null,
          lastName || null,
          email || null,
          hashedPassword,
          phone || null,
          userStatus || 0,
          'customer'
        );

        const user = db.prepare(`
          SELECT id, username, first_name, last_name, email, phone, user_status, role 
          FROM users WHERE id = ?
        `).get(result.lastInsertRowid);

        results.push({
          id: (user as any).id,
          username: (user as any).username,
          firstName: (user as any).first_name,
          lastName: (user as any).last_name,
          email: (user as any).email,
          password: '[PROTECTED]',
          phone: (user as any).phone,
          userStatus: (user as any).user_status
        });
      }

      return results;
    });

    const createdUsers = transaction();
    res.status(201).json({ data: createdUsers });
  } catch (error) {
    console.error('Create users error:', error);
    res.status(400).json({ error: (error as Error).message });
  }
});

// GET /api/v3/user/login
router.get('/login', (req, res) => {
  try {
    const { username, password } = req.query;

    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username as string);

    if (!user || !verifyPassword(password as string, (user as any).password)) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = generateToken({
      id: (user as any).id,
      username: (user as any).username,
      role: (user as any).role,
      first_name: (user as any).first_name,
      last_name: (user as any).last_name,
      email: (user as any).email,
      phone: (user as any).phone,
      user_status: (user as any).user_status
    });

    res.json({ data: { token } });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/user/logout
router.get('/logout', authenticateToken, (req: AuthRequest, res) => {
  // In a real implementation, you would invalidate the token
  // For JWT tokens, this could involve a blacklist or shorter expiry
  res.json({ data: { message: 'User logged out successfully' } });
});

// GET /api/v3/user/:username
router.get('/:username', authenticateToken, checkOwnership('user', 'username', ['admin']), (req: AuthRequest, res) => {
  try {
    const { username } = req.params;

    const user = db.prepare(`
      SELECT id, username, first_name, last_name, email, phone, user_status, role 
      FROM users WHERE username = ?
    `).get(username);

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({
      data: {
        id: (user as any).id,
        username: (user as any).username,
        firstName: (user as any).first_name,
        lastName: (user as any).last_name,
        email: (user as any).email,
        password: '[PROTECTED]',
        phone: (user as any).phone,
        userStatus: (user as any).user_status
      }
    });
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/v3/user/:username
router.put('/:username', authenticateToken, checkOwnership('user', 'username', ['admin']), (req: AuthRequest, res) => {
  try {
    const { username } = req.params;
    const { firstName, lastName, email, password, phone, userStatus, role } = req.body;

    // Check if user exists
    const existingUser = db.prepare('SELECT * FROM users WHERE username = ?').get(username);
    if (!existingUser) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Validation: only admin can change roles
    if (role !== undefined && role !== (existingUser as any).role && req.user?.role !== 'admin') {
      return res.status(403).json({ error: 'Only admin can change user roles' });
    }

    const updateFields = [];
    const values = [];

    if (firstName !== undefined) {
      updateFields.push('first_name = ?');
      values.push(firstName);
    }
    if (lastName !== undefined) {
      updateFields.push('last_name = ?');
      values.push(lastName);
    }
    if (email !== undefined) {
      updateFields.push('email = ?');
      values.push(email);
    }
    if (password !== undefined) {
      updateFields.push('password = ?');
      values.push(hashPassword(password));
    }
    if (phone !== undefined) {
      updateFields.push('phone = ?');
      values.push(phone);
    }
    if (userStatus !== undefined) {
      updateFields.push('user_status = ?');
      values.push(userStatus);
    }
    if (role !== undefined && req.user?.role === 'admin') {
      updateFields.push('role = ?');
      values.push(role);
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    values.push(username);

    const result = db.prepare(`
      UPDATE users 
      SET ${updateFields.join(', ')}
      WHERE username = ?
    `).run(...values);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ data: { message: 'User updated successfully' } });
  } catch (error) {
    console.error('Update user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/user/:username
router.delete('/:username', authenticateToken, requireRoles(['admin']), (req: AuthRequest, res) => {
  try {
    const { username } = req.params;

    // Pre-condition check: cannot delete user with active orders
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count FROM orders 
      WHERE user_id = (SELECT id FROM users WHERE username = ?) AND status IN ('placed', 'approved')
    `).get(username) as { count: number };

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ error: 'Cannot delete user with active orders' });
    }

    const result = db.prepare('DELETE FROM users WHERE username = ?').run(username);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ data: { message: 'User deleted successfully' } });
  } catch (error) {
    console.error('Delete user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;