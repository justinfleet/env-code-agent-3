import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function resolveDatabasePath() {
  // 1. DATABASE_PATH env var (highest priority)
  if (process.env.DATABASE_PATH?.trim()) {
    return path.resolve(process.env.DATABASE_PATH);
  }
  // 2. ENV_DB_DIR env var
  if (process.env.ENV_DB_DIR) {
    return path.join(process.env.ENV_DB_DIR, 'current.sqlite');
  }
  // 3. Default
  return path.join(__dirname, '../../../data/current.sqlite');
}

const DATABASE_PATH = resolveDatabasePath();

// Ensure data directory exists
const dataDir = path.dirname(DATABASE_PATH);
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

// Auto-copy seed.db to current.sqlite if not exists
if (!fs.existsSync(DATABASE_PATH)) {
  const seedPath = path.join(path.dirname(DATABASE_PATH), 'seed.db');
  if (fs.existsSync(seedPath)) {
    fs.copyFileSync(seedPath, DATABASE_PATH);
  }
}

// Initialize database connection
const db = new Database(DATABASE_PATH);

// Enable WAL mode and foreign keys
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

export default db;