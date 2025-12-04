import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import { Request, Response, NextFunction } from 'express';
import db from './db';

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-key-change-in-production';

export interface AuthUser {
  user_id: number;
  username: string;
  role: string;
}

export interface AuthRequest extends Request {
  user?: AuthUser;
}

export const hashPassword = (password: string): string => {
  return bcrypt.hashSync(password, 10);
};

export const comparePassword = (password: string, hash: string): boolean => {
  return bcrypt.compareSync(password, hash);
};

export const generateToken = (payload: AuthUser): string => {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '24h' });
};

export const verifyToken = (token: string): AuthUser | null => {
  try {
    return jwt.verify(token, JWT_SECRET) as AuthUser;
  } catch {
    return null;
  }
};

export const authMiddleware = (req: AuthRequest, res: Response, next: NextFunction) => {
  const authHeader = req.headers.authorization;
  const token = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : null;

  if (!token) {
    return res.status(401).json({ error: 'Authentication required' });
  }

  const user = verifyToken(token);
  if (!user) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }

  req.user = user;
  next();
};

export const requireRoles = (allowedRoles: string[]) => {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }

    next();
  };
};

export const checkOwnership = (resource: string, ownerField: string, bypassRoles: string[] = []) => {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    // Bypass ownership check for certain roles
    if (bypassRoles.includes(req.user.role)) {
      return next();
    }

    try {
      let query: string;
      let params: any[];

      if (resource === 'order') {
        query = 'SELECT user_id FROM orders WHERE id = ?';
        params = [req.params.orderId];
      } else if (resource === 'user') {
        query = 'SELECT username FROM users WHERE username = ?';
        params = [req.params.username];
      } else {
        return res.status(400).json({ error: 'Invalid resource type' });
      }

      const result = db.prepare(query).get(...params) as any;
      
      if (!result) {
        return res.status(404).json({ error: `${resource} not found` });
      }

      // Check ownership
      if (resource === 'order' && result.user_id !== req.user.user_id) {
        return res.status(403).json({ error: 'Access denied: not owner' });
      } else if (resource === 'user' && result.username !== req.user.username) {
        return res.status(403).json({ error: 'Access denied: not owner' });
      }

      next();
    } catch (error) {
      console.error('Ownership check error:', error);
      res.status(500).json({ error: 'Server error during ownership check' });
    }
  };
};