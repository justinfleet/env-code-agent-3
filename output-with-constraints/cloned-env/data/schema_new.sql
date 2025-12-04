-- Enable foreign key support
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS pet_tags;
DROP TABLE IF EXISTS pet_photos;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS pets;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS categories;

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

-- Users table with role-based access control
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    user_status INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    role TEXT DEFAULT 'customer'
);

-- Pets table
CREATE TABLE pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    status TEXT DEFAULT 'available',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pet photos table
CREATE TABLE pet_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL
);

-- Pet tags junction table
CREATE TABLE pet_tags (
    pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (pet_id, tag_id)
);

-- Orders table with user ownership
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL REFERENCES pets(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    ship_date TEXT,
    status TEXT DEFAULT 'placed',
    complete INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO categories (name) VALUES 
    ('Dogs'),
    ('Cats'),
    ('Birds'),
    ('Fish');

INSERT INTO tags (name) VALUES 
    ('friendly'),
    ('energetic'),
    ('quiet'),
    ('small'),
    ('large'),
    ('trained');

-- Insert users with password 'password' (plain text for seed data)
INSERT INTO users (username, first_name, last_name, email, password, role) VALUES 
    ('admin', 'Admin', 'User', 'admin@petstore.com', 'password', 'admin'),
    ('store_owner', 'Store', 'Owner', 'owner@petstore.com', 'password', 'store_owner'),
    ('customer1', 'John', 'Doe', 'john@example.com', 'password', 'customer'),
    ('customer2', 'Jane', 'Smith', 'jane@example.com', 'password', 'customer');

INSERT INTO pets (name, category_id, status) VALUES 
    ('Buddy', 1, 'available'),
    ('Whiskers', 2, 'available'), 
    ('Tweety', 3, 'available'),
    ('Nemo', 4, 'pending'),
    ('Max', 1, 'sold'),
    ('Luna', 2, 'available');

INSERT INTO pet_photos (pet_id, photo_url) VALUES 
    (1, 'https://example.com/buddy.jpg'),
    (2, 'https://example.com/whiskers.jpg'),
    (3, 'https://example.com/tweety.jpg'),
    (4, 'https://example.com/nemo.jpg'),
    (5, 'https://example.com/max.jpg'),
    (6, 'https://example.com/luna.jpg');

INSERT INTO pet_tags (pet_id, tag_id) VALUES 
    (1, 1), (1, 2), -- Buddy: friendly, energetic
    (2, 1), (2, 3), -- Whiskers: friendly, quiet  
    (3, 3), (3, 4), -- Tweety: quiet, small
    (4, 4), (4, 3), -- Nemo: small, quiet
    (5, 5), (5, 6), -- Max: large, trained
    (6, 1), (6, 4); -- Luna: friendly, small

INSERT INTO orders (pet_id, user_id, quantity, status) VALUES 
    (4, 3, 1, 'placed'),
    (5, 4, 1, 'delivered');