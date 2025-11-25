// frontend/vite.config.mts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { visualizer } from 'rollup-plugin-visualizer';
import type { PluginOption } from 'vite';
import { inspectorServer } from '@react-dev-inspector/vite-plugin';

export default defineConfig(({ mode, command }) => {
  // Only enable inspector for dev builds (Excludes 'preview')
  const enableInspector = command === 'serve' && mode !== 'production';

  return {
    define: { global: 'window' },
    plugins: [
      react(),
      tsconfigPaths(),
      ...(enableInspector ? [inspectorServer() as PluginOption] : []),
      ...(mode === 'analyze'
        ? [
            visualizer({
              filename: './dist/stats.html',
              open: true,
              gzipSize: true,
              brotliSize: true,
              template: 'treemap'
            }) as PluginOption
          ]
        : [])
    ],
    server: {
      port: 3000,
      host: '0.0.0.0',
      strictPort: true,
      watch: { usePolling: true, interval: 1000 },
      hmr: { host: 'localhost', clientPort: 3000 },
      proxy: {
        // Keep tracking public so hits aren’t blocked
        '/matomo/matomo.php': {
          target: 'http://backend:3000',
          changeOrigin: false,
          xfwd: true
        },
        // Everything else under /matomo: backend enforces Depends(get_current_active_user)
        '/matomo': {
          target: 'http://backend:3000',
          changeOrigin: false,
          xfwd: true
        }
      }
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/setupTests.ts',
      deps: {
        inline: ['@mui/x-data-grid']
      },
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html', 'lcov'],
        reportsDirectory: './coverage',
        include: [
          'src/components/**/*.{js,ts,jsx,tsx}',
          'src/context/**/*.{js,ts,jsx,tsx}',
          'src/hooks/**/*.{js,ts,jsx,tsx}',
          'src/pages/**/*.{js,ts,jsx,tsx}',
          'src/utils/**/*.{js,ts,jsx,tsx}'
        ],
        exclude: [
          'src/setupTests.ts',
          'src/utils/openInVSCode.ts',
          'src/utils/devInspector.ts',
          'src/**/types.*',
          'src/**/index.{js,ts,ts,tsx}',
          'src/**/*[Ss]tyle*'
        ],
        thresholds: {
          global: {
            statements: 30,
            branches: 60,
            functions: 30,
            lines: 30,
            autoUpdate: true
          }
        }
      }
    }
  };
});
