import serverless from 'serverless-http';
import express from 'express';
import path from 'path';
import rateLimit from 'express-rate-limit';
import cors from 'cors';
import helmet from 'helmet';
import fs from 'fs';

export const app = express();

app.use(
  rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 1000
  })
); // limit 1000 requests per 15 minutes

app.use(express.static(path.join(__dirname, '../docs/build')));

app.use(
  cors({
    origin: [
      /^https:\/\/(.*\.)?crossfeed\.cyber\.dhs\.gov$/,
      /^https:\/\/(.*\.)?readysetcyber\.cyber\.dhs\.gov$/
    ],
    methods: 'GET,POST,PUT,DELETE,OPTIONS'
  })
);

app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: [
          "'self'",
          `${process.env.COGNITO_URL}`,
          `${process.env.BACKEND_DOMAIN}`
        ],
        frameSrc: ["'self'", 'https://www.dhs.gov/ntas/'],
        imgSrc: [
          "'self'",
          'data:',
          `https://${process.env.DOMAIN}`,
          'https://www.ssa.gov',
          'https://www.dhs.gov'
        ],
        objectSrc: ["'none'"],
        scriptSrc: [
          "'self'",
          `${process.env.BACKEND_DOMAIN}`,
          'https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js',
          'https://www.ssa.gov/accessibility/andi/fandi.js',
          'https://www.ssa.gov/accessibility/andi/andi.js',
          'https://www.dhs.gov'
        ],
        frameAncestors: ["'none'"]
      }
    },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true
    }
  })
);

//Middleware to set Cache-Control headers
app.use((req, res, next) => {
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  next();
});

app.use((req, res, next) => {
  res.setHeader('X-XSS-Protection', '0');
  next();
});

// Serve static assets
app.use(
  express.static(path.join(__dirname, '../docs-build'), {
    setHeaders: (res, filePath) => {
      if (filePath.endsWith('.js')) {
        res.setHeader('Content-Type', 'application/javascript');
      }
    }
  })
);

// Fallback to index.html for client-side routing
app.get('*', (req, res) => {
  const rootDir = path.resolve(__dirname, '../docs-build'); // Define the root directory
  const requestedPath = path.join(rootDir, req.path); // Join the requested path with rootDir
  const resolvedPath = path.resolve(requestedPath); // Resolve to an absolute path

  // Ensure the resolved path is within the rootDir
  if (!resolvedPath.startsWith(rootDir)) {
    res.status(403).send('Forbidden');
    return;
  }

  // Check if the file exists and is a valid file
  try {
    if (fs.existsSync(resolvedPath) && fs.lstatSync(resolvedPath).isFile()) {
      res.sendFile(resolvedPath); // Serve the file
    } else {
      // Fallback to index.html for client-side routing
      res.sendFile(path.join(rootDir, 'index.html'));
    }
  } catch (error) {
    console.error('Error while serving file:', error);
    res.status(500).send('Internal Server Error');
  }
});

export const handler = serverless(app, {
  binary: ['image/*', 'font/*']
});
