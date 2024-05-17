import serverless from 'serverless-http';
import express from 'express';
import path from 'path';
import rateLimit from 'express-rate-limit';
import cors from 'cors';
import helmet from 'helmet';

export const app = express();

app.use(
  rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 1000
  })
); // limit 1000 requests per 15 minutes

app.use(express.static(path.join(__dirname, '../docs/build')));

const { origin, methods } = JSON.parse(process.env.CORS_DOCS);
app.use(
  cors({
    origin,
    methods
  })
);
app.use(
  helmet({
    contentSecurityPolicy: JSON.parse(process.env.CSP_DOCS),
    hsts: { maxAge: 31536000, includeSubDomains: true, preload: true },
    xFrameOptions: 'DENY'
  })
);

app.use((req, res, next) => {
  res.setHeader('X-XSS-Protection', '0');
  next();
});

app.use((req, res) => {
  res.sendFile(path.join(__dirname, '../docs/build/index.html'));
});

export const handler = serverless(app, {
  binary: ['image/*', 'font/*']
});
