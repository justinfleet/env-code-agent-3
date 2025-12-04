import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { Request, Response, NextFunction } from 'express';
import db from './db.js';

const JWT_SECRET = process.env.JWT_SECRET || 'your-jwt-secret-key-here';

export interface AuthUser {
  user_id: number;
  username: string;
  role: string;
}

export interface AuthRequest extends Request {
  user?: AuthUser;
}

export function hashPassword(password: string): string {
  return bcrypt.hashSync(password, 10);
}

export function comparePassword(password: string, hash: string): boolean {
  // For development: also check if it's a plain text password match (for seed data)
  if (password === hash) {
    return true;
  }
  return bcrypt.compareSync(password, hash);
}

export function generateToken(user: AuthUser): string {
  return jwt.sign(user, JWT_SECRET, { expiresIn: '24h' });
}

export function verifyAuth(req: AuthRequest, res: Response, next: NextFunction) {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const token = authHeader.substring(7);
    const decoded = jwt.verify(token, JWT_SECRET) as AuthUser;
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

export function requireRole(allowedRoles: string[]) {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }

    next();
  };
}

export function checkOwnership(resource: string, ownerField: string, bypassRoles: string[] = []) {
  return async (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    // Admin and other bypass roles can access anything
    if (bypassRoles.includes(req.user.role)) {
      return next();
    }

    try {
      let query: string;
      let params: any[];

      if (resource === 'order') {
        const orderId = req.params.orderId;
        query = 'SELECT user_id FROM orders WHERE id = ?';
        params = [orderId];
      } else if (resource === 'user') {
        const username = req.params.username;
        if (username !== req.user.username) {
          return res.status(403).json({ error: 'Can only access your own profile' });
        }
        return next();
      } else {
        return res.status(500).json({ error: 'Unknown resource type' });
      }

      const stmt = db.prepare(query);
      const row = stmt.get(...params) as any;

      if (!row) {
        return res.status(404).json({ error: `${resource} not found` });
      }

      if (row.user_id !== req.user.user_id) {
        return res.status(403).json({ error: `Cannot access this ${resource}` });
      }

      next();
    } catch (error) {
      res.status(500).json({ error: 'Internal server error' });
    }
  };
}