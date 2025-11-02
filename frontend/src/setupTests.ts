import { expect } from 'vitest';
import '@testing-library/jest-dom';
import * as matchers from '@testing-library/jest-dom/matchers';

expect.extend(matchers);

import.meta.env.VITE_TERMS_VERSION = '1';
