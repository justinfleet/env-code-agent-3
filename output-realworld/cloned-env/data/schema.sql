-- RealWorld Conduit API Database Schema

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    bio TEXT,
    image TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Articles table
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    body TEXT NOT NULL,
    author_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body TEXT NOT NULL,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    author_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Tags table
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Article tags junction table
CREATE TABLE article_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    UNIQUE (article_id, tag_id)
);

-- Favorites junction table
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    article_id INTEGER NOT NULL REFERENCES articles(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, article_id)
);

-- Follows junction table
CREATE TABLE follows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER NOT NULL REFERENCES users(id),
    following_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (follower_id, following_id)
);

-- Insert sample data

-- Sample users
INSERT INTO users (username, email, password_hash, bio, image) VALUES
('johndoe', 'john@example.com', '$2b$10$K7L1OJ45/4Y2nIvhRVpCe.FSmhDdWoXehVzJptJ/op0lSsvqNu/1u', 'Software developer passionate about clean code', 'https://api.realworld.io/images/demo-avatar.png'),
('janedoe', 'jane@example.com', '$2b$10$K7L1OJ45/4Y2nIvhRVpCe.FSmhDdWoXehVzJptJ/op0lSsvqNu/1u', 'Tech writer and blogger', 'https://api.realworld.io/images/smiley-cyrus.jpeg'),
('alexsmith', 'alex@example.com', '$2b$10$K7L1OJ45/4Y2nIvhRVpCe.FSmhDdWoXehVzJptJ/op0lSsvqNu/1u', 'Full-stack developer', NULL);

-- Sample tags
INSERT INTO tags (name) VALUES
('react'),
('javascript'),
('web-development'),
('nodejs'),
('typescript'),
('programming'),
('tutorial'),
('beginner');

-- Sample articles
INSERT INTO articles (slug, title, description, body, author_id) VALUES
('how-to-build-webapps-that-scale', 'How to build webapps that scale', 'This is the description for the post.', 'Web development is awesome. Here is how you can build scalable web applications...', 1),
('why-i-love-react', 'Why I Love React', 'React makes building UIs so much easier!', 'React is a fantastic library for building user interfaces. Here are the reasons why I love it...', 2),
('getting-started-with-nodejs', 'Getting Started with Node.js', 'A beginner-friendly guide to Node.js', 'Node.js is a powerful runtime for JavaScript. In this tutorial, we will cover the basics...', 1);

-- Sample article tags
INSERT INTO article_tags (article_id, tag_id) VALUES
(1, 3), -- web-development
(1, 4), -- nodejs
(1, 6), -- programming
(2, 1), -- react
(2, 2), -- javascript
(2, 3), -- web-development
(3, 4), -- nodejs
(3, 7), -- tutorial
(3, 8); -- beginner

-- Sample follows
INSERT INTO follows (follower_id, following_id) VALUES
(1, 2),
(2, 1),
(3, 1);

-- Sample favorites
INSERT INTO favorites (user_id, article_id) VALUES
(2, 1),
(3, 1),
(1, 2);

-- Sample comments
INSERT INTO comments (body, article_id, author_id) VALUES
('Great article! Very helpful.', 1, 2),
('Thanks for sharing this.', 1, 3),
('I totally agree with your points about React!', 2, 1);