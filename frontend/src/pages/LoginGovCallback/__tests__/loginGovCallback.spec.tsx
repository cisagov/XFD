import React from 'react';
import { render, waitFor } from 'test-utils';
import { LoginGovCallback } from '../LoginGovCallback';

jest.spyOn(Storage.prototype, 'getItem');
const mockGetItem = jest.mocked(localStorage.getItem);

jest.spyOn(Storage.prototype, 'removeItem');
const mockRemoveItem = jest.mocked(localStorage.removeItem);

const mockPost = jest.fn();
const mockLogin = jest.fn();
const { location: originalLocation } = window;

beforeAll(() => {
  // Securely mock window.location instead of overwriting it
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { search: '' } as Location
  });
});

beforeEach(() => {
  mockPost.mockReset();
  mockLogin.mockReset();
});

afterAll(() => {
  // Restore original window.location
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation
  });
  jest.restoreAllMocks();
});

const renderMocked = () => {
  return render(<LoginGovCallback />, {
    authContext: {
      apiPost: mockPost,
      login: mockLogin
    }
  });
};

it('can handle successful OAuth callback', async () => {
  Object.defineProperty(window.location, 'search', {
    configurable: true,
    value: '?state=fake_oauth_state&code=fake_oauth_code'
  });

  mockGetItem
    .mockReturnValueOnce('FAKE_NONCE')
    .mockReturnValueOnce('FAKE_STATE');
  mockPost.mockResolvedValue({ token: 'some_new_token' });

  renderMocked();

  await waitFor(() => {
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost.mock.calls[0][0]).toEqual('/auth/callback');
    expect(mockPost.mock.calls[0][1]).toMatchObject({
      body: {
        state: 'fake_oauth_state',
        code: 'fake_oauth_code',
        nonce: 'FAKE_NONCE',
        origState: 'FAKE_STATE'
      }
    });
  });

  await waitFor(() => {
    expect(mockLogin).toHaveBeenCalledTimes(1);
    expect(mockLogin.mock.calls[0][0]).toEqual('some_new_token');
  });

  await waitFor(() => {
    expect(mockRemoveItem).toHaveBeenCalledTimes(2);
    expect(mockRemoveItem).toHaveBeenCalledWith('nonce');
    expect(mockRemoveItem).toHaveBeenCalledWith('state');
  });
});

it('still navigates home on API errors', async () => {
  Object.defineProperty(window.location, 'search', {
    configurable: true,
    value: '?state=fake_oauth_state&code=fake_oauth_code'
  });

  mockGetItem
    .mockReturnValueOnce('FAKE_NONCE')
    .mockReturnValueOnce('FAKE_STATE');
  mockPost.mockRejectedValue(new Error('some network error'));

  renderMocked();

  await waitFor(() => {
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockLogin).not.toHaveBeenCalled();
  });
});
