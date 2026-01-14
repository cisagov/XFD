// adjust path as needed
import React from 'react';
import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import { NavMenuDrawer } from '../../../components/Header/NavMenuDrawer';
import {
  useUserLevel,
  STANDARD_USER,
  REGIONAL_ADMIN,
  GLOBAL_ADMIN,
  GLOBAL_VIEW
} from '../../../hooks/useUserLevel';
import { Header } from '../../../components/Header/Header';

type MenuItemType = any;

const theme = createTheme();

const renderWithProviders = (ui: React.ReactElement) =>
  render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>{ui}</ThemeProvider>
    </MemoryRouter>
  );

const getToggleDrawerMocks = () => {
  const innerToggle = vi.fn();
  const toggleDrawer = vi.fn().mockReturnValue(innerToggle);
  return { toggleDrawer, innerToggle };
};

const actionItemOnClick = vi.fn();
const objectStoreItem: MenuItemType = {
  menuItemTitle: 'Object Store Item',
  objectStoreParams: { id: 'obj-1' }
};
const subMenuChild: MenuItemType = {
  menuItemTitle: 'Submenu Child',
  objectStoreParams: { id: 'sub-1' }
};

const baseMenuItems: { [section: string]: MenuItemType[] }[] = [
  {
    'Learning Center': [
      {
        menuItemTitle: 'Learning Link',
        path: '/learning'
      },
      {
        menuItemTitle: 'Learning Submenu',
        subMenuItems: [subMenuChild]
      }
    ]
  },
  {
    Main: [
      {
        menuItemTitle: 'Action Item',
        onClick: actionItemOnClick
      },
      objectStoreItem,
      {
        menuItemTitle: 'External HTTP',
        path: 'http://example.com'
      },
      {
        menuItemTitle: 'Mail Link',
        path: 'mailto:test@example.com'
      },
      {
        menuItemTitle: 'Internal Link',
        path: '/internal'
      }
    ]
  }
];

vi.mock('context', () => ({
  useAuthContext: () => ({
    apiPost: vi.fn(),
    logout: vi.fn()
  })
}));

vi.mock('../../../hooks/useUserLevel', () => ({
  useUserLevel: vi.fn(),
  GLOBAL_ADMIN: 4,
  GLOBAL_VIEW: 3,
  REGIONAL_ADMIN: 2,
  STANDARD_USER: 1
}));

const renderHeader = () =>
  render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <Header />
      </ThemeProvider>
    </MemoryRouter>
  );

const mockedUseUserLevel = useUserLevel as unknown as Mock;

const openMobileMenu = async () => {
  const user = userEvent.setup();
  const menuButton = screen.getByRole('button', {
    name: /open mobile menu/i
  });
  await user.click(menuButton);
};

describe('NavMenuDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('respects openDrawer prop (dialog appears only when openDrawer is true)', () => {
    const { toggleDrawer } = getToggleDrawerMocks();

    const { rerender, queryByRole } = renderWithProviders(
      <NavMenuDrawer
        toggleDrawer={toggleDrawer}
        openDrawer={false}
        menuItems={baseMenuItems}
      />
    );

    expect(
      queryByRole('dialog', { name: /navigation menu/i })
    ).not.toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <NavMenuDrawer
            toggleDrawer={toggleDrawer}
            openDrawer={true}
            menuItems={baseMenuItems}
          />
        </ThemeProvider>
      </MemoryRouter>
    );

    expect(
      queryByRole('dialog', { name: /navigation menu/i })
    ).toBeInTheDocument();
  });

  it('onClose calls toggleDrawer(false) and its inner function', async () => {
    const { toggleDrawer, innerToggle } = getToggleDrawerMocks();

    renderWithProviders(
      <NavMenuDrawer
        toggleDrawer={toggleDrawer}
        openDrawer={true}
        menuItems={baseMenuItems}
      />
    );

    const presentationEls = screen.getAllByRole('presentation');
    const container = presentationEls[0];

    fireEvent.keyDown(container, { key: 'Escape', code: 'Escape' });

    expect(toggleDrawer).toHaveBeenCalledWith(false);
    expect(innerToggle).toHaveBeenCalled();
  });

  it('renders dropdown section and reveals its items when expanded', async () => {
    const user = userEvent.setup();
    const { toggleDrawer } = getToggleDrawerMocks();

    renderWithProviders(
      <NavMenuDrawer
        toggleDrawer={toggleDrawer}
        openDrawer={true}
        menuItems={baseMenuItems}
      />
    );

    expect(screen.queryByText('Learning Link')).not.toBeInTheDocument();
    expect(screen.queryByText('Learning Submenu')).not.toBeInTheDocument();

    const learningCenterButton = screen.getByRole('button', {
      name: /learning center/i
    });
    await user.click(learningCenterButton);

    expect(screen.getByText('Learning Link')).toBeInTheDocument();
  });

  it('renders submenu and its children when onMenuItemClick is provided', async () => {
    const user = userEvent.setup();
    const { toggleDrawer } = getToggleDrawerMocks();
    const onMenuItemClick = vi.fn().mockResolvedValue(undefined);

    renderWithProviders(
      <NavMenuDrawer
        toggleDrawer={toggleDrawer}
        openDrawer={true}
        menuItems={baseMenuItems}
        onMenuItemClick={onMenuItemClick}
      />
    );

    const learningCenterButton = screen.getByRole('button', {
      name: /learning center/i
    });
    await user.click(learningCenterButton);

    const learningSubmenuButton = screen.getByRole('menuitem', {
      name: /learning submenu/i
    });
    expect(learningSubmenuButton).toBeInTheDocument();

    await user.click(learningSubmenuButton);

    expect(screen.getByText('Submenu Child')).toBeInTheDocument();
  });

  it('calls onClick for "Action Item" and closes the drawer', async () => {
    const user = userEvent.setup();
    const { toggleDrawer, innerToggle } = getToggleDrawerMocks();

    renderWithProviders(
      <NavMenuDrawer
        toggleDrawer={toggleDrawer}
        openDrawer={true}
        menuItems={baseMenuItems}
      />
    );

    const actionItem = screen.getByRole('menuitem', {
      name: /action item/i
    });

    const toggleCallsBefore = toggleDrawer.mock.calls.length;

    await user.click(actionItem);

    expect(actionItemOnClick).toHaveBeenCalledTimes(1);
    expect(toggleDrawer.mock.calls.length).toBe(toggleCallsBefore + 1);
    expect(innerToggle).toHaveBeenCalledTimes(1);
  });
});

describe('Header / NavMenuDrawer role-based menus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not show Admin Hub for STANDARD_USER', async () => {
    mockedUseUserLevel.mockReturnValue({
      userLevel: STANDARD_USER,
      user_type: 'standard',
      user: null,
      formattedUserType: 'Standard User'
    });

    renderHeader();
    await openMobileMenu();

    const drawer = screen.getByRole('dialog', { name: /navigation menu/i });
    const drawerQueries = within(drawer);

    expect(drawerQueries.queryByText(/admin hub/i)).not.toBeInTheDocument();
  });

  it('shows Admin Hub without Admin Tools for REGIONAL_ADMIN', async () => {
    const user = userEvent.setup();

    mockedUseUserLevel.mockReturnValue({
      userLevel: REGIONAL_ADMIN,
      user_type: 'regionalAdmin',
      user: { isRegistered: true, user_type: 'regionalAdmin' },
      formattedUserType: 'Regional Admin'
    });

    renderHeader();

    const mobileButton = screen.getByRole('button', {
      name: /open mobile menu/i
    });
    await user.click(mobileButton);

    const drawer = screen.getByRole('dialog', {
      name: /navigation menu/i
    });
    const drawerQueries = within(drawer);

    const adminHubToggle = drawerQueries.getByRole('button', {
      name: /admin hub/i
    });
    expect(adminHubToggle).toBeInTheDocument();

    await user.click(adminHubToggle);

    expect(
      drawerQueries.getByRole('menuitem', { name: /manage organizations/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /manage users/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /user registration/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.queryByRole('menuitem', { name: /admin tools/i })
    ).not.toBeInTheDocument();
  });

  it('shows Admin Hub with Admin Tools for GLOBAL_ADMIN', async () => {
    const user = userEvent.setup();

    mockedUseUserLevel.mockReturnValue({
      userLevel: GLOBAL_ADMIN,
      user_type: 'globalAdmin',
      user: { isRegistered: true, user_type: 'globalAdmin' },
      formattedUserType: 'Global Admin'
    });

    renderHeader();

    const mobileButton = screen.getByRole('button', {
      name: /open mobile menu/i
    });
    await user.click(mobileButton);

    const drawer = screen.getByRole('dialog', {
      name: /navigation menu/i
    });
    const drawerQueries = within(drawer);

    const adminHubToggle = drawerQueries.getByRole('button', {
      name: /admin hub/i
    });
    expect(adminHubToggle).toBeInTheDocument();

    await user.click(adminHubToggle);

    const adminToolsItem = drawerQueries.getByRole('menuitem', {
      name: /admin tools/i
    });
    expect(adminToolsItem).toBeInTheDocument();

    expect(
      drawerQueries.getByRole('menuitem', { name: /manage organizations/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /manage users/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /user registration/i })
    ).toBeInTheDocument();
  });

  it('shows Admin Hub without Admin Tools for GLOBAL_VIEW', async () => {
    const user = userEvent.setup();

    mockedUseUserLevel.mockReturnValue({
      userLevel: GLOBAL_VIEW,
      user_type: 'globalView',
      user: { isRegistered: true, user_type: 'globalView' },
      formattedUserType: 'Global View'
    });

    renderHeader();

    const mobileButton = screen.getByRole('button', {
      name: /open mobile menu/i
    });
    await user.click(mobileButton);

    const drawer = screen.getByRole('dialog', {
      name: /navigation menu/i
    });
    const drawerQueries = within(drawer);

    const adminHubToggle = drawerQueries.getByRole('button', {
      name: /admin hub/i
    });
    expect(adminHubToggle).toBeInTheDocument();

    await user.click(adminHubToggle);

    expect(
      drawerQueries.queryByRole('menuitem', { name: /admin tools/i })
    ).not.toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /manage organizations/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /manage users/i })
    ).toBeInTheDocument();
    expect(
      drawerQueries.getByRole('menuitem', { name: /user registration/i })
    ).toBeInTheDocument();
  });
});
