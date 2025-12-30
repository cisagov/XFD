// frontend/vite.config.mts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { visualizer } from 'rollup-plugin-visualizer';
import type { PluginOption } from 'vite';
import { inspectorServer } from '@react-dev-inspector/vite-plugin';

const enableInspector = process.env.ENABLE_INSPECTOR === 'true';
const mode = process.env.MODE || 'development';
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
    hmr: { host: 'localhost', clientPort: 3000 },
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
        statements: 38.97,
        branches: 27.75,
        functions: 33.79,
        lines: 39.39,
        autoUpdate: true
      }
    }
  }
});
