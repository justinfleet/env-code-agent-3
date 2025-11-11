import { Router, Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import db from '../lib/db';

const router = Router();
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

// Helper to generate JWT
function generateToken(userId: number) {
  return jwt.sign({ userId }, JWT_SECRET, { expiresIn: '30d' });
}

// Helper to get user by email
function getUserByEmail(email: string) {
  return db.prepare('SELECT * FROM users WHERE email = ?').get(email) as any;
}

// Helper to get user by id
function getUserById(id: number) {
  return db.prepare('SELECT * FROM users WHERE id = ?').get(id) as any;
}

// Helper to format user response
function formatUser(user: any, token?: string) {
  return {
    email: user.email,
    token: token || generateToken(user.id),
    username: user.username,
    bio: user.bio || '',
    image: user.image || ''
  };
}

// POST /api/users/login
router.post('/login', async (req: Request, res: Response) => {
  try {
    const { user: { email, password } } = req.body;

    if (!email || !password) {
      return res.status(422).json({ 
        errors: { body: ['email and password are required'] } 
      });
    }

    const user = getUserByEmail(email);
    if (!user) {
      return res.status(422).json({ 
        errors: { body: ['email or password is invalid'] } 
      });
    }

    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      return res.status(422).json({ 
        errors: { body: ['email or password is invalid'] } 
      });
    }

    res.json({ user: formatUser(user) });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/users (registration)
router.post('/', async (req: Request, res: Response) => {
  try {
    const { user: { username, email, password } } = req.body;

    if (!username || !email || !password) {
      return res.status(422).json({ 
        errors: { body: ['username, email and password are required'] } 
      });
    }

    // Check if user already exists
    const existingUser = getUserByEmail(email);
    if (existingUser) {
      return res.status(422).json({ 
        errors: { body: ['email already taken'] } 
      });
    }

    const existingUsername = db.prepare('SELECT * FROM users WHERE username = ?').get(username);
    if (existingUsername) {
      return res.status(422).json({ 
        errors: { body: ['username already taken'] } 
      });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    
    const result = db.prepare(
      'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)'
    ).run(username, email, passwordHash);

    const newUser = getUserById(result.lastInsertRowid as number);
    res.json({ user: formatUser(newUser) });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;