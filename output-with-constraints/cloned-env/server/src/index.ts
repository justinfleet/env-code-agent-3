import express from 'express';
import cors from 'cors';
import petsRouter from './routes/pets.js';
import storeRouter from './routes/store.js';
import usersRouter from './routes/users.js';

const app = express();
const PORT = process.env.PORT || 3002;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// API routes - mount with proper base paths
app.use('/api/v3/pet', petsRouter);
app.use('/api/v3/store', storeRouter);
app.use('/api/v3/user', usersRouter);

// Error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

export default app;