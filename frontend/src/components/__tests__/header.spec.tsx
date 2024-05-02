import React from 'react';
import { render, testUser, testOrganization } from 'test-utils';
import { Header } from '../Header';

jest.mock('@elastic/react-search-ui', () => ({
  withSearch: () => (comp: any) => comp
}));

describe('Header component', () => {
  it('matches snapshot', () => {
    const { asFragment } = render(<Header />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('can expand drawer', async () => {
    const { queryByTestId } = render(<Header />);
    expect(queryByTestId('mobilenav')).not.toBeInTheDocument();
  });

  it('shows no links for unauthenticated user', () => {
    const { queryByText } = render(<Header />, {
      authContext: {
        user: { ...testUser, userType: 'standard', isRegistered: false },
        currentOrganization: { ...testOrganization }
      }
    });
    ['Vulnerabilities', 'Risk Summary', 'Scans'].forEach((expected) => {
      expect(queryByText(expected)).not.toBeInTheDocument();
    });
  });

  it('shows correct links for ORG_USER', () => {
    const { getByText, queryByText } = render(<Header />, {
      authContext: {
        user: { ...testUser, userType: 'standard', isRegistered: true },
        currentOrganization: { ...testOrganization }
      }
    });
    ['Overview', 'Inventory'].forEach((expected) => {
      expect(getByText(expected)).toBeInTheDocument();
    });
    ['Scans'].forEach((notExpected) => {
      expect(queryByText(notExpected)).not.toBeInTheDocument();
    });
  });

  it('shows correct links for ORG_ADMIN', () => {
    const { getByText } = render(<Header />, {
      authContext: {
        user: { ...testUser, userType: 'standard', isRegistered: true },
        currentOrganization: { ...testOrganization }
      }
    });
    ['Overview', 'Inventory'].forEach((expected) => {
      expect(getByText(expected)).toBeInTheDocument();
    });
    // ['Manage Organizations', 'Manage Users'].forEach((notExpected) => {
    //   expect(queryByText(notExpected)).not.toBeInTheDocument();
    // });
  });

  it('shows correct links for GLOBAL_ADMIN', () => {
    const { getByText } = render(<Header />, {
      authContext: {
        user: { ...testUser, userType: 'globalAdmin', isRegistered: true },
        currentOrganization: { ...testOrganization }
      }
    });
    ['Overview', 'Inventory'].forEach((expected) => {
      expect(getByText(expected)).toBeInTheDocument();
    });
  });
});
