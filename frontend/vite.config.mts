// frontend/vite.config.mts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { visualizer } from 'rollup-plugin-visualizer';
import type { PluginOption } from 'vite';
import { inspectorServer } from '@react-dev-inspector/vite-plugin';

const enableInspector = process.env.ENABLE_INSPECTOR === 'true';
const mode = process.env.MODE || 'development';
const isCI = process.env.CI === 'true';

const plugins: PluginOption[] = [
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
];

export default defineConfig({
  define: { global: 'window' },
  plugins,
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
    watch: { usePolling: true, interval: 1000 },
    proxy: {
      '/matomo/matomo.php': {
        target: 'http://backend:3000',
        changeOrigin: false,
        xfwd: true
      },
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
    server: {
      deps: {
        inline: ['@mui/x-data-grid']
      }
    },
    coverage: {
      provider: 'istanbul',
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
        'src/utils/devInspector.tsx',
        'src/**/types.*',
        'src/**/index.{js,ts,ts,tsx}',
        'src/**/*[Ss]tyle*',
        'src/components/MatomoTracker/*',
        'src/components/Metrics/*'
      ],
      thresholds: {
        statements: 45.98,
        branches: 34.61,
        functions: 41.54,
        lines: 46.5,
        autoUpdate: isCI
      }
    }
  }
});
