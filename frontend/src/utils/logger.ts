const isDevelopment = import.meta.env.MODE === 'development';

/**
 * Logger utility that only logs in development mode.
 * In production, all log calls are no-ops.
 */
export const logger = {
  /**
   * Log informational messages
   */
  info: (...args: unknown[]): void => {
    if (isDevelopment) {
      // eslint-disable-next-line no-console
      console.log('[INFO]', ...args);
    }
  },

  /**
   * Log error messages
   */
  error: (...args: unknown[]): void => {
    if (isDevelopment) {
      // eslint-disable-next-line no-console
      console.error('[ERROR]', ...args);
    }
  },

  /**
   * Log warning messages
   */
  warn: (...args: unknown[]): void => {
    if (isDevelopment) {
      // eslint-disable-next-line no-console
      console.warn('[WARN]', ...args);
    }
  },

  /**
   * Log debug messages
   */
  debug: (...args: unknown[]): void => {
    if (isDevelopment) {
      // eslint-disable-next-line no-console
      console.log('[DEBUG]', ...args);
    }
  }
};
