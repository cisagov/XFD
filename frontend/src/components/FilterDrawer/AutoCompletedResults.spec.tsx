import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { AutoCompleteResults } from './AutoCompletedResults';

// Mock MUI components to avoid theme issues
vi.mock('@mui/material', async () => {
  const actual = await vi.importActual('@mui/material');
  return {
    ...actual,
    useTheme: () => ({
      palette: {
        primary: { dark: '#1976d2' },
        grey: { 700: '#616161' }
      }
    })
  };
});

describe('AutoCompleteResults', () => {
  const mockValues = [
    {
      id: { raw: 'option-1' },
      text: { raw: 'First Option' }
    },
    {
      id: { raw: 'option-2' },
      text: { raw: 'Second Option' }
    },
    {
      id: { raw: 'option-3' },
      text: { raw: 'Third Option' }
    }
  ];

  const defaultProps = {
    open: true,
    anchorEl: document.createElement('div'),
    values: mockValues
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all menu items when values are provided', () => {
    render(<AutoCompleteResults {...defaultProps} />);

    expect(screen.getByText('First Option')).toBeTruthy();
    expect(screen.getByText('Second Option')).toBeTruthy();
    expect(screen.getByText('Third Option')).toBeTruthy();
  });

  it('renders correct number of menu items', () => {
    render(<AutoCompleteResults {...defaultProps} />);

    const menuItems = screen.getAllByRole('menuitem');
    expect(menuItems).toHaveLength(3);
  });

  it('uses the correct key for each menu item', () => {
    render(<AutoCompleteResults {...defaultProps} />);

    const menuItems = screen.getAllByRole('menuitem');

    // Check that each menu item has the expected text content
    expect(menuItems[0]).toHaveTextContent('First Option');
    expect(menuItems[1]).toHaveTextContent('Second Option');
    expect(menuItems[2]).toHaveTextContent('Third Option');
  });

  it('renders empty popover when no values are provided', () => {
    const emptyProps = {
      ...defaultProps,
      values: []
    };

    render(<AutoCompleteResults {...emptyProps} />);

    const menuItems = screen.queryAllByRole('menuitem');
    expect(menuItems).toHaveLength(0);
  });

  it('handles single value correctly', () => {
    const singleValueProps = {
      ...defaultProps,
      values: [
        {
          id: { raw: 'single-option' },
          text: { raw: 'Only Option' }
        }
      ]
    };

    render(<AutoCompleteResults {...singleValueProps} />);

    expect(screen.getByText('Only Option')).toBeTruthy();

    const menuItems = screen.getAllByRole('menuitem');
    expect(menuItems).toHaveLength(1);
  });

  it('handles special characters in text content', () => {
    const specialCharProps = {
      ...defaultProps,
      values: [
        {
          id: { raw: 'special-1' },
          text: { raw: 'Option with & special chars!' }
        },
        {
          id: { raw: 'special-2' },
          text: { raw: 'Option with "quotes" and numbers 123' }
        }
      ]
    };

    render(<AutoCompleteResults {...specialCharProps} />);

    expect(screen.getByText('Option with & special chars!')).toBeTruthy();
    expect(
      screen.getByText('Option with "quotes" and numbers 123')
    ).toBeTruthy();
  });

  it('passes through additional popover props', () => {
    const propsWithAdditional = {
      ...defaultProps,
      'data-testid': 'custom-popover',
      elevation: 8
    };

    render(<AutoCompleteResults {...propsWithAdditional} />);

    // Check that the popover has the custom test id
    const popover = screen.getByTestId('custom-popover');
    expect(popover).toBeTruthy();
  });

  it('does not render when open is false', () => {
    const closedProps = {
      ...defaultProps,
      open: false
    };

    render(<AutoCompleteResults {...closedProps} />);

    // When popover is closed, menu items shouldn't be visible
    const menuItems = screen.queryAllByRole('menuitem');
    expect(menuItems).toHaveLength(0);
  });

  it('handles long text content without breaking', () => {
    const longTextProps = {
      ...defaultProps,
      values: [
        {
          id: { raw: 'long-text' },
          text: {
            raw: 'This is a very long option text that should still render properly without causing any layout issues or breaking the component functionality'
          }
        }
      ]
    };

    render(<AutoCompleteResults {...longTextProps} />);

    expect(screen.getByText(/This is a very long option text/)).toBeTruthy();
  });

  it('renders with different anchor elements', () => {
    const buttonAnchor = document.createElement('button');
    buttonAnchor.textContent = 'Click me';

    const buttonAnchorProps = {
      ...defaultProps,
      anchorEl: buttonAnchor
    };

    render(<AutoCompleteResults {...buttonAnchorProps} />);

    expect(screen.getByText('First Option')).toBeTruthy();
    expect(screen.getByText('Second Option')).toBeTruthy();
  });
});
