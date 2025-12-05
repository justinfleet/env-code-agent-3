import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import { Request, Response, NextFunction } from 'express';
import db from './db';

const JWT_SECRET = process.env.JWT_SECRET || 'your-development-jwt-secret-key-change-in-production';

export interface User {
  id: number;
  username: string;
  role: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  user_status?: number;
}

export interface AuthRequest extends Request {
  user?: User;
}

export function hashPassword(password: string): string {
  return bcrypt.hashSync(password, 10);
}

export function verifyPassword(password: string, hash: string): boolean {
  return bcrypt.compareSync(password, hash);
}

export function generateToken(user: User): string {
  return jwt.sign(
    {
      user_id: user.id,
      username: user.username,
      role: user.role
    },
    JWT_SECRET,
    { expiresIn: '24h' }
  );
}

export function verifyToken(token: string): any {
  return jwt.verify(token, JWT_SECRET);
}

export function authenticateToken(req: AuthRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  try {
    const decoded = verifyToken(token);
    const user = db.prepare('SELECT * FROM users WHERE id = ?').get(decoded.user_id) as User;
    
    if (!user) {
      return res.status(401).json({ error: 'Invalid token' });
    }

    req.user = user;
    next();
  } catch (error) {
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
}

export function requireRoles(allowedRoles: string[]) {
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
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    // Bypass roles can access any resource
    if (bypassRoles.includes(req.user.role)) {
      return next();
    }

    try {
      let query: string;
      let params: any[];

      if (resource === 'order') {
        const orderId = req.params.orderId;
        const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId);
        
        if (!order) {
          return res.status(404).json({ error: 'Order not found' });
        }

        if ((order as any)[ownerField] !== req.user.id) {
          return res.status(403).json({ error: 'Access denied' });
        }
      } else if (resource === 'user') {
        const username = req.params.username;
        if (username !== req.user.username) {
          return res.status(403).json({ error: 'Access denied' });
        }
      }

      next();
    } catch (error) {
      res.status(500).json({ error: 'Internal server error' });
    }
  };
}