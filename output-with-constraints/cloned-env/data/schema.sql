-- Swagger Petstore API Database Schema
-- Note: No CHECK constraints in schema - validation handled in application code

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

-- Users table (with role field for auth)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    email TEXT UNIQUE,
    password TEXT NOT NULL,
    phone TEXT,
    user_status INTEGER DEFAULT 0,
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

-- Orders table (with user_id for ownership tracking)
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER REFERENCES pets(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    quantity INTEGER DEFAULT 1,
    ship_date TEXT,
    status TEXT DEFAULT 'placed',
    complete INTEGER DEFAULT 0
);

-- Insert initial data for testing

-- Categories
INSERT INTO categories (name) VALUES 
    ('Dogs'),
    ('Cats'),
    ('Birds'),
    ('Fish');

-- Tags
INSERT INTO tags (name) VALUES 
    ('friendly'),
    ('energetic'),
    ('quiet'),
    ('small'),
    ('large'),
    ('trained');

-- Test users with proper bcrypt hash for password "password"
INSERT INTO users (username, first_name, last_name, email, password, phone, user_status, role) VALUES
    ('admin', 'Admin', 'User', 'admin@petstore.com', '$2b$10$QKu3ViFOt0WKM3kOmZrt2eDn2y7c/KLt6073vLknBCH1ajvEIffci', '555-0001', 1, 'admin'),
    ('storeowner', 'Store', 'Owner', 'owner@petstore.com', '$2b$10$QKu3ViFOt0WKM3kOmZrt2eDn2y7c/KLt6073vLknBCH1ajvEIffci', '555-0002', 1, 'store_owner'),
    ('customer1', 'John', 'Doe', 'john@example.com', '$2b$10$QKu3ViFOt0WKM3kOmZrt2eDn2y7c/KLt6073vLknBCH1ajvEIffci', '555-0003', 1, 'customer'),
    ('customer2', 'Jane', 'Smith', 'jane@example.com', '$2b$10$QKu3ViFOt0WKM3kOmZrt2eDn2y7c/KLt6073vLknBCH1ajvEIffci', '555-0004', 1, 'customer');

-- Sample pets
INSERT INTO pets (name, category_id, photo_urls, status) VALUES
    ('Buddy', 1, '["https://example.com/buddy.jpg"]', 'available'),
    ('Luna', 2, '["https://example.com/luna.jpg"]', 'pending'),
    ('Charlie', 1, '["https://example.com/charlie.jpg"]', 'sold'),
    ('Bella', 2, '["https://example.com/bella.jpg"]', 'available'),
    ('Max', 1, '["https://example.com/max.jpg"]', 'available');

-- Pet tags relationships
INSERT INTO pet_tags (pet_id, tag_id) VALUES
    (1, 1), (1, 2), -- Buddy: friendly, energetic
    (2, 3), (2, 4), -- Luna: quiet, small
    (3, 1), (3, 6), -- Charlie: friendly, trained
    (4, 1), (4, 4), -- Bella: friendly, small
    (5, 2), (5, 5); -- Max: energetic, large

-- Sample orders
INSERT INTO orders (pet_id, user_id, quantity, ship_date, status, complete) VALUES
    (2, 3, 1, '2024-01-15', 'placed', 0), -- customer1 ordered Luna (pending pet)
    (3, 4, 1, '2024-01-10', 'delivered', 1); -- customer2 ordered Charlie (sold pet)