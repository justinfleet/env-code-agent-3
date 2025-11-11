import { Router, Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import db from '../lib/db';

const router = Router();
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

// Middleware to optionally authenticate user
function optionalAuth(req: any, res: Response, next: any) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    req.user = null;
    return next();
  }

  jwt.verify(token, JWT_SECRET, (err: any, user: any) => {
    if (err) {
      req.user = null;
    } else {
      req.user = user;
    }
    next();
  });
}

// Middleware to require authentication
function requireAuth(req: any, res: Response, next: any) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

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

// Helper to get user by username
function getUserByUsername(username: string) {
  return db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any;
}

// Helper to check if user is following another user
function isFollowing(followerId: number, followingId: number): boolean {
  const result = db.prepare(
    'SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?'
  ).get(followerId, followingId);
  return !!result;
}

// Helper to format profile response
function formatProfile(user: any, currentUserId?: number) {
  return {
    username: user.username,
    bio: user.bio || '',
    image: user.image || '',
    following: currentUserId ? isFollowing(currentUserId, user.id) : false
  };
}

// GET /api/profiles/:username
router.get('/:username', optionalAuth, (req: any, res: Response) => {
  try {
    const { username } = req.params;
    
    const user = getUserByUsername(username);
    if (!user) {
      return res.status(404).json({ error: 'Profile not found' });
    }

    const currentUserId = req.user?.userId;
    res.json({ profile: formatProfile(user, currentUserId) });
  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/profiles/:username/follow
router.post('/:username/follow', requireAuth, (req: any, res: Response) => {
  try {
    const { username } = req.params;
    const currentUserId = req.user.userId;

    const user = getUserByUsername(username);
    if (!user) {
      return res.status(404).json({ error: 'Profile not found' });
    }

    if (user.id === currentUserId) {
      return res.status(422).json({ 
        errors: { body: ['Cannot follow yourself'] }
      });
    }

    // Check if already following
    if (!isFollowing(currentUserId, user.id)) {
      db.prepare(
        'INSERT INTO follows (follower_id, following_id) VALUES (?, ?)'
      ).run(currentUserId, user.id);
    }

    res.json({ profile: formatProfile(user, currentUserId) });
  } catch (error) {
    console.error('Follow error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/profiles/:username/follow
router.delete('/:username/follow', requireAuth, (req: any, res: Response) => {
  try {
    const { username } = req.params;
    const currentUserId = req.user.userId;

    const user = getUserByUsername(username);
    if (!user) {
      return res.status(404).json({ error: 'Profile not found' });
    }

    // Remove follow relationship
    db.prepare(
      'DELETE FROM follows WHERE follower_id = ? AND following_id = ?'
    ).run(currentUserId, user.id);

    res.json({ profile: formatProfile(user, currentUserId) });
  } catch (error) {
    console.error('Unfollow error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;