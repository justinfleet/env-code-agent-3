import { Router, Request, Response } from 'express';
import db from '../lib/db';
import { 
  hashPassword, 
  comparePassword, 
  generateToken, 
  authMiddleware, 
  requireRoles, 
  checkOwnership, 
  AuthRequest 
} from '../lib/auth';

const router = Router();

// GET /api/v3/user/login - User login (no auth required)
router.get('/login', (req: Request, res: Response) => {
  try {
    // Add detailed logging
    console.log('=== LOGIN REQUEST ===');
    console.log('URL:', req.url);
    console.log('Query string:', req.query);
    console.log('Method:', req.method);
    console.log('Headers:', req.headers);
    console.log('Raw query:', req.url.split('?')[1]);

    const username = req.query.username as string;
    const password = req.query.password as string;

    console.log('Parsed username:', username);
    console.log('Parsed password:', password ? '[PROVIDED]' : '[MISSING]');

    // If no username or password, try to be more helpful
    if (!username && !password) {
      console.log('No username or password provided at all');
      return res.status(400).json({ 
        error: 'Username and password required',
        received: req.query,
        help: 'Expected: /api/v3/user/login?username=XXX&password=YYY'
      });
    }

    if (!username) {
      console.log('Username missing');
      return res.status(400).json({ error: 'Username parameter required' });
    }

    if (!password) {
      console.log('Password missing');
      return res.status(400).json({ error: 'Password parameter required' });
    }

    // Try both testuser/password and admin/password
    const user = db.prepare(`
      SELECT id, username, password, role 
      FROM users 
      WHERE username = ?
    `).get(username) as any;

    console.log('User lookup result:', user ? { id: user.id, username: user.username, role: user.role } : 'not found');

    if (!user) {
      console.log('User not found, available users:');
      const allUsers = db.prepare('SELECT username FROM users').all();
      console.log(allUsers);
      return res.status(401).json({ error: 'Invalid username or password' });
    }

    // For testing, check if password is literally "password"
    const isPasswordMatch = comparePassword(password, user.password);
    console.log('Password verification result:', isPasswordMatch);

    if (!isPasswordMatch) {
      console.log('Password does not match');
      return res.status(401).json({ error: 'Invalid username or password' });
    }

    const token = generateToken({
      user_id: user.id,
      username: user.username,
      role: user.role
    });

    console.log('Login successful, token generated');
    console.log('=== END LOGIN REQUEST ===');
    
    // API spec expects { token: "string" }
    res.json({ token });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Server error', details: error });
  }
});

// GET /api/v3/user/logout - User logout (no auth required)
router.get('/logout', (req: Request, res: Response) => {
  // Since we're using JWT, logout is handled client-side by discarding the token
  res.json({});
});

// GET /api/v3/user/{username} - Get user by username (NO AUTH according to spec)
router.get('/:username', (req: Request, res: Response) => {
  try {
    const username = req.params.username;
    
    const user = db.prepare(`
      SELECT id, username, first_name, last_name, email, phone, user_status
      FROM users 
      WHERE username = ?
    `).get(username) as any;

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // API spec expects direct user object properties, not wrapped in data
    const result = {
      id: user.id,
      username: user.username,
      firstName: user.first_name,
      lastName: user.last_name,
      email: user.email,
      password: "***", // Don't return actual password, but spec expects this field
      phone: user.phone,
      userStatus: user.user_status
    };

    res.json(result);
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// POST /api/v3/user - Create user (no auth required - registration)
router.post('/', (req: Request, res: Response) => {
  try {
    const { username, firstName, lastName, email, password, phone, userStatus } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }

    // Check if username already exists
    const existingUser = db.prepare('SELECT username FROM users WHERE username = ?').get(username);
    if (existingUser) {
      return res.status(409).json({ error: 'Username already exists' });
    }

    const hashedPassword = hashPassword(password);

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
      userStatus || 1,
      'customer' // Default role for new users
    );

    res.status(201).json({
      code: 201,
      type: 'success',
      message: 'User created successfully'
    });
  } catch (error) {
    console.error('Create user error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// POST /api/v3/user/createWithList - Bulk create users (NO AUTH according to spec)
router.post('/createWithList', (req: Request, res: Response) => {
  try {
    const users = req.body;

    if (!Array.isArray(users) || users.length === 0) {
      return res.status(400).json({ error: 'Users array is required' });
    }

    const transaction = db.transaction(() => {
      const insertUser = db.prepare(`
        INSERT INTO users (username, first_name, last_name, email, password, phone, user_status, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `);

      for (const user of users) {
        if (!user.username || !user.password) {
          throw new Error('Username and password are required for all users');
        }

        const hashedPassword = hashPassword(user.password);
        insertUser.run(
          user.username,
          user.firstName || null,
          user.lastName || null,
          user.email || null,
          hashedPassword,
          user.phone || null,
          user.userStatus || 1,
          'customer'
        );
      }
    });

    transaction();

    res.status(201).json({
      code: 201,
      type: 'success',
      message: `${users.length} users created successfully`
    });
  } catch (error) {
    console.error('Bulk create users error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// PUT /api/v3/user/{username} - Update user (NO AUTH according to spec)
router.put('/:username', (req: Request, res: Response) => {
  try {
    const username = req.params.username;
    const { firstName, lastName, email, password, phone, userStatus } = req.body;

    const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    const updateFields = [];
    const params = [];

    if (firstName !== undefined) {
      updateFields.push('first_name = ?');
      params.push(firstName);
    }
    if (lastName !== undefined) {
      updateFields.push('last_name = ?');
      params.push(lastName);
    }
    if (email !== undefined) {
      updateFields.push('email = ?');
      params.push(email);
    }
    if (password) {
      updateFields.push('password = ?');
      params.push(hashPassword(password));
    }
    if (phone !== undefined) {
      updateFields.push('phone = ?');
      params.push(phone);
    }
    if (userStatus !== undefined) {
      updateFields.push('user_status = ?');
      params.push(userStatus);
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    params.push(username);
    db.prepare(`UPDATE users SET ${updateFields.join(', ')} WHERE username = ?`).run(...params);

    // No response body expected for this endpoint
    res.status(200).send();
  } catch (error) {
    console.error('Update user error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// DELETE /api/v3/user/{username} - Delete user (NO AUTH according to spec)
router.delete('/:username', (req: Request, res: Response) => {
  try {
    const username = req.params.username;

    const result = db.prepare('DELETE FROM users WHERE username = ?').run(username);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    // No response body expected for this endpoint
    res.status(200).send();
  } catch (error) {
    console.error('Delete user error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

export default router;