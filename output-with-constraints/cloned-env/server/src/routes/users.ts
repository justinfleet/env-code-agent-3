import { Router } from 'express';
import db from '../lib/db.js';
import { verifyAuth, requireRole, checkOwnership, AuthRequest, hashPassword, comparePassword, generateToken } from '../lib/auth.js';

const router = Router();

// GET /api/v3/user/login
router.get('/login', (req, res) => {
  try {
    const { username, password } = req.query;

    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }

    console.log(`Login attempt: ${username}`);

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username as string) as any;
    if (!user) {
      console.log(`User not found: ${username}`);
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    console.log(`User found, checking password for ${username}`);

    if (!comparePassword(password as string, user.password)) {
      console.log(`Password mismatch for ${username}`);
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    console.log(`Password correct for ${username}, generating token`);

    const token = generateToken({
      user_id: user.id,
      username: user.username,
      role: user.role
    });

    // Calculate expiry (24h from now)
    const expiryDate = new Date();
    expiryDate.setHours(expiryDate.getHours() + 24);

    console.log(`Login successful for ${username}`);

    res.json({
      token,
      expires: expiryDate.toISOString()
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/user/logout
router.get('/logout', (req, res) => {
  // In a real implementation, you might maintain a blacklist of tokens
  // For now, we'll just return success as JWT tokens are stateless
  res.json({ message: 'Logged out successfully' });
});

// POST /api/v3/user
router.post('/', (req, res) => {
  try {
    const { username, firstName, lastName, email, password, phone, userStatus } = req.body;

    if (!username || !email || !password) {
      return res.status(400).json({ error: 'Username, email, and password are required' });
    }

    // Check if username already exists
    const existingUser = db.prepare('SELECT id FROM users WHERE username = ?').get(username) as any;
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
      email,
      hashedPassword,
      phone || null,
      userStatus || 0,
      'customer' // New users are customers by default
    );
    const userId = result.lastInsertRowid as number;

    const createdUser = db.prepare('SELECT * FROM users WHERE id = ?').get(userId) as any;

    const response = {
      id: createdUser.id,
      username: createdUser.username,
      firstName: createdUser.first_name,
      lastName: createdUser.last_name,
      email: createdUser.email,
      password: createdUser.password, // In real apps, never return password
      phone: createdUser.phone,
      userStatus: createdUser.user_status
    };

    res.status(201).json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/user/createWithList
router.post('/createWithList', verifyAuth, requireRole(['admin']), (req, res) => {
  try {
    const users = req.body;

    if (!Array.isArray(users) || users.length === 0) {
      return res.status(400).json({ error: 'Users array is required' });
    }

    const createdUsers = [];
    
    for (const userData of users) {
      const { username, firstName, lastName, email, password, phone, userStatus } = userData;

      if (!username || !email || !password) {
        return res.status(400).json({ error: 'Each user must have username, email, and password' });
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
        email,
        hashedPassword,
        phone || null,
        userStatus || 0,
        'customer'
      );
      const userId = result.lastInsertRowid as number;

      const createdUser = db.prepare('SELECT * FROM users WHERE id = ?').get(userId) as any;
      createdUsers.push({
        id: createdUser.id,
        username: createdUser.username,
        firstName: createdUser.first_name,
        lastName: createdUser.last_name,
        email: createdUser.email,
        password: createdUser.password,
        phone: createdUser.phone,
        userStatus: createdUser.user_status
      });
    }

    res.status(201).json(createdUsers[0]); // Return first user as per spec
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/user/{username}
router.get('/:username', verifyAuth, checkOwnership('user', 'username', ['admin']), (req, res) => {
  try {
    const username = req.params.username;
    
    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    const response = {
      id: user.id,
      username: user.username,
      firstName: user.first_name,
      lastName: user.last_name,
      email: user.email,
      password: user.password,
      phone: user.phone,
      userStatus: user.user_status
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/v3/user/{username}
router.put('/:username', verifyAuth, checkOwnership('user', 'username', ['admin']), (req: AuthRequest, res) => {
  try {
    const username = req.params.username;
    const { firstName, lastName, email, password, phone, userStatus, role } = req.body;

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Special check: only admin can change roles
    if (role !== undefined && role !== user.role) {
      if (req.user!.role !== 'admin') {
        return res.status(403).json({ error: 'Only admin can change user roles' });
      }
    }

    const hashedPassword = password ? hashPassword(password) : user.password;

    const updateUser = db.prepare(`
      UPDATE users 
      SET first_name = ?, last_name = ?, email = ?, password = ?, phone = ?, user_status = ?, role = ?
      WHERE username = ?
    `);
    updateUser.run(
      firstName || user.first_name,
      lastName || user.last_name,
      email || user.email,
      hashedPassword,
      phone || user.phone,
      userStatus !== undefined ? userStatus : user.user_status,
      role || user.role,
      username
    );

    const updatedUser = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;

    const response = {
      id: updatedUser.id,
      username: updatedUser.username,
      firstName: updatedUser.first_name,
      lastName: updatedUser.last_name,
      email: updatedUser.email,
      password: updatedUser.password,
      phone: updatedUser.phone,
      userStatus: updatedUser.user_status
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/user/{username}
router.delete('/:username', verifyAuth, requireRole(['admin']), (req, res) => {
  try {
    const username = req.params.username;

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Pre-condition: check for active orders
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count 
      FROM orders 
      WHERE user_id = ? AND status IN ('placed', 'approved')
    `).get(user.id) as any;

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ error: 'Cannot delete user with active orders' });
    }

    const deleteUser = db.prepare('DELETE FROM users WHERE username = ?');
    deleteUser.run(username);

    res.json({ message: 'User deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;