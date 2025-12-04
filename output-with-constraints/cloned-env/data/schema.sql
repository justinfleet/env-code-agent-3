-- Drop existing tables if they exist
DROP TABLE IF EXISTS pet_tags;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS pets;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

-- Categories table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Tags table
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
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
    user_status INTEGER DEFAULT 1,
    role TEXT DEFAULT 'customer'
);

-- Pets table
CREATE TABLE pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    photo_urls TEXT,
    status TEXT DEFAULT 'available'
);

-- Pet tags junction table
CREATE TABLE pet_tags (
    pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (pet_id, tag_id)
);

-- Orders table with user_id for ownership tracking
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER REFERENCES pets(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    quantity INTEGER DEFAULT 1,
    ship_date TEXT,
    status TEXT DEFAULT 'placed',
    complete INTEGER DEFAULT 0
);

-- Insert sample data
INSERT INTO categories (name) VALUES 
('Dogs'), 
('Cats'), 
('Birds'), 
('Fish');

INSERT INTO tags (name) VALUES 
('friendly'), 
('trained'), 
('young'), 
('active'), 
('calm');

-- Create test users with simple passwords for validation
-- The hash $2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi is for "password"
INSERT INTO users (username, first_name, last_name, email, password, role) VALUES 
('testuser', 'Test', 'User', 'test@example.com', '$2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'customer'),
('admin', 'Admin', 'User', 'admin@petstore.com', '$2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin'),
('customer', 'John', 'Doe', 'customer@example.com', '$2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'customer');

INSERT INTO pets (name, category_id, photo_urls, status) VALUES 
('Buddy', 1, '["https://example.com/buddy.jpg"]', 'available'),
('Whiskers', 2, '["https://example.com/whiskers.jpg"]', 'available'),
('Tweety', 3, '["https://example.com/tweety.jpg"]', 'pending'),
('Nemo', 4, '["https://example.com/nemo.jpg"]', 'sold');

INSERT INTO pet_tags (pet_id, tag_id) VALUES 
(1, 1), (1, 2), (1, 4),
(2, 1), (2, 5),
(3, 3), (3, 4),
(4, 3);

INSERT INTO orders (pet_id, user_id, quantity, status, complete) VALUES 
(3, 3, 1, 'placed', 0),
(4, 3, 1, 'delivered', 1);