// Main entrypoint for serverless frontend code.

import serverless from 'serverless-http';
import cors from 'cors';
import helmet from 'helmet';
import express from 'express';
import path from 'path';
import { ALLOW_ORIGIN, ALLOW_METHODS } from './constants.js';
import logger from 'lambda-logger';

export const app = express();

app.use((req, res, next) => {
  const sanitizedHeaders = { ...req.headers };
  // Remove or replace sensitive headers
  delete sanitizedHeaders['authorization'];
  res.on('finish', () => {
    const logInfo = {
      httpMethod: req.method,
      protocol: req.protocol,
      originalUrl: req.originalUrl,
      path: req.path,
      statusCode: res.statusCode,
      headers: sanitizedHeaders
    };
    logger.info(`Request Info: ${JSON.stringify(logInfo)}`);
  });
  next();
});

app.use(cors({ origin: ALLOW_ORIGIN, methods: ALLOW_METHODS }));

app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: [
          "'self'",
          'https://cognito-idp.us-gov-west-1.amazonaws.com',
          'https://api.crossfeed.cyber.dhs.gov'
        ],
        objectSrc: ["'none'"],
        scriptSrc: [
          "'self'",
          'https://api.crossfeed.cyber.dhs.gov'
          // Add any other allowed script sources here
        ],
        frameAncestors: ["'none'"]
        // Add other directives as needed
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
