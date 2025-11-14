module.exports = {
  env: {
    browser: true,
    es6: true,
    node: true
  },
  parser: '@typescript-eslint/parser',
  extends: [
    'plugin:prettier/recommended',
    'plugin:react/recommended',
    'plugin:@typescript-eslint/eslint-recommended'
  ],
  plugins: [
    'react',
    'react-hooks',
    'prettier',
    '@typescript-eslint',
    'unused-imports'
  ],
  parserOptions: {
    ecmaFeatures: { jsx: true },
    ecmaVersion: 2018,
    sourceType: 'module'
  },
  rules: {
    'prettier/prettier': 'error',
    'react/prop-types': 0,
    'react/display-name': 0,
    'no-restricted-imports': [
      'error',
      {
        paths: ['@mui/material', '@mui/icons-material']
      }
    ],
    'unused-imports/no-unused-imports': 'error',
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        vars: 'all',
        args: 'after-used',
        ignoreRestSiblings: true,
        varsIgnorePattern: '^_',
        argsIgnorePattern: '^_',
        caughtErrors: 'none'
      }
    ]
  },
  overrides: [
    {
      files: [
        '**/*.test.ts',
        '**/*.test.tsx',
        '**/*.spec.ts',
        '**/*.spec.tsx',
        '**/__tests__/**/*.{ts,tsx,js,jsx}'
      ],
      rules: {
        '@typescript-eslint/no-unused-vars': 'off',
        'unused-imports/no-unused-imports': 'off'
      }
    }
  ],
  settings: {
    react: { version: 'detect' },
    'import/resolver': { typescript: { project: './frontend/tsconfig.json' } }
  },
  globals: {
    Atomics: 'readonly',
    SharedArrayBuffer: 'readonly'
  }
};
