import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

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

// Auto-copy seed.db to current.sqlite if not exists
if (!fs.existsSync(DATABASE_PATH)) {
  const seedPath = path.join(path.dirname(DATABASE_PATH), 'seed.db');
  if (fs.existsSync(seedPath)) {
    fs.copyFileSync(seedPath, DATABASE_PATH);
  }
}

const db = new Database(DATABASE_PATH);

// Enable WAL mode and foreign keys
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

export default db;