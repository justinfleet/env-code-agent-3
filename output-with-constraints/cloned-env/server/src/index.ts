import express from 'express';
import cors from 'cors';
import petsRouter from './routes/pets';
import storeRouter from './routes/store';
import usersRouter from './routes/users';

const app = express();
const PORT = process.env.PORT || 3002;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    service: 'Swagger Petstore API'
  });
});

// API routes
app.use('/api/v3/pet', petsRouter);
app.use('/api/v3/store', storeRouter);
app.use('/api/v3/user', usersRouter);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Swagger Petstore API - OpenAPI 3.0',
    version: '1.0.0',
    documentation: '/api-docs',
    health: '/health'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ 
    error: 'Not Found',
    message: `Route ${req.method} ${req.originalUrl} not found`
  });
});

// Error handler
app.use((error: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Unhandled error:', error);
  res.status(500).json({ 
    error: 'Internal Server Error',
    message: 'An unexpected error occurred'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Swagger Petstore API server listening on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🐾 API base: http://localhost:${PORT}/api/v3`);
});

export default app;