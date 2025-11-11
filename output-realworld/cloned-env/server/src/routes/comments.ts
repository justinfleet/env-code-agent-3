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

// Helper to format comment with author
function formatComment(comment: any, currentUserId?: number) {
  // Check if current user follows comment author
  let following = false;
  if (currentUserId && currentUserId !== comment.author_id) {
    const follow = db.prepare(
      'SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?'
    ).get(currentUserId, comment.author_id);
    following = !!follow;
  }

  return {
    id: comment.id,
    createdAt: comment.created_at,
    updatedAt: comment.updated_at,
    body: comment.body,
    author: {
      username: comment.username,
      bio: comment.bio || '',
      image: comment.image || '',
      following
    }
  };
}

// GET /api/articles/:slug/comments
router.get('/:slug/comments', optionalAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const currentUserId = req.user?.userId;

    // Check if article exists
    const article = db.prepare('SELECT id FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    // Get comments with author information
    const comments = db.prepare(`
      SELECT c.*, u.username, u.bio, u.image
      FROM comments c
      JOIN users u ON c.author_id = u.id
      WHERE c.article_id = ?
      ORDER BY c.created_at DESC
    `).all(article.id);

    const formattedComments = comments.map(comment => formatComment(comment, currentUserId));

    res.json({ comments: formattedComments });
  } catch (error) {
    console.error('Get comments error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/articles/:slug/comments
router.post('/:slug/comments', requireAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const { comment } = req.body;
    const currentUserId = req.user.userId;

    if (!comment.body) {
      return res.status(422).json({
        errors: { body: ['comment body is required'] }
      });
    }

    // Check if article exists
    const article = db.prepare('SELECT id FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    // Create comment
    const result = db.prepare(`
      INSERT INTO comments (body, article_id, author_id)
      VALUES (?, ?, ?)
    `).run(comment.body, article.id, currentUserId);

    // Get created comment with author information
    const createdComment = db.prepare(`
      SELECT c.*, u.username, u.bio, u.image
      FROM comments c
      JOIN users u ON c.author_id = u.id
      WHERE c.id = ?
    `).get(result.lastInsertRowid) as any;

    res.json({ comment: formatComment(createdComment, currentUserId) });
  } catch (error) {
    console.error('Create comment error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/articles/:slug/comments/:id
router.delete('/:slug/comments/:id', requireAuth, (req: any, res: Response) => {
  try {
    const { slug, id } = req.params;
    const currentUserId = req.user.userId;

    // Check if article exists
    const article = db.prepare('SELECT id FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    // Check if comment exists and user owns it
    const comment = db.prepare(
      'SELECT * FROM comments WHERE id = ? AND article_id = ?'
    ).get(id, article.id) as any;

    if (!comment) {
      return res.status(404).json({ error: 'Comment not found' });
    }

    if (comment.author_id !== currentUserId) {
      return res.status(403).json({ error: 'Not authorized to delete this comment' });
    }

    // Delete comment
    db.prepare('DELETE FROM comments WHERE id = ?').run(id);

    res.json({});
  } catch (error) {
    console.error('Delete comment error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;