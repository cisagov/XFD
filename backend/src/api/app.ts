import * as express from 'express';
import * as cookieParser from 'cookie-parser';
import * as cookie from 'cookie';
import * as cors from 'cors';
import * as helmet from 'helmet';
import { handler as healthcheck } from './healthcheck';
import * as auth from './auth';
import * as cpes from './cpes';
import * as cves from './cves';
import * as domains from './domains';
import * as notifications from './notifications';
import * as search from './search';
import * as vulnerabilities from './vulnerabilities';
import * as organizations from './organizations';
import * as scans from './scans';
import * as users from './users';
import * as scanTasks from './scan-tasks';
import * as stats from './stats';
import * as apiKeys from './api-keys';
import * as reports from './reports';
import * as savedSearches from './saved-searches';
import rateLimit from 'express-rate-limit';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { User, UserType, connectToDatabase } from '../models';
import * as assessments from './assessments';
import * as jwt from 'jsonwebtoken';
import { Request, Response, NextFunction } from 'express';
import fetch from 'node-fetch';

const sanitizer = require('sanitizer');

if (
  (process.env.IS_OFFLINE || process.env.IS_LOCAL) &&
  typeof jest === 'undefined'
) {
  // Run scheduler during local development. When deployed on AWS,
  // the scheduler runs on a separate lambda function.
  const { handler: scheduler } = require('../tasks/scheduler');
  const { listenForDockerEvents } = require('./docker-events');
  listenForDockerEvents();
  setInterval(() => scheduler({}, {} as any, () => null), 30000);
}

const handlerToExpress = (handler) => async (req, res) => {
  const { statusCode, body } = await handler(
    {
      pathParameters: req.params,
      query: req.query,
      requestContext: req.requestContext,
      body: JSON.stringify(req.body || '{}'),
      headers: req.headers,
      path: req.originalUrl
    },
    {}
  );
  try {
    const parsedBody = JSON.parse(sanitizer.sanitize(body));
    res.status(statusCode).json(parsedBody);
  } catch (e) {
    // Not a JSON body
    res.setHeader('content-type', 'text/plain');
    res.status(statusCode).send(sanitizer.sanitize(body));
  }
};

const app = express();

app.use(
  rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: 5000
  })
); // limit 1000 requests per 15 minutes

app.use(express.json({ strict: false }));

// These CORS origins work in all Crossfeed environments
app.use(
  cors({
    origin: [
      'http://localhost',
      /^https:\/\/(.*\.)?crossfeed\.cyber\.dhs\.gov$/,
      /^https:\/\/(.*\.)?readysetcyber\.cyber\.dhs\.gov$/
    ],
    methods: 'GET,POST,PUT,DELETE,OPTIONS'
  })
);

// The API URLs are different in each environment
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: [
          "'self'",
          'https://cognito-idp.us-east-1.amazonaws.com',
          'https://api.staging-cd.crossfeed.cyber.dhs.gov'
        ],
        frameSrc: ["'self'", 'https://www.dhs.gov/ntas/'],
        imgSrc: [
          "'self'",
          'data:',
          'https://staging-cd.crossfeed.cyber.dhs.gov',
          'https://www.ssa.gov',
          'https://www.dhs.gov'
        ],
        objectSrc: ["'none'"],
        scriptSrc: [
          "'self'",
          'https://api.staging-cd.crossfeed.cyber.dhs.gov',
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

app.use((req, res, next) => {
  res.setHeader('X-XSS-Protection', '0');
  // Okta header
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  next();
});

const setAuthorizationHeader = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const accessToken = req.cookies.access_token;

  if (accessToken) {
    req.headers.authorization = `Bearer ${accessToken}`;
  }

  next();
};

app.use(cookieParser());
app.use(setAuthorizationHeader);

app.get('/whoami', (req, res, next) => {
  // TODO: Test and determine if this can be removed.
  // if (!req.isAuthenticated()) {
  //   return res.status(401).json({
  //     message: 'Unauthorized'
  //   });
  // } else {

  //   // You can log other SAML attributes similarly
  //   // return res.status(200).json({ user: req.user });
  // }
  return next();
});

interface DecodedToken {
  sub: string;
  email: string;
  'cognito:username': string;
  'custom:OKTA_ID': string;
  given_name: string;
  family_name: string;
  email_verified: boolean;
  [key: string]: any; // Index signature for additional properties
}

// Okta Callback Handler
app.post('/auth/okta-callback', async (req, res) => {
  const { code } = req.body;
  const clientId = process.env.REACT_APP_COGNITO_CLIENT_ID;
  const callbackUrl = process.env.REACT_APP_COGNITO_CALLBACK_URL;
  const domain = process.env.REACT_APP_COGNITO_DOMAIN;

  if (!code) {
    return res.status(400).json({ message: 'Missing authorization code' });
  }

  try {
    if (!callbackUrl) {
      throw new Error('callbackUrl is required');
    }

    const tokenEndpoint = `https://${domain}/oauth2/token`;
    const tokenData = `grant_type=authorization_code&client_id=${clientId}&code=${code}&redirect_uri=${callbackUrl}&scope=openid`;

    const response = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: tokenData
    });
    const { id_token, access_token, refresh_token } = await response.json();

    if (!id_token) {
      throw new Error('ID token is missing in the response');
    }

    const decodedToken = jwt.decode(id_token) as DecodedToken;
    if (!decodedToken) {
      throw new Error('Failed to decode ID token');
    }

    const cognitoUsername = decodedToken['cognito:username'];
    const oktaId = decodedToken['custom:OKTA_ID'];
    jwt.verify(
      id_token,
      auth.getOktaKey,
      { algorithms: ['RS256'] },
      async (err, payload) => {
        if (err) {
          console.log('Error: ', err);
          return res.status(401).json({ message: 'Invalid ID token' });
        }

        await connectToDatabase();

        let user = await User.findOne({ email: decodedToken.email });

        if (!user) {
          user = User.create({
            email: decodedToken.email,
            oktaId: oktaId,
            firstName: decodedToken.given_name,
            lastName: decodedToken.family_name,
            invitePending: true,
            // TODO: Replace these default Region/State values with user selection
            state: 'Virginia',
            regionId: '3'
          });
          await user.save();
        } else {
          user.oktaId = oktaId;
          await user.save();
        }

        res.cookie('access_token', access_token, {
          httpOnly: true,
          secure: true
        });
        res.cookie('refresh_token', refresh_token, {
          httpOnly: true,
          secure: true
        });

        if (user) {
          if (!process.env.JWT_SECRET) {
            throw new Error('JWT_SECRET is not defined');
          }

          const signedToken = await jwt.sign(
            { id: user.id, email: user.email },
            process.env.JWT_SECRET,
            { expiresIn: '14m' }
          );

          res.cookie('id_token', signedToken, { httpOnly: true, secure: true });

          return res.status(200).json({
            token: signedToken,
            user: user
          });
        }
      }
    );
  } catch (error) {
    console.error(
      'Token exchange error:',
      error.response ? error.response.data : error.message
    );
    res.status(500).json({
      message: 'Authentication failed',
      error: error.response ? error.response.data : error.message
    });
  }
});

app.get('/', handlerToExpress(healthcheck));
app.post('/auth/login', handlerToExpress(auth.login));
app.post('/auth/callback', handlerToExpress(auth.callback));
app.post('/users/register', handlerToExpress(users.register));
app.post('/readysetcyber/register', handlerToExpress(users.RSCRegister));

app.get('/notifications', handlerToExpress(notifications.list));
app.get(
  '/notifications/508-banner',
  handlerToExpress(notifications.get508Banner)
);

const checkUserLoggedIn = async (req, res, next) => {
  console.log('Checking if user is logged in.');

  const authorizationHeader = req.headers.authorization;

  if (!authorizationHeader) {
    return res.status(401).send('Not logged in');
  }

  try {
    req.requestContext = {
      authorizer: await auth.authorize({
        authorizationToken: authorizationHeader
      })
    };

    if (
      !req.requestContext.authorizer.id ||
      req.requestContext.authorizer.id === 'cisa:crossfeed:anonymous'
    ) {
      return res.status(401).send('Not logged in');
    }

    return next();
  } catch (error) {
    console.error('Error authorizing user:', error);
    return res.status(500).send('Internal server error');
  }
};

const checkUserSignedTerms = (req, res, next) => {
  // Bypass ToU for CISA emails
  const approvedEmailAddresses = ['@cisa.dhs.gov', '@associates.cisa.dhs.gov'];
  if (process.env.NODE_ENV === 'test')
    approvedEmailAddresses.push('@crossfeed.cisa.gov');
  for (const email of approvedEmailAddresses) {
    if (
      req.requestContext.authorizer.email &&
      req.requestContext.authorizer.email.endsWith(email)
    )
      return next();
  }
  if (
    !req.requestContext.authorizer.dateAcceptedTerms ||
    (req.requestContext.authorizer.acceptedTermsVersion &&
      req.requestContext.authorizer.acceptedTermsVersion !==
        getToUVersion(req.requestContext.authorizer))
  ) {
    return res.status(403).send('User must accept terms of use');
  }
  return next();
};

const getMaximumRole = (user) => {
  if (user?.userType === UserType.GLOBAL_VIEW) return 'user';
  return user && user.roles && user.roles.find((role) => role.role === 'admin')
    ? 'admin'
    : 'user';
};

const getToUVersion = (user) => {
  return `v${process.env.REACT_APP_TERMS_VERSION}-${getMaximumRole(user)}`;
};

// Rewrite the URL for some Matomo admin dashboard URLs, due to a bug in
// how Matomo handles relative URLs when hosted on a subpath.
app.get('/plugins/Morpheus/images/logo.svg', (req, res) =>
  res.redirect('/matomo/plugins/Morpheus/images/logo.svg?matomo')
);
app.get('/index.php', (req, res) => res.redirect('/matomo/index.php'));

/**
 * @swagger
 *
 * /matomo:
 *  get:
 *    description: All paths under /matomo proxy to a Matomo instance, which is used to handle and process user analytics. A global admin user can access this page from the "My Account" page.
 *    tags:
 *    - Analytics
 */
const matomoProxy = createProxyMiddleware({
  target: process.env.MATOMO_URL,
  headers: { HTTP_X_FORWARDED_URI: '/matomo' },
  pathRewrite: function (path) {
    return path.replace(/^\/matomo/, '');
  },
  onProxyReq: function (proxyReq) {
    // Only pass the MATOMO_SESSID cookie to Matomo.
    if (!proxyReq.getHeader('Cookie')) return;
    const cookies = cookie.parse(proxyReq.getHeader('Cookie'));
    const newCookies = cookie.serialize(
      'MATOMO_SESSID',
      String(cookies['MATOMO_SESSID'])
    );
    proxyReq.setHeader('Cookie', newCookies);
  },
  onProxyRes: function (proxyRes) {
    // Remove transfer-encoding: chunked responses, because API Gateway doesn't
    // support chunked encoding.
    if (proxyRes.headers['transfer-encoding'] === 'chunked') {
      proxyRes.headers['transfer-encoding'] = '';
    }
  }
});

/**
 * @swagger
 *
 * /pe:
 *  get:
 *    description: All paths under /pe proxy to the P&E django application and API. Only a global admin can access.
 */
const peProxy = createProxyMiddleware({
  target: process.env.PE_API_URL,
  pathRewrite: function (path) {
    return path.replace(/^\/pe/, '');
  }
});

app.use(
  '/matomo',
  async (req, res, next) => {
    // Public paths -- see https://matomo.org/docs/security-how-to/
    const ALLOWED_PATHS = ['/matomo.php', '/matomo.js'];
    if (ALLOWED_PATHS.indexOf(req.path) > -1) {
      return next();
    }
    // API Gateway isn't able to proxy fonts properly -- so we're using a CDN instead.
    if (req.path === '/plugins/Morpheus/fonts/matomo.woff2') {
      return res.redirect(
        'https://cdn.jsdelivr.net/gh/matomo-org/matomo@3.14.1/plugins/Morpheus/fonts/matomo.woff2'
      );
    }
    if (req.path === '/plugins/Morpheus/fonts/matomo.woff') {
      return res.redirect(
        'https://cdn.jsdelivr.net/gh/matomo-org/matomo@3.14.1/plugins/Morpheus/fonts/matomo.woff'
      );
    }
    if (req.path === '/plugins/Morpheus/fonts/matomo.ttf') {
      return res.redirect(
        'https://cdn.jsdelivr.net/gh/matomo-org/matomo@3.14.1/plugins/Morpheus/fonts/matomo.ttf'
      );
    }
    // Only allow global admins to access all other paths.
    const user = (await auth.authorize({
      authorizationToken: req.cookies['crossfeed-token']
    })) as auth.UserToken;
    if (user.userType !== UserType.GLOBAL_ADMIN) {
      return res.status(401).send('Unauthorized');
    }
    return next();
  },
  matomoProxy
);

app.use(
  '/pe',
  async (req, res, next) => {
    // Only allow specific users to access
    const user = (await auth.authorize({
      authorizationToken: req.headers.authorization
    })) as auth.UserToken;
    if (
      user.userType !== UserType.GLOBAL_VIEW &&
      user.userType !== UserType.GLOBAL_ADMIN
    ) {
      return res.status(401).send('Unauthorized');
    }
    return next();
  },
  peProxy
);

const checkGlobalAdminOrRegionAdmin = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const user = (await auth.authorize({
      authorizationToken: req.headers.authorization
    })) as auth.UserToken;

    if (
      user.userType !== UserType.GLOBAL_ADMIN &&
      user.userType !== UserType.REGIONAL_ADMIN
    ) {
      return res.status(401).send('Unauthorized');
    }
    next();
  } catch (error) {
    console.error('Error authorizing user:', error);
    return res.status(500).send('Internal server error');
  }
};

// Routes that require an authenticated user, without
// needing to sign the terms of service yet
const authenticatedNoTermsRoute = express.Router();
authenticatedNoTermsRoute.use(checkUserLoggedIn);
authenticatedNoTermsRoute.get('/users/me', handlerToExpress(users.me));
authenticatedNoTermsRoute.post(
  '/users/me/acceptTerms',
  handlerToExpress(users.acceptTerms)
);
authenticatedNoTermsRoute.put('/users/:userId', handlerToExpress(users.update));

app.use(authenticatedNoTermsRoute);

// Routes that require an authenticated user that has
// signed the terms of service
const authenticatedRoute = express.Router();

authenticatedRoute.use(checkUserLoggedIn);
authenticatedRoute.use(checkUserSignedTerms);

authenticatedRoute.post('/api-keys', handlerToExpress(apiKeys.generate));
authenticatedRoute.delete('/api-keys/:keyId', handlerToExpress(apiKeys.del));

authenticatedRoute.post('/search', handlerToExpress(search.search));
authenticatedRoute.post('/search/export', handlerToExpress(search.export_));
authenticatedRoute.get('/cpes/:id', handlerToExpress(cpes.get));
authenticatedRoute.get('/cves/:id', handlerToExpress(cves.get));
authenticatedRoute.get('/cves/name/:name', handlerToExpress(cves.getByName));
authenticatedRoute.post('/domain/search', handlerToExpress(domains.list));
authenticatedRoute.post('/domain/export', handlerToExpress(domains.export_));
authenticatedRoute.get('/domain/:domainId', handlerToExpress(domains.get));
authenticatedRoute.post(
  '/vulnerabilities/search',
  handlerToExpress(vulnerabilities.list)
);
authenticatedRoute.post(
  '/vulnerabilities/export',
  handlerToExpress(vulnerabilities.export_)
);
authenticatedRoute.get(
  '/vulnerabilities/:vulnerabilityId',
  handlerToExpress(vulnerabilities.get)
);
authenticatedRoute.put(
  '/vulnerabilities/:vulnerabilityId',
  handlerToExpress(vulnerabilities.update)
);
authenticatedRoute.get('/saved-searches', handlerToExpress(savedSearches.list));
authenticatedRoute.post(
  '/saved-searches',
  handlerToExpress(savedSearches.create)
);
authenticatedRoute.get(
  '/saved-searches/:searchId',
  handlerToExpress(savedSearches.get)
);
authenticatedRoute.put(
  '/saved-searches/:searchId',
  handlerToExpress(savedSearches.update)
);
authenticatedRoute.delete(
  '/saved-searches/:searchId',
  handlerToExpress(savedSearches.del)
);
authenticatedRoute.get('/scans', handlerToExpress(scans.list));
authenticatedRoute.get('/granularScans', handlerToExpress(scans.listGranular));
authenticatedRoute.post('/scans', handlerToExpress(scans.create));
authenticatedRoute.get('/scans/:scanId', handlerToExpress(scans.get));
authenticatedRoute.put('/scans/:scanId', handlerToExpress(scans.update));
authenticatedRoute.delete('/scans/:scanId', handlerToExpress(scans.del));
authenticatedRoute.post('/scans/:scanId/run', handlerToExpress(scans.runScan));
authenticatedRoute.post(
  '/scheduler/invoke',
  handlerToExpress(scans.invokeScheduler)
);
authenticatedRoute.post('/scan-tasks/search', handlerToExpress(scanTasks.list));
authenticatedRoute.post(
  '/scan-tasks/:scanTaskId/kill',
  handlerToExpress(scanTasks.kill)
);
authenticatedRoute.get(
  '/scan-tasks/:scanTaskId/logs',
  handlerToExpress(scanTasks.logs)
);

authenticatedRoute.get('/organizations', handlerToExpress(organizations.list));
authenticatedRoute.get(
  '/organizations/tags',
  handlerToExpress(organizations.getTags)
);
authenticatedRoute.get(
  '/organizations/:organizationId',
  handlerToExpress(organizations.get)
);
authenticatedRoute.get(
  '/organizations/state/:state',
  handlerToExpress(organizations.getByState)
);
authenticatedRoute.get(
  '/organizations/regionId/:regionId',
  handlerToExpress(organizations.getByRegionId)
);
authenticatedRoute.post(
  '/organizations',
  handlerToExpress(organizations.create)
);
authenticatedRoute.post(
  '/organizations_upsert',
  handlerToExpress(organizations.upsert_org)
);

authenticatedRoute.put(
  '/organizations/:organizationId',
  handlerToExpress(organizations.update)
);
authenticatedRoute.delete(
  '/organizations/:organizationId',
  handlerToExpress(organizations.del)
);
authenticatedRoute.post(
  '/v2/organizations/:organizationId/users',
  handlerToExpress(organizations.addUserV2)
);
authenticatedRoute.post(
  '/organizations/:organizationId/roles/:roleId/approve',
  handlerToExpress(organizations.approveRole)
);
authenticatedRoute.post(
  '/organizations/:organizationId/roles/:roleId/remove',
  handlerToExpress(organizations.removeRole)
);
authenticatedRoute.post(
  '/organizations/:organizationId/granularScans/:scanId/update',
  handlerToExpress(organizations.updateScan)
);
authenticatedRoute.post(
  '/organizations/:organizationId/initiateDomainVerification',
  handlerToExpress(organizations.initiateDomainVerification)
);
authenticatedRoute.post(
  '/organizations/:organizationId/checkDomainVerification',
  handlerToExpress(organizations.checkDomainVerification)
);
authenticatedRoute.post('/stats', handlerToExpress(stats.get));
authenticatedRoute.post('/users', handlerToExpress(users.invite));
authenticatedRoute.get('/users', handlerToExpress(users.list));
authenticatedRoute.delete('/users/:userId', handlerToExpress(users.del));
authenticatedRoute.get(
  '/users/state/:state',
  handlerToExpress(users.getByState)
);
authenticatedRoute.get(
  '/users/regionId/:regionId',
  handlerToExpress(users.getByRegionId)
);
authenticatedRoute.post('/users/search', handlerToExpress(users.search));

authenticatedRoute.post(
  '/reports/export',
  handlerToExpress(reports.export_report)
);

authenticatedRoute.post(
  '/reports/list',
  handlerToExpress(reports.list_reports)
);

//Authenticated Registration Routes
authenticatedRoute.put(
  '/users/:userId/register/approve',
  checkGlobalAdminOrRegionAdmin,
  handlerToExpress(users.registrationApproval)
);

authenticatedRoute.put(
  '/users/:userId/register/deny',
  handlerToExpress(users.registrationDenial)
);

authenticatedRoute.delete(
  '/notifications/:notificationId',
  handlerToExpress(notifications.del)
);

authenticatedRoute.post(
  '/notifications',
  handlerToExpress(notifications.create)
);

authenticatedRoute.put(
  '/notifications/:notificationId',
  handlerToExpress(notifications.update)
);
//Authenticated ReadySetCyber Routes
authenticatedRoute.get('/assessments', handlerToExpress(assessments.list));

authenticatedRoute.get('/assessments/:id', handlerToExpress(assessments.get));

//************* */
//  V2 Routes   //
//************* */

// Users
authenticatedRoute.put('/v2/users/:userId', handlerToExpress(users.updateV2));
authenticatedRoute.get('/v2/users', handlerToExpress(users.getAllV2));

// Organizations
authenticatedRoute.put(
  '/v2/organizations/:organizationId',
  handlerToExpress(organizations.updateV2)
);
authenticatedRoute.get(
  '/v2/organizations',
  handlerToExpress(organizations.getAllV2)
);

app.use(authenticatedRoute);

export default app;
