-- Categories table
CREATE TABLE categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

-- Tags table
CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

-- Users table with role field for RBAC
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  password TEXT NOT NULL,
  phone TEXT,
  user_status INTEGER DEFAULT 0,
  role TEXT DEFAULT 'customer',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pets table (removed CHECK constraint as required)
CREATE TABLE pets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category_id INTEGER REFERENCES categories(id),
  photo_urls TEXT,
  status TEXT DEFAULT 'available',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pet-Tags junction table
CREATE TABLE pet_tags (
  pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
  tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (pet_id, tag_id)
);

-- Orders table with user_id for ownership tracking (removed CHECK constraint)
CREATE TABLE orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pet_id INTEGER REFERENCES pets(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity INTEGER NOT NULL DEFAULT 1,
  ship_date TEXT,
  status TEXT DEFAULT 'placed',
  complete INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data

-- Categories
INSERT INTO categories (name) VALUES
('Dogs'),
('Cats'),
('Birds'),
('Fish');

-- Tags
INSERT INTO tags (name) VALUES
('friendly'),
('playful'),
('calm'),
('energetic'),
('trained'),
('young'),
('adult');

-- Users with different roles
INSERT INTO users (username, first_name, last_name, email, password, phone, role) VALUES
('admin', 'Admin', 'User', 'admin@petstore.com', '$2b$10$7Z1Z1Z1Z1Z1Z1Z1Z1Z1Z1e', '555-0001', 'admin'),
('storeowner', 'Store', 'Owner', 'owner@petstore.com', '$2b$10$7Z1Z1Z1Z1Z1Z1Z1Z1Z1Z1e', '555-0002', 'store_owner'),
('customer1', 'John', 'Doe', 'john@example.com', '$2b$10$7Z1Z1Z1Z1Z1Z1Z1Z1Z1Z1e', '555-0003', 'customer'),
('customer2', 'Jane', 'Smith', 'jane@example.com', '$2b$10$7Z1Z1Z1Z1Z1Z1Z1Z1Z1Z1e', '555-0004', 'customer');

-- Pets with different statuses
INSERT INTO pets (name, category_id, photo_urls, status) VALUES
('Buddy', 1, '["https://example.com/buddy.jpg"]', 'available'),
('Fluffy', 2, '["https://example.com/fluffy.jpg"]', 'available'),
('Tweety', 3, '["https://example.com/tweety.jpg"]', 'pending'),
('Nemo', 4, '["https://example.com/nemo.jpg"]', 'sold'),
('Max', 1, '["https://example.com/max.jpg"]', 'available');

-- Pet-Tag relationships
INSERT INTO pet_tags (pet_id, tag_id) VALUES
(1, 1), (1, 2), -- Buddy: friendly, playful
(2, 1), (2, 3), -- Fluffy: friendly, calm
(3, 4), (3, 6), -- Tweety: energetic, young
(4, 3), (4, 7), -- Nemo: calm, adult
(5, 5), (5, 4); -- Max: trained, energetic

-- Sample orders
INSERT INTO orders (pet_id, user_id, quantity, status) VALUES
(3, 3, 1, 'placed'),  -- customer1 ordered Tweety (pending)
(4, 4, 1, 'delivered'); -- customer2 ordered Nemo (sold)