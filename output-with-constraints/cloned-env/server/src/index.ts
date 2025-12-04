import express from 'express';
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

// Enable query string parsing
app.set('query parser', 'extended');

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Debug endpoint to test query params
app.get('/debug/query', (req, res) => {
  res.json({ 
    query: req.query,
    url: req.url,
    originalUrl: req.originalUrl
  });
});

// API routes
app.use('/api/v3/pet', petRoutes);
app.use('/api/v3/store', storeRoutes);
app.use('/api/v3/user', userRoutes);

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Error handler
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

export default app;