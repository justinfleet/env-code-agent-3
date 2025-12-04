import express, { Request, Response } from 'express';
import db from '../lib/db';
import { authenticateToken, requireRoles, AuthenticatedRequest } from './auth';
import multer from 'multer';

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// Helper function to validate pet status transitions
function isValidStatusTransition(currentStatus: string, newStatus: string, userRole: string): boolean {
  // Admin can do any transition (including sold -> available)
  if (userRole === 'admin') {
    return true;
  }

  // Store owner cannot change sold pets back to available
  if (currentStatus === 'sold' && newStatus === 'available') {
    return false;
  }

  return true;
}

// Helper function to build pet response with relationships
function buildPetResponse(petRow: any): any {
  const pet = {
    id: petRow.id,
    name: petRow.name,
    status: petRow.status,
    category: null as any,
    photoUrls: petRow.photo_urls ? JSON.parse(petRow.photo_urls) : [],
    tags: [] as any[]
  };

  // Get category
  if (petRow.category_id) {
    const category = db.prepare('SELECT * FROM categories WHERE id = ?').get(petRow.category_id);
    if (category) {
      pet.category = { id: category.id, name: category.name };
    }
  }

  // Get tags
  const tags = db.prepare(`
    SELECT t.id, t.name FROM tags t
    JOIN pet_tags pt ON t.id = pt.tag_id
    WHERE pt.pet_id = ?
  `).all(petRow.id);
  pet.tags = tags;

  return pet;
}

// PUT /api/v3/pet - Update an existing pet
router.put('/', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id, name, category, photoUrls, tags, status } = req.body;

    if (!id) {
      return res.status(400).json({ error: 'Pet ID is required' });
    }

    // Get current pet
    const currentPet = db.prepare('SELECT * FROM pets WHERE id = ?').get(id);
    if (!currentPet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    // Validate status transition (exact message from business requirements)
    if (status && !isValidStatusTransition(currentPet.status, status, req.user!.role)) {
      return res.status(400).json({ 
        message: 'Invalid status transition. Admin required to change sold pets back to available.' 
      });
    }

    const transaction = db.transaction(() => {
      // Handle category
      let categoryId = null;
      if (category && category.name) {
        let existingCategory = db.prepare('SELECT id FROM categories WHERE name = ?').get(category.name);
        if (!existingCategory) {
          const insertCategory = db.prepare('INSERT INTO categories (name) VALUES (?)');
          const result = insertCategory.run(category.name);
          categoryId = result.lastInsertRowid;
        } else {
          categoryId = existingCategory.id;
        }
      }

      // Update pet
      const updatePet = db.prepare(`
        UPDATE pets 
        SET name = ?, category_id = ?, photo_urls = ?, status = ?
        WHERE id = ?
      `);
      updatePet.run(
        name || currentPet.name,
        categoryId || currentPet.category_id,
        photoUrls ? JSON.stringify(photoUrls) : currentPet.photo_urls,
        status || currentPet.status,
        id
      );

      // Handle tags if provided
      if (tags && Array.isArray(tags)) {
        // Remove existing tags
        db.prepare('DELETE FROM pet_tags WHERE pet_id = ?').run(id);

        // Add new tags
        for (const tag of tags) {
          if (tag.name) {
            let existingTag = db.prepare('SELECT id FROM tags WHERE name = ?').get(tag.name);
            let tagId;
            
            if (!existingTag) {
              const insertTag = db.prepare('INSERT INTO tags (name) VALUES (?)');
              const result = insertTag.run(tag.name);
              tagId = result.lastInsertRowid;
            } else {
              tagId = existingTag.id;
            }

            db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)').run(id, tagId);
          }
        }
      }
    });

    transaction();

    // Return updated pet
    const updatedPet = db.prepare('SELECT * FROM pets WHERE id = ?').get(id);
    const response = buildPetResponse(updatedPet);
    res.json(response);

  } catch (error) {
    console.error('Error updating pet:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet - Add a new pet
router.post('/', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { name, category, photoUrls, tags, status } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Pet name is required' });
    }

    const transaction = db.transaction(() => {
      // Handle category
      let categoryId = null;
      if (category && category.name) {
        let existingCategory = db.prepare('SELECT id FROM categories WHERE name = ?').get(category.name);
        if (!existingCategory) {
          const insertCategory = db.prepare('INSERT INTO categories (name) VALUES (?)');
          const result = insertCategory.run(category.name);
          categoryId = result.lastInsertRowid;
        } else {
          categoryId = existingCategory.id;
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
      const petId = petResult.lastInsertRowid;

      // Handle tags
      if (tags && Array.isArray(tags)) {
        for (const tag of tags) {
          if (tag.name) {
            let existingTag = db.prepare('SELECT id FROM tags WHERE name = ?').get(tag.name);
            let tagId;
            
            if (!existingTag) {
              const insertTag = db.prepare('INSERT INTO tags (name) VALUES (?)');
              const result = insertTag.run(tag.name);
              tagId = result.lastInsertRowid;
            } else {
              tagId = existingTag.id;
            }

            db.prepare('INSERT INTO pet_tags (pet_id, tag_id) VALUES (?, ?)').run(petId, tagId);
          }
        }
      }

      return petId;
    });

    const petId = transaction();

    // Return created pet
    const newPet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);
    const response = buildPetResponse(newPet);
    res.json(response);

  } catch (error) {
    console.error('Error creating pet:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/findByStatus
router.get('/findByStatus', authenticateToken, (req: AuthenticatedRequest, res: Response) => {
  try {
    const { status } = req.query;

    if (!status) {
      return res.status(400).json({ error: 'Status parameter is required' });
    }

    const pets = db.prepare('SELECT * FROM pets WHERE status = ?').all(status);
    const response = pets.map(pet => buildPetResponse(pet));
    res.json(response);

  } catch (error) {
    console.error('Error finding pets by status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/findByTags
router.get('/findByTags', authenticateToken, (req: AuthenticatedRequest, res: Response) => {
  try {
    const { tags } = req.query;

    if (!tags) {
      return res.status(400).json({ error: 'Tags parameter is required' });
    }

    const tagArray = Array.isArray(tags) ? tags : [tags];
    const placeholders = tagArray.map(() => '?').join(',');

    const pets = db.prepare(`
      SELECT DISTINCT p.* FROM pets p
      JOIN pet_tags pt ON p.id = pt.pet_id
      JOIN tags t ON pt.tag_id = t.id
      WHERE t.name IN (${placeholders})
    `).all(...tagArray);

    const response = pets.map(pet => buildPetResponse(pet));
    res.json(response);

  } catch (error) {
    console.error('Error finding pets by tags:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v3/pet/:petId - No auth required per spec
router.get('/:petId', (req: Request, res: Response) => {
  try {
    const { petId } = req.params;
    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);

    if (!pet) {
      return res.status(404).json({ error: 'Pet not found' });
    }

    const response = buildPetResponse(pet);
    res.json(response);

  } catch (error) {
    console.error('Error getting pet:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/v3/pet/:petId - Update pet with form data
router.post('/:petId', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { petId } = req.params;
    const { name, status } = req.body;

    // Get current pet
    const currentPet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);
    if (!currentPet) {
      return res.status(404).json({ code: 404, type: 'error', message: 'Pet not found' });
    }

    // Validate status transition (exact message from business requirements)
    if (status && !isValidStatusTransition(currentPet.status, status, req.user!.role)) {
      return res.status(400).json({ 
        code: 400,
        type: 'error', 
        message: 'Invalid status transition. Admin required to change sold pets back to available.' 
      });
    }

    // Update pet
    const updatePet = db.prepare('UPDATE pets SET name = ?, status = ? WHERE id = ?');
    updatePet.run(
      name || currentPet.name,
      status || currentPet.status,
      petId
    );

    res.json({ code: 200, type: 'success', message: 'Pet updated successfully' });

  } catch (error) {
    console.error('Error updating pet:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

// DELETE /api/v3/pet/:petId
router.delete('/:petId', authenticateToken, requireRoles(['store_owner', 'admin']), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { petId } = req.params;

    // Pre-condition check: Cannot delete pets with active orders (exact message from business requirements)
    const activeOrdersCount = db.prepare(`
      SELECT COUNT(*) as count FROM orders 
      WHERE pet_id = ? AND status IN ('placed', 'approved')
    `).get(petId) as any;

    if (activeOrdersCount.count > 0) {
      return res.status(400).json({ 
        code: 400, 
        type: 'error', 
        message: 'Cannot delete pet with active orders' 
      });
    }

    // Check if pet exists
    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);
    if (!pet) {
      return res.status(404).json({ code: 404, type: 'error', message: 'Pet not found' });
    }

    // Delete pet (CASCADE will handle pet_tags)
    db.prepare('DELETE FROM pets WHERE id = ?').run(petId);

    res.json({ code: 200, type: 'success', message: 'Pet deleted successfully' });

  } catch (error) {
    console.error('Error deleting pet:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

// POST /api/v3/pet/:petId/uploadImage
router.post('/:petId/uploadImage', authenticateToken, requireRoles(['store_owner', 'admin']), upload.single('file'), (req: AuthenticatedRequest, res: Response) => {
  try {
    const { petId } = req.params;
    const { additionalMetadata } = req.body;

    // Check if pet exists
    const pet = db.prepare('SELECT * FROM pets WHERE id = ?').get(petId);
    if (!pet) {
      return res.status(404).json({ code: 404, type: 'error', message: 'Pet not found' });
    }

    // In a real implementation, you would upload the file to cloud storage
    // For this demo, we'll just simulate adding a URL to the photoUrls array
    let photoUrls = pet.photo_urls ? JSON.parse(pet.photo_urls) : [];
    const newPhotoUrl = `https://example.com/uploads/${petId}/${Date.now()}.jpg`;
    photoUrls.push(newPhotoUrl);

    // Update pet with new photo URL
    db.prepare('UPDATE pets SET photo_urls = ? WHERE id = ?').run(JSON.stringify(photoUrls), petId);

    res.json({ 
      code: 200, 
      type: 'success', 
      message: `Image uploaded successfully: ${newPhotoUrl}` 
    });

  } catch (error) {
    console.error('Error uploading image:', error);
    res.status(500).json({ code: 500, type: 'error', message: 'Internal server error' });
  }
});

export default router;