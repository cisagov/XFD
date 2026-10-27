import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { Forbidden, NotFound } from 'pages/Errors';

describe('error pages', () => {
  it('renders the forbidden page', () => {
    render(
      <MemoryRouter>
        <Forbidden />
      </MemoryRouter>
    );

    expect(screen.getByText('403')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Access denied' })
    ).toBeInTheDocument();
    expect(
      screen.getByText('You do not have permission to view this page.')
    ).toBeInTheDocument();
  });

  it('renders the not-found page', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );

    expect(screen.getByText('404')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Page not found' })
    ).toBeInTheDocument();
    expect(
      screen.getByText('The page or resource you requested could not be found.')
    ).toBeInTheDocument();
  });
});
