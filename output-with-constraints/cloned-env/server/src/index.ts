import express, { Request, Response } from 'express';
import cors from 'cors';
import petRoutes from './routes/pet';
import storeRoutes from './routes/store';
import userRoutes from './routes/user';

const app = express();
const PORT = process.env.PORT || 3002;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// API routes
app.use('/api/v3/pet', petRoutes);
app.use('/api/v3/store', storeRoutes);
app.use('/api/v3/user', userRoutes);

// Error handling middleware
app.use((err: any, req: Request, res: Response, next: any) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
  console.log(`Health check available at http://localhost:${PORT}/health`);
});

export default app;