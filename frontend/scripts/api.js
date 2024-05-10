// Main entrypoint for serverless frontend code.

import serverless from 'serverless-http';
import cors from 'cors';
import helmet from 'helmet';
import express from 'express';
import path from 'path';

export const app = express();

app.use((req, res, next) => {
  const sanitizedHeaders = { ...req.headers };
  // Remove or replace sensitive headers
  delete sanitizedHeaders['authorization'];
  console.log(`Request Headers: ${JSON.stringify(sanitizedHeaders)}`);
  next();
});

app.use(
  cors({
    origin: [
      /^https:\/\/.*\.crossfeed\.cyber\.dhs\.gov$/,
      /^https:\/\/.*\.readysetcyber\.cyber\.dhs\.gov$/
    ],
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
  })
);

app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: [
          "'self'",
          'https://cognito-idp.*.amazonaws.com',
          'https://*.crossfeed.cyber.dhs.gov',
          'https://*.readysetcyber.cyber.dhs.gov'
        ],
        frameSrc: ["'self'", 'https://www.dhs.gov/ntas/'],
        imgSrc: [
          "'self'",
          'https://*.crossfeed.cyber.dhs.gov',
          'https://*.readysetcyber.cyber.dhs.gov',
          'https://www.dhs.gov'
        ],
        objectSrc: ["'none'"],
        scriptSrc: [
          "'self'",
          'https://*.crossfeed.cyber.dhs.gov',
          'https://*.readysetcyber.cyber.dhs.gov',
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

app.use((req, res, next) => {
  res.setHeader('X-XSS-Protection', '0');
  next();
});

app.use(express.static(path.join(__dirname, '../build')));

app.use((req, res) => {
  res.sendFile(path.join(__dirname, '../build/index.html'));
});

export const handler = serverless(app, {
  binary: ['image/*', 'font/*']
});
