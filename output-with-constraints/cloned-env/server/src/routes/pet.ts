import { Router, Request, Response } from 'express';
import db from '../lib/db';
import { authMiddleware, requireRoles, AuthRequest } from '../lib/auth';
import multer from 'multer';

const router = Router();
const upload = multer({ dest: 'uploads/' });

// Helper function to get pet with category and tags
const getPetWithDetails = (petId: number) => {
  const pet = db.prepare(`
    SELECT p.*, c.name as category_name 
    FROM pets p 
    LEFT JOIN categories c ON p.category_id = c.id 
    WHERE p.id = ?
  `).get(petId) as any;

  if (!pet) return null;

  const tags = db.prepare(`
    SELECT t.id, t.name 
    FROM tags t 
    JOIN pet_tags pt ON t.id = pt.tag_id 
    WHERE pt.pet_id = ?
  `).all(petId) as any[];

  return {
    id: pet.id,
    name: pet.name,
    category: pet.category_id ? {
      id: pet.category_id,
      name: pet.category_name
    } : null,
    photoUrls: pet.photo_urls ? JSON.parse(pet.photo_urls) : [],
    tags: tags,
    status: pet.status
  };
};

// GET /api/v3/pet/findByStatus - Find pets by status (auth required per spec)
router.get('/findByStatus', authMiddleware, (req: Request, res: Response) => {
  try {
    const status = req.query.status as string;
    if (!status) {
      return res.status(400).json({ error: 'Status parameter required' });
    }

    const pets = db.prepare(`
      SELECT p.*, c.name as category_name 
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      WHERE p.status = ?
    `).all(status) as any[];

    const result = pets.map(pet => {
      const tags = db.prepare(`
        SELECT t.id, t.name 
        FROM tags t 
        JOIN pet_tags pt ON t.id = pt.tag_id 
        WHERE pt.pet_id = ?
      `).all(pet.id) as any[];

      return {
        id: pet.id,
        name: pet.name,
        category: pet.category_id ? {
          id: pet.category_id,
          name: pet.category_name
        } : null,
        photoUrls: pet.photo_urls ? JSON.parse(pet.photo_urls) : [],
        tags: tags,
        status: pet.status
      };
    });

    // API spec expects array directly, not wrapped in data
    res.json(result);
  } catch (error) {
    console.error('Find by status error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// GET /api/v3/pet/findByTags - Find pets by tags (auth required per spec)
router.get('/findByTags', authMiddleware, (req: Request, res: Response) => {
  try {
    const tags = req.query.tags as string;
    if (!tags) {
      return res.status(400).json({ error: 'Tags parameter required' });
    }

    const tagNames = tags.split(',').map(t => t.trim());
    const placeholders = tagNames.map(() => '?').join(',');
    
    const pets = db.prepare(`
      SELECT DISTINCT p.*, c.name as category_name 
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      JOIN pet_tags pt ON p.id = pt.pet_id 
      JOIN tags t ON pt.tag_id = t.id 
      WHERE t.name IN (${placeholders})
    `).all(...tagNames) as any[];

    const result = pets.map(pet => {
      const petTags = db.prepare(`
        SELECT t.id, t.name 
        FROM tags t 
        JOIN pet_tags pt ON t.id = pt.tag_id 
        WHERE pt.pet_id = ?
      `).all(pet.id) as any[];

      return {
        id: pet.id,
        name: pet.name,
        category: pet.category_id ? {
          id: pet.category_id,
          name: pet.category_name
        } : null,
        photoUrls: pet.photo_urls ? JSON.parse(pet.photo_urls) : [],
        tags: petTags,
        status: pet.status
      };
    });

    // API spec expects array directly, not wrapped in data
    res.json(result);
  } catch (error) {
    console.error('Find by tags error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// POST /api/v3/pet - Add new pet (auth required per spec)
router.post('/', authMiddleware, (req: AuthRequest, res: Response) => {
  try {
    const { name, category, photoUrls, tags, status } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Pet name is required' });
    }

    const transaction = db.transaction(() => {
      // Insert or get category
      let categoryId = null;
      if (category?.name) {
        let cat = db.prepare('SELECT id FROM categories WHERE name = ?').get(category.name) as any;
        if (!cat) {
          const insertCat = db.prepare('INSERT INTO categories (name) VALUES (?)');
          const result = insertCat.run(category.name);
          categoryId = result.lastInsertRowid;
        } else {
          categoryId = cat.id;
        }
      }

      // Insert pet
      const insertPet = db.prepare(`
        INSERT INTO pets (name, category_id, photo_urls, status) 
        VALUES (?, ?, ?, ?)
      `);
      const petResult = insertPet.run(
        name,
        categoryId,
        photoUrls ? JSON.stringify(photoUrls) : null,
        status || 'available'
      );
      const petId = petResult.lastInsertRowid as number;

      // Insert tags
      if (tags && Array.isArray(tags)) {
        for (const tag of tags) {
          if (tag.name) {
            let tagRecord = db.prepare('SELECT id FROM tags WHERE name = ?').get(tag.name) as any;
            if (!tagRecord) {
              const insertTag = db.prepare('INSERT INTO tags (name) VALUES (?)');
              const tagResult = insertTag.run(tag.name);
              tagRecord = { id: tagResult.lastInsertRowid };
            }
            
            // Link pet to tag
            db.prepare('INSERT OR IGNORE INTO pet_tags (pet_id, tag_id) VALUES (?, ?)')
              .run(petId, tagRecord.id);
          }
        }
      }

      return petId;
    });

    const petId = transaction();
    const pet = getPetWithDetails(petId);
    // API spec expects pet object directly, not wrapped in data
    res.status(201).json(pet);
  } catch (error) {
    console.error('Create pet error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// PUT /api/v3/pet - Update existing pet (auth required per spec)
router.put('/', authMiddleware, (req: AuthRequest, res: Response) => {
  try {
    const { id, name, category, photoUrls, tags, status } = req.body;

    if (!id || !name) {
      return res.status(400).json({ error: 'Pet ID and name are required' });
    }

    // Check if pet exists and get current status
    const currentPet = db.prepare('SELECT status FROM pets WHERE id = ?').get(id) as any;
    if (!currentPet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    const transaction = db.transaction(() => {
      // Handle category
      let categoryId = null;
      if (category?.name) {
        let cat = db.prepare('SELECT id FROM categories WHERE name = ?').get(category.name) as any;
        if (!cat) {
          const insertCat = db.prepare('INSERT INTO categories (name) VALUES (?)');
          const result = insertCat.run(category.name);
          categoryId = result.lastInsertRowid;
        } else {
          categoryId = cat.id;
        }
      }

      // Update pet
      db.prepare(`
        UPDATE pets 
        SET name = ?, category_id = ?, photo_urls = ?, status = ? 
        WHERE id = ?
      `).run(
        name,
        categoryId,
        photoUrls ? JSON.stringify(photoUrls) : null,
        status || currentPet.status,
        id
      );

      // Remove existing tags
      db.prepare('DELETE FROM pet_tags WHERE pet_id = ?').run(id);

      // Insert new tags
      if (tags && Array.isArray(tags)) {
        for (const tag of tags) {
          if (tag.name) {
            let tagRecord = db.prepare('SELECT id FROM tags WHERE name = ?').get(tag.name) as any;
            if (!tagRecord) {
              const insertTag = db.prepare('INSERT INTO tags (name) VALUES (?)');
              const tagResult = insertTag.run(tag.name);
              tagRecord = { id: tagResult.lastInsertRowid };
            }
            
            db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)')
              .run(id, tagRecord.id);
          }
        }
      }
    });

    transaction();
    const pet = getPetWithDetails(id);
    // API spec expects pet object directly, not wrapped in data
    res.json(pet);
  } catch (error) {
    console.error('Update pet error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// GET /api/v3/pet/{petId} - Find pet by ID (NO AUTH per spec) - MUST BE AFTER SPECIAL ROUTES
router.get('/:petId', (req: Request, res: Response) => {
  try {
    const petId = parseInt(req.params.petId);
    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    const pet = getPetWithDetails(petId);
    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // API spec expects pet object directly, not wrapped in data
    res.json(pet);
  } catch (error) {
    console.error('Get pet error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// POST /api/v3/pet/{petId} - Update pet with form data (auth required per spec)
router.post('/:petId', authMiddleware, (req: AuthRequest, res: Response) => {
  try {
    const petId = parseInt(req.params.petId);
    const { name, status } = req.body;

    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId) as any;
    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    const updateFields = [];
    const params = [];

    if (name) {
      updateFields.push('name = ?');
      params.push(name);
    }
    if (status) {
      updateFields.push('status = ?');
      params.push(status);
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    params.push(petId);
    db.prepare(`UPDATE pets SET ${updateFields.join(', ')} WHERE id = ?`).run(...params);

    // No response body expected for this endpoint
    res.status(200).send();
  } catch (error) {
    console.error('Update pet form error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// DELETE /api/v3/pet/{petId} - Delete pet (auth required per spec)
router.delete('/:petId', authMiddleware, (req: Request, res: Response) => {
  try {
    const petId = parseInt(req.params.petId);
    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    const result = db.prepare('DELETE FROM pets WHERE id = ?').run(petId);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // No response body expected for this endpoint
    res.status(200).send();
  } catch (error) {
    console.error('Delete pet error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// POST /api/v3/pet/{petId}/uploadImage - Upload image (auth required per spec)
router.post('/:petId/uploadImage', 
  authMiddleware, 
  upload.single('file'),
  (req: AuthRequest, res: Response) => {
    try {
      const petId = parseInt(req.params.petId);
      if (isNaN(petId)) {
        return res.status(400).json({ error: 'Invalid pet ID' });
      }

      const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId) as any;
      if (!pet) {
        return res.status(404).json({ error: 'Pet not found' });
      }

      // In a real implementation, you'd upload to S3 or similar
      // For now, we'll just simulate adding the file path
      const fileName = req.file?.filename || 'uploaded-image.jpg';
      const imageUrl = `/uploads/${fileName}`;
      
      const currentUrls = pet.photo_urls ? JSON.parse(pet.photo_urls) : [];
      currentUrls.push(imageUrl);

      db.prepare('UPDATE pets SET photo_urls = ? WHERE id = ?')
        .run(JSON.stringify(currentUrls), petId);

      // API spec expects this response format
      res.json({
        code: 200,
        type: 'success',
        message: `Image uploaded successfully: ${imageUrl}`
      });
    } catch (error) {
      console.error('Upload image error:', error);
      res.status(500).json({ error: 'Server error' });
    }
  }
);

export default router;