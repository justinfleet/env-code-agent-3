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

// Helper to generate slug from title
function generateSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9 -]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim('-') + '-' + Math.random().toString(36).substr(2, 8);
}

// Helper to get article with tags and author
function getArticleWithDetails(slug: string, currentUserId?: number) {
  const article = db.prepare(`
    SELECT a.*, u.username, u.bio, u.image as author_image
    FROM articles a
    JOIN users u ON a.author_id = u.id
    WHERE a.slug = ?
  `).get(slug) as any;

  if (!article) return null;

  // Get tags
  const tags = db.prepare(`
    SELECT t.name
    FROM tags t
    JOIN article_tags at ON t.id = at.tag_id
    WHERE at.article_id = ?
  `).all(article.id).map((tag: any) => tag.name);

  // Get favorites count
  const favoritesCount = db.prepare(
    'SELECT COUNT(*) as count FROM favorites WHERE article_id = ?'
  ).get(article.id) as any;

  // Check if current user favorited
  let favorited = false;
  if (currentUserId) {
    const favorite = db.prepare(
      'SELECT 1 FROM favorites WHERE user_id = ? AND article_id = ?'
    ).get(currentUserId, article.id);
    favorited = !!favorite;
  }

  // Check if current user follows author
  let following = false;
  if (currentUserId && currentUserId !== article.author_id) {
    const follow = db.prepare(
      'SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?'
    ).get(currentUserId, article.author_id);
    following = !!follow;
  }

  return {
    slug: article.slug,
    title: article.title,
    description: article.description,
    body: article.body,
    tagList: tags,
    createdAt: article.created_at,
    updatedAt: article.updated_at,
    favorited,
    favoritesCount: favoritesCount.count,
    author: {
      username: article.username,
      bio: article.bio || '',
      image: article.author_image || '',
      following
    }
  };
}

// GET /api/articles/feed
router.get('/feed', requireAuth, (req: any, res: Response) => {
  try {
    const currentUserId = req.user.userId;
    const limit = parseInt(req.query.limit as string) || 20;
    const offset = parseInt(req.query.offset as string) || 0;

    const articles = db.prepare(`
      SELECT a.slug
      FROM articles a
      JOIN follows f ON a.author_id = f.following_id
      WHERE f.follower_id = ?
      ORDER BY a.created_at DESC
      LIMIT ? OFFSET ?
    `).all(currentUserId, limit, offset);

    const articlesWithDetails = articles.map((a: any) => 
      getArticleWithDetails(a.slug, currentUserId)
    ).filter(Boolean);

    const articlesCount = db.prepare(`
      SELECT COUNT(*) as count
      FROM articles a
      JOIN follows f ON a.author_id = f.following_id
      WHERE f.follower_id = ?
    `).get(currentUserId) as any;

    res.json({
      articles: articlesWithDetails,
      articlesCount: articlesCount.count
    });
  } catch (error) {
    console.error('Get feed error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/articles
router.get('/', optionalAuth, (req: any, res: Response) => {
  try {
    const { tag, author, favorited, limit = 20, offset = 0 } = req.query;
    const currentUserId = req.user?.userId;

    let query = `
      SELECT DISTINCT a.slug
      FROM articles a
      JOIN users u ON a.author_id = u.id
    `;
    const params: any[] = [];
    const conditions: string[] = [];

    if (tag) {
      query += ' JOIN article_tags at ON a.id = at.article_id JOIN tags t ON at.tag_id = t.id';
      conditions.push('t.name = ?');
      params.push(tag);
    }

    if (author) {
      conditions.push('u.username = ?');
      params.push(author);
    }

    if (favorited) {
      query += ' JOIN favorites f ON a.id = f.article_id JOIN users fu ON f.user_id = fu.id';
      conditions.push('fu.username = ?');
      params.push(favorited);
    }

    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }

    query += ' ORDER BY a.created_at DESC LIMIT ? OFFSET ?';
    params.push(parseInt(limit as string), parseInt(offset as string));

    const articles = db.prepare(query).all(...params);

    const articlesWithDetails = articles.map((a: any) => 
      getArticleWithDetails(a.slug, currentUserId)
    ).filter(Boolean);

    // Get count
    let countQuery = `
      SELECT COUNT(DISTINCT a.id) as count
      FROM articles a
      JOIN users u ON a.author_id = u.id
    `;
    const countParams: any[] = [];
    const countConditions: string[] = [];

    if (tag) {
      countQuery += ' JOIN article_tags at ON a.id = at.article_id JOIN tags t ON at.tag_id = t.id';
      countConditions.push('t.name = ?');
      countParams.push(tag);
    }

    if (author) {
      countConditions.push('u.username = ?');
      countParams.push(author);
    }

    if (favorited) {
      countQuery += ' JOIN favorites f ON a.id = f.article_id JOIN users fu ON f.user_id = fu.id';
      countConditions.push('fu.username = ?');
      countParams.push(favorited);
    }

    if (countConditions.length > 0) {
      countQuery += ' WHERE ' + countConditions.join(' AND ');
    }

    const articlesCount = db.prepare(countQuery).get(...countParams) as any;

    res.json({
      articles: articlesWithDetails,
      articlesCount: articlesCount.count
    });
  } catch (error) {
    console.error('Get articles error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/articles
router.post('/', requireAuth, (req: any, res: Response) => {
  try {
    const { article } = req.body;
    const currentUserId = req.user.userId;

    if (!article.title || !article.description || !article.body) {
      return res.status(422).json({
        errors: { body: ['title, description and body are required'] }
      });
    }

    const slug = generateSlug(article.title);
    
    const result = db.prepare(`
      INSERT INTO articles (slug, title, description, body, author_id)
      VALUES (?, ?, ?, ?, ?)
    `).run(slug, article.title, article.description, article.body, currentUserId);

    const articleId = result.lastInsertRowid as number;

    // Handle tags
    if (article.tagList && Array.isArray(article.tagList)) {
      for (const tagName of article.tagList) {
        // Insert tag if it doesn't exist
        db.prepare('INSERT OR IGNORE INTO tags (name) VALUES (?)').run(tagName);
        
        // Get tag ID
        const tag = db.prepare('SELECT id FROM tags WHERE name = ?').get(tagName) as any;
        
        // Link article to tag
        db.prepare('INSERT INTO article_tags (article_id, tag_id) VALUES (?, ?)').run(articleId, tag.id);
      }
    }

    const createdArticle = getArticleWithDetails(slug, currentUserId);
    res.json({ article: createdArticle });
  } catch (error) {
    console.error('Create article error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/articles/:slug
router.get('/:slug', optionalAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const currentUserId = req.user?.userId;

    const article = getArticleWithDetails(slug, currentUserId);
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    res.json({ article });
  } catch (error) {
    console.error('Get article error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/articles/:slug
router.put('/:slug', requireAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const { article: updateData } = req.body;
    const currentUserId = req.user.userId;

    // Check if article exists and user owns it
    const article = db.prepare('SELECT * FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    if (article.author_id !== currentUserId) {
      return res.status(403).json({ error: 'Not authorized to update this article' });
    }

    const updates: string[] = [];
    const values: any[] = [];

    if (updateData.title) {
      updates.push('title = ?', 'slug = ?');
      values.push(updateData.title, generateSlug(updateData.title));
    }

    if (updateData.description) {
      updates.push('description = ?');
      values.push(updateData.description);
    }

    if (updateData.body) {
      updates.push('body = ?');
      values.push(updateData.body);
    }

    if (updates.length > 0) {
      updates.push('updated_at = CURRENT_TIMESTAMP');
      values.push(article.id);

      const query = `UPDATE articles SET ${updates.join(', ')} WHERE id = ?`;
      db.prepare(query).run(...values);
    }

    // Get the updated slug
    const updatedArticle = db.prepare('SELECT slug FROM articles WHERE id = ?').get(article.id) as any;
    const articleWithDetails = getArticleWithDetails(updatedArticle.slug, currentUserId);

    res.json({ article: articleWithDetails });
  } catch (error) {
    console.error('Update article error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/articles/:slug
router.delete('/:slug', requireAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const currentUserId = req.user.userId;

    const article = db.prepare('SELECT * FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    if (article.author_id !== currentUserId) {
      return res.status(403).json({ error: 'Not authorized to delete this article' });
    }

    // Delete associated data first
    db.prepare('DELETE FROM article_tags WHERE article_id = ?').run(article.id);
    db.prepare('DELETE FROM favorites WHERE article_id = ?').run(article.id);
    db.prepare('DELETE FROM comments WHERE article_id = ?').run(article.id);
    
    // Delete article
    db.prepare('DELETE FROM articles WHERE id = ?').run(article.id);

    res.json({});
  } catch (error) {
    console.error('Delete article error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/articles/:slug/favorite
router.post('/:slug/favorite', requireAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const currentUserId = req.user.userId;

    const article = db.prepare('SELECT id FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    // Add favorite if not already favorited
    db.prepare('INSERT OR IGNORE INTO favorites (user_id, article_id) VALUES (?, ?)').run(currentUserId, article.id);

    const articleWithDetails = getArticleWithDetails(slug, currentUserId);
    res.json({ article: articleWithDetails });
  } catch (error) {
    console.error('Favorite article error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/articles/:slug/favorite
router.delete('/:slug/favorite', requireAuth, (req: any, res: Response) => {
  try {
    const { slug } = req.params;
    const currentUserId = req.user.userId;

    const article = db.prepare('SELECT id FROM articles WHERE slug = ?').get(slug) as any;
    if (!article) {
      return res.status(404).json({ error: 'Article not found' });
    }

    // Remove favorite
    db.prepare('DELETE FROM favorites WHERE user_id = ? AND article_id = ?').run(currentUserId, article.id);

    const articleWithDetails = getArticleWithDetails(slug, currentUserId);
    res.json({ article: articleWithDetails });
  } catch (error) {
    console.error('Unfavorite article error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;