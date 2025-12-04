import { Router } from 'express';
import db from '../lib/db.js';
import { verifyAuth, requireRole, AuthRequest } from '../lib/auth.js';
import multer from 'multer';

const router = Router();
const upload = multer({ dest: 'uploads/' });

// GET /api/v3/pet/findByStatus (must come before /:petId to avoid conflicts)
router.get('/findByStatus', verifyAuth, (req, res) => {
  try {
    const status = req.query.status as string;
    if (!status) {
      return res.status(400).json({ error: 'Status parameter is required' });
    }

    const pets = db.prepare(`
      SELECT p.*, c.name as category_name, c.id as category_id
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      WHERE p.status = ?
    `).all(status) as any[];

    const response = pets.map(pet => {
      const photos = db.prepare('SELECT photo_url FROM pet_photos WHERE pet_id = ?').all(pet.id) as any[];
      const photoUrls = photos.map(p => p.photo_url);

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
        photoUrls: photoUrls,
        tags: tags,
        status: pet.status
      };
    });

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/findByTags (must come before /:petId to avoid conflicts)
router.get('/findByTags', verifyAuth, (req, res) => {
  try {
    const tags = req.query.tags as string;
    if (!tags) {
      return res.status(400).json({ error: 'Tags parameter is required' });
    }

    const tagList = tags.split(',').map(t => t.trim());
    const placeholders = tagList.map(() => '?').join(',');

    const pets = db.prepare(`
      SELECT DISTINCT p.*, c.name as category_name, c.id as category_id
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      JOIN pet_tags pt ON p.id = pt.pet_id
      JOIN tags t ON pt.tag_id = t.id
      WHERE t.name IN (${placeholders})
    `).all(...tagList) as any[];

    const response = pets.map(pet => {
      const photos = db.prepare('SELECT photo_url FROM pet_photos WHERE pet_id = ?').all(pet.id) as any[];
      const photoUrls = photos.map(p => p.photo_url);

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
        photoUrls: photoUrls,
        tags: petTags,
        status: pet.status
      };
    });

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/{petId}
router.get('/:petId', (req, res) => {
  try {
    const petId = parseInt(req.params.petId);
    
    const pet = db.prepare(`
      SELECT p.*, c.name as category_name, c.id as category_id
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      WHERE p.id = ?
    `).get(petId) as any;

    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // Get photo URLs
    const photos = db.prepare('SELECT photo_url FROM pet_photos WHERE pet_id = ?').all(petId) as any[];
    const photoUrls = photos.map(p => p.photo_url);

    // Get tags
    const tags = db.prepare(`
      SELECT t.id, t.name 
      FROM tags t 
      JOIN pet_tags pt ON t.id = pt.tag_id 
      WHERE pt.pet_id = ?
    `).all(petId) as any[];

    const response = {
      id: pet.id,
      name: pet.name,
      category: pet.category_id ? {
        id: pet.category_id,
        name: pet.category_name
      } : null,
      photoUrls: photoUrls,
      tags: tags,
      status: pet.status
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet
router.post('/', verifyAuth, requireRole(['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const { name, category, photoUrls, tags, status } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Name is required' });
    }

    // Insert pet
    const insertPet = db.prepare(`
      INSERT INTO pets (name, category_id, status) 
      VALUES (?, ?, ?)
    `);
    const result = insertPet.run(name, category?.id || null, status || 'available');
    const petId = result.lastInsertRowid as number;

    // Insert photo URLs
    if (photoUrls && Array.isArray(photoUrls)) {
      const insertPhoto = db.prepare('INSERT INTO pet_photos (pet_id, photo_url) VALUES (?, ?)');
      for (const url of photoUrls) {
        insertPhoto.run(petId, url);
      }
    }

    // Insert tags
    if (tags && Array.isArray(tags)) {
      const insertPetTag = db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)');
      for (const tag of tags) {
        if (tag.id) {
          insertPetTag.run(petId, tag.id);
        }
      }
    }

    // Return the created pet
    const createdPet = db.prepare(`
      SELECT p.*, c.name as category_name, c.id as category_id
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      WHERE p.id = ?
    `).get(petId) as any;

    const photos = db.prepare('SELECT photo_url FROM pet_photos WHERE pet_id = ?').all(petId) as any[];
    const petTags = db.prepare(`
      SELECT t.id, t.name 
      FROM tags t 
      JOIN pet_tags pt ON t.id = pt.tag_id 
      WHERE pt.pet_id = ?
    `).all(petId) as any[];

    const response = {
      id: createdPet.id,
      name: createdPet.name,
      category: createdPet.category_id ? {
        id: createdPet.category_id,
        name: createdPet.category_name
      } : null,
      photoUrls: photos.map(p => p.photo_url),
      tags: petTags,
      status: createdPet.status
    };

    res.status(201).json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/v3/pet
router.put('/', verifyAuth, requireRole(['store_owner', 'admin']), (req: AuthRequest, res) => {
  try {
    const { id, name, category, photoUrls, tags, status } = req.body;

    if (!id) {
      return res.status(400).json({ error: 'Pet ID is required' });
    }

    // Check if pet exists
    const existingPet = db.prepare('SELECT * FROM pets WHERE id = ?').get(id) as any;
    if (!existingPet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // Special check: only admin can relist sold pets
    if (existingPet.status === 'sold' && status === 'available') {
      if (req.user?.role !== 'admin') {
        return res.status(403).json({ error: 'Only admin can relist sold pets' });
      }
    }

    // Update pet
    const updatePet = db.prepare(`
      UPDATE pets 
      SET name = ?, category_id = ?, status = ?
      WHERE id = ?
    `);
    updatePet.run(name || existingPet.name, category?.id || existingPet.category_id, status || existingPet.status, id);

    // Update photo URLs
    if (photoUrls && Array.isArray(photoUrls)) {
      db.prepare('DELETE FROM pet_photos WHERE pet_id = ?').run(id);
      const insertPhoto = db.prepare('INSERT INTO pet_photos (pet_id, photo_url) VALUES (?, ?)');
      for (const url of photoUrls) {
        insertPhoto.run(id, url);
      }
    }

    // Update tags
    if (tags && Array.isArray(tags)) {
      db.prepare('DELETE FROM pet_tags WHERE pet_id = ?').run(id);
      const insertPetTag = db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)');
      for (const tag of tags) {
        if (tag.id) {
          insertPetTag.run(id, tag.id);
        }
      }
    }

    // Return the updated pet
    const updatedPet = db.prepare(`
      SELECT p.*, c.name as category_name, c.id as category_id
      FROM pets p 
      LEFT JOIN categories c ON p.category_id = c.id 
      WHERE p.id = ?
    `).get(id) as any;

    const photos = db.prepare('SELECT photo_url FROM pet_photos WHERE pet_id = ?').all(id) as any[];
    const petTags = db.prepare(`
      SELECT t.id, t.name 
      FROM tags t 
      JOIN pet_tags pt ON t.id = pt.tag_id 
      WHERE pt.pet_id = ?
    `).all(id) as any[];

    const response = {
      id: updatedPet.id,
      name: updatedPet.name,
      category: updatedPet.category_id ? {
        id: updatedPet.category_id,
        name: updatedPet.category_name
      } : null,
      photoUrls: photos.map(p => p.photo_url),
      tags: petTags,
      status: updatedPet.status
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet/{petId}
router.post('/:petId', verifyAuth, requireRole(['store_owner', 'admin']), (req, res) => {
  try {
    const petId = parseInt(req.params.petId);
    const { name, status } = req.body;

    const existingPet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId) as any;
    if (!existingPet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    const updatePet = db.prepare(`
      UPDATE pets 
      SET name = ?, status = ?
      WHERE id = ?
    `);
    updatePet.run(name || existingPet.name, status || existingPet.status, petId);

    res.json({ message: 'Pet updated successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/v3/pet/{petId}
router.delete('/:petId', verifyAuth, requireRole(['store_owner', 'admin']), (req, res) => {
  try {
    const petId = parseInt(req.params.petId);

    // Pre-condition: check for active orders
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count 
      FROM orders 
      WHERE pet_id = ? AND status IN ('placed', 'approved')
    `).get(petId) as any;

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ error: 'Cannot delete pet with active orders' });
    }

    const deletePet = db.prepare('DELETE FROM pets WHERE id = ?');
    const result = deletePet.run(petId);

    if (result.changes === 0) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    res.json({ message: 'Pet deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet/{petId}/uploadImage
router.post('/:petId/uploadImage', verifyAuth, requireRole(['store_owner', 'admin']), upload.single('file'), (req, res) => {
  try {
    const petId = parseInt(req.params.petId);
    const { additionalMetadata } = req.body;

    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // In a real implementation, you'd upload to S3 or similar
    // For now, we'll just store the local file path
    const photoUrl = `/uploads/${req.file.filename}`;

    const insertPhoto = db.prepare('INSERT INTO pet_photos (pet_id, photo_url) VALUES (?, ?)');
    insertPhoto.run(petId, photoUrl);

    res.json({
      code: 200,
      type: 'success',
      message: `Image uploaded successfully. Metadata: ${additionalMetadata || 'none'}`
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;