// Main entrypoint for dev server.
import logger from '@/utils/logger.js';
import { app } from './api.js';

const port = 3000;
app.listen(port, () => {
  logger.info('App listening on port ' + port);
});
