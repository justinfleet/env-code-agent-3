import express from 'express';
import db from '../lib/db';
import { authenticateToken, requireRoles, AuthRequest } from '../lib/auth';
import multer from 'multer';

const router = express.Router();
const upload = multer({ dest: 'uploads/' });

// Helper function to validate pet status
function isValidStatus(status: string): boolean {
  return ['available', 'pending', 'sold'].includes(status);
}

// Helper function to get pet with category and tags
function getPetWithDetails(id: number) {
  const pet = db.prepare(`
    SELECT p.*, c.name as category_name, c.id as category_id
    FROM pets p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.id = ?
  `).get(id);

  if (!pet) return null;

  const tags = db.prepare(`
    SELECT t.id, t.name
    FROM tags t
    JOIN pet_tags pt ON t.id = pt.tag_id
    WHERE pt.pet_id = ?
  `).all(id);

  return {
    id: pet.id,
    name: pet.name,
    category: pet.category_id ? { id: pet.category_id, name: pet.category_name } : null,
    photoUrls: pet.photo_urls ? JSON.parse(pet.photo_urls) : [],
    tags: tags,
    status: pet.status
  };
}

// PUT /api/v3/pet - Update existing pet
router.put('/', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const { id, name, category, photoUrls, tags, status } = req.body;

    if (!id || !name) {
      return res.status(400).json({ error: 'Pet ID and name are required' });
    }

    if (status && !isValidStatus(status)) {
      return res.status(400).json({ error: 'Invalid status. Must be available, pending, or sold' });
    }

    // Check if changing sold to available (admin only)
    if (status === 'available') {
      const currentPet = db.prepare('SELECT status FROM pets WHERE id = ?').get(id);
      if (currentPet && (currentPet as any).status === 'sold' && req.user?.role !== 'admin') {
        return res.status(403).json({ error: 'Only admin can relist sold pets' });
      }
    }

    const transaction = db.transaction(() => {
      // Handle category
      let categoryId = null;
      if (category && category.name) {
        const existingCategory = db.prepare('SELECT id FROM categories WHERE name = ?').get(category.name);
        if (existingCategory) {
          categoryId = (existingCategory as any).id;
        } else {
          const categoryResult = db.prepare('INSERT INTO categories (name) VALUES (?)').run(category.name);
          categoryId = categoryResult.lastInsertRowid;
        }
      }

      // Update pet
      const updatePet = db.prepare(`
        UPDATE pets 
        SET name = ?, category_id = ?, photo_urls = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `);
      
      const result = updatePet.run(
        name, 
        categoryId,
        photoUrls ? JSON.stringify(photoUrls) : null,
        status || 'available',
        id
      );

      if (result.changes === 0) {
        throw new Error('Pet not found');
      }

      // Handle tags
      if (tags && Array.isArray(tags)) {
        // Remove existing tags
        db.prepare('DELETE FROM pet_tags WHERE pet_id = ?').run(id);
        
        // Add new tags
        for (const tag of tags) {
          if (tag.name) {
            let tagId;
            const existingTag = db.prepare('SELECT id FROM tags WHERE name = ?').get(tag.name);
            if (existingTag) {
              tagId = (existingTag as any).id;
            } else {
              const tagResult = db.prepare('INSERT INTO tags (name) VALUES (?)').run(tag.name);
              tagId = tagResult.lastInsertRowid;
            }
            db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)').run(id, tagId);
          }
        }
      }
    });

    transaction();

    const updatedPet = getPetWithDetails(id);
    res.json({ data: updatedPet });
  } catch (error) {
    console.error('Update pet error:', error);
    if ((error as Error).message === 'Pet not found') {
      res.status(404).json({ error: 'Pet not found' });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

// POST /api/v3/pet - Add new pet
router.post('/', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const { name, category, photoUrls, tags, status } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Pet name is required' });
    }

    if (status && !isValidStatus(status)) {
      return res.status(400).json({ error: 'Invalid status. Must be available, pending, or sold' });
    }

    const transaction = db.transaction(() => {
      // Handle category
      let categoryId = null;
      if (category && category.name) {
        const existingCategory = db.prepare('SELECT id FROM categories WHERE name = ?').get(category.name);
        if (existingCategory) {
          categoryId = (existingCategory as any).id;
        } else {
          const categoryResult = db.prepare('INSERT INTO categories (name) VALUES (?)').run(category.name);
          categoryId = categoryResult.lastInsertRowid;
        }
      }

      // Insert pet
      const insertPet = db.prepare(`
        INSERT INTO pets (name, category_id, photo_urls, status)
        VALUES (?, ?, ?, ?)
      `);
      
      const result = insertPet.run(
        name, 
        categoryId,
        photoUrls ? JSON.stringify(photoUrls) : null,
        status || 'available'
      );

      const petId = result.lastInsertRowid;

      // Handle tags
      if (tags && Array.isArray(tags)) {
        for (const tag of tags) {
          if (tag.name) {
            let tagId;
            const existingTag = db.prepare('SELECT id FROM tags WHERE name = ?').get(tag.name);
            if (existingTag) {
              tagId = (existingTag as any).id;
            } else {
              const tagResult = db.prepare('INSERT INTO tags (name) VALUES (?)').run(tag.name);
              tagId = tagResult.lastInsertRowid;
            }
            db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)').run(petId, tagId);
          }
        }
      }

      return petId;
    });

    const petId = transaction();
    const newPet = getPetWithDetails(petId as number);
    res.status(201).json({ data: newPet });
  } catch (error) {
    console.error('Create pet error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/findByStatus
router.get('/findByStatus', authenticateToken, (req: AuthRequest, res) => {
  try {
    const { status } = req.query;

    if (!status) {
      return res.status(400).json({ error: 'Status parameter is required' });
    }

    const statusArray = Array.isArray(status) ? status : [status];
    const validStatuses = statusArray.filter(s => isValidStatus(s as string));

    if (validStatuses.length === 0) {
      return res.status(400).json({ error: 'Invalid status values' });
    }

    const placeholders = validStatuses.map(() => '?').join(',');
    const pets = db.prepare(`
      SELECT p.*, c.name as category_name, c.id as category_id
      FROM pets p
      LEFT JOIN categories c ON p.category_id = c.id
      WHERE p.status IN (${placeholders})
    `).all(...validStatuses);

    const petsWithDetails = pets.map((pet: any) => {
      const tags = db.prepare(`
        SELECT t.id, t.name
        FROM tags t
        JOIN pet_tags pt ON t.id = pt.tag_id
        WHERE pt.pet_id = ?
      `).all(pet.id);

      return {
        id: pet.id,
        name: pet.name,
        category: pet.category_id ? { id: pet.category_id, name: pet.category_name } : null,
        photoUrls: pet.photo_urls ? JSON.parse(pet.photo_urls) : [],
        tags: tags,
        status: pet.status
      };
    });

    res.json({ data: petsWithDetails });
  } catch (error) {
    console.error('Find by status error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/findByTags
router.get('/findByTags', authenticateToken, (req: AuthRequest, res) => {
  try {
    const { tags } = req.query;

    if (!tags) {
      return res.status(400).json({ error: 'Tags parameter is required' });
    }

    const tagArray = Array.isArray(tags) ? tags : [tags];
    const placeholders = tagArray.map(() => '?').join(',');

    const pets = db.prepare(`
      SELECT DISTINCT p.*, c.name as category_name, c.id as category_id
      FROM pets p
      LEFT JOIN categories c ON p.category_id = c.id
      JOIN pet_tags pt ON p.id = pt.pet_id
      JOIN tags t ON pt.tag_id = t.id
      WHERE t.name IN (${placeholders})
    `).all(...tagArray);

    const petsWithDetails = pets.map((pet: any) => {
      const petTags = db.prepare(`
        SELECT t.id, t.name
        FROM tags t
        JOIN pet_tags pt ON t.id = pt.tag_id
        WHERE pt.pet_id = ?
      `).all(pet.id);

      return {
        id: pet.id,
        name: pet.name,
        category: pet.category_id ? { id: pet.category_id, name: pet.category_name } : null,
        photoUrls: pet.photo_urls ? JSON.parse(pet.photo_urls) : [],
        tags: petTags,
        status: pet.status
      };
    });

    res.json({ data: petsWithDetails });
  } catch (error) {
    console.error('Find by tags error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/:petId
router.get('/:petId', (req, res) => {
  try {
    const petId = parseInt(req.params.petId);

    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    const pet = getPetWithDetails(petId);

    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    res.json({ data: pet });
  } catch (error) {
    console.error('Get pet error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet/:petId - Update pet with form data
router.post('/:petId', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const petId = parseInt(req.params.petId);
    const { name, status } = req.body;

    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    if (status && !isValidStatus(status)) {
      return res.status(400).json({ error: 'Invalid status. Must be available, pending, or sold' });
    }

    const updateFields = [];
    const values = [];

    if (name) {
      updateFields.push('name = ?');
      values.push(name);
    }
    
    if (status) {
      updateFields.push('status = ?');
      values.push(status);
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    updateFields.push('updated_at = CURRENT_TIMESTAMP');
    values.push(petId);

    const result = db.prepare(`
      UPDATE pets 
      SET ${updateFields.join(', ')}
      WHERE id = ?
    `).run(...values);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    res.json({ data: { message: 'Pet updated successfully' } });
  } catch (error) {
    console.error('Update pet form error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/pet/:petId
router.delete('/:petId', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const petId = parseInt(req.params.petId);

    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    // Pre-condition check: cannot delete pet with active orders
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count FROM orders 
      WHERE pet_id = ? AND status IN ('placed', 'approved')
    `).get(petId) as { count: number };

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ error: 'Cannot delete pet with active orders' });
    }

    const result = db.prepare('DELETE FROM pets WHERE id = ?').run(petId);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    res.json({ data: { message: 'Pet deleted successfully' } });
  } catch (error) {
    console.error('Delete pet error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet/:petId/uploadImage
router.post('/:petId/uploadImage', authenticateToken, requireRoles(['store_owner', 'admin']), upload.single('file'), (req: AuthRequest, res) => {
  try {
    const petId = parseInt(req.params.petId);
    const { additionalMetadata } = req.body;

    if (isNaN(petId)) {
      return res.status(400).json({ error: 'Invalid pet ID' });
    }

    // Check if pet exists
    const pet = db.prepare('SELECT id FROM pets WHERE id = ?').get(petId);
    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // In a real implementation, you would save the file to S3 or similar
    // For this demo, we'll just return a success response
    const imageUrl = `/uploads/pets/${petId}/${Date.now()}.jpg`;

    res.json({
      data: {
        code: 200,
        type: 'success',
        message: `Image uploaded successfully. URL: ${imageUrl}${additionalMetadata ? '. Metadata: ' + additionalMetadata : ''}`
      }
    });
  } catch (error) {
    console.error('Upload image error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;