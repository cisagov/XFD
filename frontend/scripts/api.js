// Main entrypoint for serverless frontend code.

// AWS Lambda expects console.log and this file is not shipped to the browser,
// So we are disabling the es-lint no-console rule for just this file
/* eslint-disable no-console */
import rateLimit from 'express-rate-limit';
import serverless from 'serverless-http';
import cors from 'cors';
import helmet from 'helmet';
import express from 'express';
import path from 'path';
import { z } from 'zod';

export const app = express();

const telemetrySchema = z.object({
  type: z.string(),
  path: z.string().optional(),
  status: z.number().nullable().optional(),
  server: z.string().nullable().optional(),
  via: z.string().nullable().optional(),
  cfRay: z.string().nullable().optional(),
  cfCacheStatus: z.string().nullable().optional(),
  ts: z.number().optional()
});

// Rate limiting middleware (per IP, ~1 req/sec over 5 min)
const telemetryLimiter = rateLimit({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 300, // limit each IP to 300 requests per 5 min
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res) => {
    console.warn(
      JSON.stringify({
        clientTelemetry: {
          type: 'rate_limited',
          ip: req.ip,
          ts: Date.now()
        }
      })
    );
    res
      .status(429)
      .send('Too many telemetry requests. Please try again later.');
  }
});

function getErrorMessage(err) {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  try {
    return JSON.stringify(err);
  } catch (e) {
    return 'Unknown error';
  }
}

// JSON body parsing needed for telemetry POST
app.use(express.json({ limit: '10kb' }));

// These CORS origins work in all Crossfeed environments
app.use(
  cors({
    origin: [/^https:\/\/(.*\.)?crossfeed\.cyber\.dhs\.gov$/],
    methods: 'GET,POST,PUT,DELETE,OPTIONS'
  })
);

// The API URLs are different in each environment
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        // Keep default-src tight; widen with specific directives below.
        defaultSrc: ["'self'"],
        // Where the SPA may open XHR/fetch/WebSocket connections:
        connectSrc: [
          "'self'",
          ...[process.env.BACKEND_DOMAIN].filter(Boolean)
          // add 'https://static.cloudflareinsights.com' here if their beacon runs
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
          ...[process.env.BACKEND_DOMAIN].filter(Boolean),
          'https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js',
          ...(process.env.DOMAIN === 'crossfeed.cyber.dhs.gov'
            ? []
            : [
                'https://www.ssa.gov/accessibility/andi/fandi.js',
                'https://www.ssa.gov/accessibility/andi/andi.js'
              ]),
          'https://www.dhs.gov',
          'https://static.cloudflareinsights.com'
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

// Middleware: apply rate limiter before POST handler
app.use('/client-telemetry', telemetryLimiter);

// Telemetry endpoint to log to CloudWatch (CORS preflight)
app.options('/client-telemetry', (req, res) => {
  const origin = req.headers.origin;
  const allowedOrigin = process.env.DOMAIN
    ? `https://${process.env.DOMAIN}`
    : null;

  if (origin && origin === allowedOrigin) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }

  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  res.setHeader('Access-Control-Max-Age', '86400'); // cache preflight 24h

  return res.status(204).send();
});

// Endpoint to log to Cloudwatch
app.post('/client-telemetry', (req, res) => {
  res.setHeader('Cache-Control', 'no-store');

  const origin = req.headers.origin;
  const allowedOrigin = process.env.DOMAIN
    ? `https://${process.env.DOMAIN}`
    : null;

  if (origin && origin === allowedOrigin) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }

  try {
    const parseResult = telemetrySchema.safeParse(req.body);
    if (!parseResult.success) {
      console.warn(
        JSON.stringify({
          clientTelemetry: {
            type: 'invalid_format',
            issues: parseResult.error.issues,
            ts: Date.now()
          }
        })
      );
      return res.status(400).send('Invalid telemetry payload');
    }

    const body = parseResult.data;

    const logInfo = {
      type: body.type,
      path: body.path,
      status: body.status ?? null,
      server: body.server ?? null,
      via: body.via ?? null,
      cfRay: body.cfRay ?? null,
      cfCacheStatus: body.cfCacheStatus ?? null,
      ts: body.ts ?? Date.now()
    };

    console.log(JSON.stringify({ clientTelemetry: logInfo }));
    return res.status(204).send();
  } catch (err) {
    console.error(
      JSON.stringify({
        clientTelemetry: {
          type: 'parse_error',
          error: getErrorMessage(err),
          ts: Date.now()
        }
      })
    );
    return res.status(500).send('Error processing telemetry');
  }
});
app.use(
  express.static(path.join(__dirname, '../dist'), {
    setHeaders: (res, path) => {
      if (path.endsWith('.js')) {
        res.setHeader('Content-Type', 'application/javascript');
      }
    },
    maxAge: 'no-cache, no-store, must-revalidate'
  })
);

app.use((req, res) => {
  res.setHeader('Content-Type', 'text/html');
  res.sendFile(path.join(__dirname, '../dist/index.html'));
});

export const handler = serverless(app, {
  binary: ['image/*', 'font/*']
});
