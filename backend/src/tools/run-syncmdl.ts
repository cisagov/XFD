import { handler as syncmdl } from '../tasks/syncmdl';

/**
 * Runs syncmdl locally. This script is called from running "npm run syncmdl".
 * Call "npm run syncmdl -- -d dangerouslyforce" to force dropping and
 * recreating the SQL database.
 * */

process.env.DB_HOST = 'db';
process.env.MDL_USERNAME = 'mdl';
process.env.MDL_PASSWORD = 'password';
process.env.MDL_DATABASE = 'crossfeed_mini_datalake';

syncmdl(process.argv[2] === '-d' ? process.argv[3] : '', {} as any, () => null);
