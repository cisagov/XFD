import { describe, it, expect } from 'vitest';
import { transformUserData } from '@/utils/transformTableData';
import { User } from 'types';
import { initializeUser, testUsers } from '@/constants/userAndOrgData';

describe('transformUserData', () => {
  it('transforms users with roles into display-friendly fields', () => {
    const result = transformUserData([testUsers[0]]);

    expect(result).toHaveLength(1);

    expect(result[0]).toMatchObject({
      id: '1',
      email: 'jane@example.com',
      roles: testUsers[0].roles,
      organizations: [' Acme Corp', ' Globex'],
      org_acronym: 'ACME',
      organizations_display: 'Acme Corp, Globex'
    });

    expect(result[0].last_logged_in).toMatch(
      /\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} (AM|PM)/
    );
  });

  it('handles users with no roles', () => {
    const result = transformUserData([testUsers[1]]);

    expect(result[0]).toEqual(
      expect.objectContaining({
        roles: [],
        organizations: [],
        org_acronym: '',
        organizations_display: ''
      })
    );
  });

  it('formats last_logged_in when present', () => {
    const result = transformUserData([testUsers[2]]);

    expect(result[0].last_logged_in).toMatch(
      /\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} (AM|PM)/
    );
  });

  it('returns "None" when last_logged_in is null', () => {
    const userWithNoLogin: User = {
      ...initializeUser,
      id: 'no-login',
      email: 'nologin@test.gov',
      last_logged_in: null,
      roles: []
    };

    const result = transformUserData([userWithNoLogin]);

    expect(result[0].last_logged_in).toBe('None');
  });

  it('does not mutate the original users array', () => {
    const original = structuredClone(testUsers);

    transformUserData(testUsers);

    expect(testUsers).toEqual(original);
  });

  it('returns the same number of users as provided', () => {
    const result = transformUserData(testUsers);

    expect(result).toHaveLength(testUsers.length);
  });
});
