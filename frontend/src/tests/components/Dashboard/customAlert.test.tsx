import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CustomAlert from '@/components/Dashboard/CustomAlert';

describe('CustomAlert', () => {
  it('renders default header and default body when no props are provided', () => {
    render(<CustomAlert />);

    expect(screen.getByText('No Data Found')).toBeInTheDocument();

    expect(
      screen.getByText(/No data was found for this organization/i)
    ).toBeInTheDocument();
  });

  it('renders a custom header message when provided', () => {
    render(<CustomAlert headerMsg="Custom Header" />);

    expect(screen.getByText('Custom Header')).toBeInTheDocument();
  });

  it('renders a custom body message when provided', () => {
    render(<CustomAlert bodyMsg="This is a custom body message" />);

    expect(
      screen.getByText('This is a custom body message')
    ).toBeInTheDocument();
  });

  it('does not render when isAlertActive is false', () => {
    const { container } = render(<CustomAlert isAlertActive={false} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('renders a close button when hasOnClose is true', () => {
    render(<CustomAlert hasOnClose />);

    expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
  });

  it('closes the alert when the close button is clicked', async () => {
    const user = userEvent.setup();

    render(<CustomAlert hasOnClose />);

    const closeButton = screen.getByRole('button', {
      name: /close/i
    });

    await user.click(closeButton);

    expect(screen.queryByText('No Data Found')).not.toBeInTheDocument();
  });

  it('renders ReactNode body content correctly', () => {
    render(
      <CustomAlert
        bodyMsg={
          <span>
            <strong>Bold text</strong> inside body
          </span>
        }
      />
    );

    expect(screen.getByText('Bold text')).toBeInTheDocument();

    expect(screen.getByText(/inside body/i)).toBeInTheDocument();
  });
});
