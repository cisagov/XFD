import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@/test-utils';
import { authCtx } from '@/test-utils/authCtx';
import QueueMonitorView from '../../../pages/Scans/QueueMonitorView';

describe('QueueMonitorView', () => {
  it('keeps the grid mounted while queue data is loading', () => {
    const apiPost = vi.fn(() => new Promise(() => {}));

    render(<QueueMonitorView />, {
      authContext: {
        ...authCtx,
        apiPost
      }
    });

    expect(screen.getByRole('grid')).toBeInTheDocument();
  });

  it('renders the standard toolbar after queue data loads', async () => {
    const apiPost = vi.fn().mockResolvedValue({
      result: [
        {
          name: 'queue-1',
          messages_available: 1,
          messages_in_flight: 2,
          messages_delayed: 3
        }
      ],
      count: 1
    });

    render(<QueueMonitorView />, {
      authContext: {
        ...authCtx,
        apiPost
      }
    });

    expect(
      await screen.findByRole('button', { name: /filters/i })
    ).toBeInTheDocument();
    expect(await screen.findByText('queue-1')).toBeInTheDocument();
  });
});
