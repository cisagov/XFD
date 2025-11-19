import React from 'react';
import { logger } from '@/utils/logger';
import { useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';
import {
  useUserLevel,
  GLOBAL_ADMIN,
  REGIONAL_ADMIN,
  STANDARD_USER
} from 'hooks/useUserLevel';
import {
  AppBar,
  Box,
  Button,
  IconButton,
  Toolbar,
  Typography
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import cisaLogo from 'assets/cisaSeal.svg';
import { NavMenuButton } from './NavMenuButton';
import { NavMenuDrawer } from './NavMenuDrawer';
import {
  MAILTO_BUG,
  MAILTO_FEEDBACK,
  MAILTO_INQUIRY
} from '@/constants/emailLinks';
import { ENDPOINTS } from '@/constants/endpoints';
import { ROUTES } from '@/constants/routes';

export interface MenuItemType {
  menuItemTitle: string;
  path?: string;
  objectStoreParams?: { bucket_name: string; object_key: string };
  users?: number;
  onClick?: any;
  href?: string;
  subMenuItems?: MenuItemType[];
}

// TODO: Update bucket/key names when provided.
const LEARNING_CENTER_DOC_BUCKET_NAME = import.meta.env
  .VITE_LEARNING_CENTER_DOC_BUCKET_NAME as string;

const LEARNING_CENTER_DOC_KEYS = {
  glossary: 'CyHy Dashboard VS Glossary.pdf',
  faq: 'CyHy Dashboard VS FAQ.pdf',
  methodology: 'CyHy Dashboard VS Methodology.pdf',
  userGuide: 'CyHy Dashboard User Guide.pdf',
  communications: 'Vulnerability Snapshot Communications Sector.pdf',
  financialServices: 'Vulnerability Snapshot Financial Services Sector.pdf',
  foodAndAgriculture: 'Vulnerability Snapshot Food and Agriculture Sector.pdf',
  healthcareAndPublicHealth:
    'Vulnerability Snapshot Healthcare and Public Health Sector.pdf',
  informationTechnology:
    'Vulnerability Snapshot Information Technology Sector.pdf',
  transportationSystems:
    'Vulnerability Snapshot Transportation Systems Sector.pdf',
  waterAndWastewater:
    'Vulnerability Snapshot Water and Wastewater Systems Sector.pdf'
};

export const Header: React.FC = () => {
  const history = useHistory();
  const { apiPost, logout } = useAuthContext();
  const { userLevel, user_type } = useUserLevel();
  const [openDrawer, setOpenDrawer] = React.useState(false);
  const toggleDrawer = (newOpen: boolean) => () => {
    setOpenDrawer(newOpen);
  };

  const roleBasedPath = () => {
    switch (user_type) {
      case 'globalAdmin':
        return ROUTES.GLOBAL_ADMIN_DASHBOARD;
      case 'globalView':
        return ROUTES.GLOBAL_VIEW_DASHBOARD;
      case 'regionalAdmin':
        return ROUTES.REGION_ADMIN_DASHBOARD;
      case 'standard':
        return ROUTES.VSDASHBOARD;
      default:
        return ROUTES.LOGIN;
    }
  };

  const adminHubMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Admin Tools',
      path: ROUTES.ADMIN_TOOLS,
      users: GLOBAL_ADMIN
    },
    {
      menuItemTitle: 'Manage Organizations',
      path: ROUTES.ORGANIZATIONS,
      users: REGIONAL_ADMIN
    },
    {
      menuItemTitle: 'Manage Users',
      path: ROUTES.USERS,
      users: REGIONAL_ADMIN
    },
    {
      menuItemTitle: 'User Registration',
      path: roleBasedPath(),
      users: REGIONAL_ADMIN
    }
  ].filter(({ users }) => users <= userLevel);

  const userMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Account Settings',
      path: ROUTES.SETTINGS,
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Logout',
      users: STANDARD_USER,
      onClick: logout
    }
  ].filter(({ users }) => users <= userLevel);

  const vulnScanningMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Vulnerability Scanning',
      path: ROUTES.VSDASHBOARD,
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const supportMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'General Questions',
      path: MAILTO_INQUIRY,
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Report Bug',
      path: MAILTO_BUG,
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Send Feedback',
      path: MAILTO_FEEDBACK,
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const inventoryMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Findings Library',
      path: ROUTES.INVENTORY,
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const handleLogoClick = () => {
    history.push(ROUTES.VSDASHBOARD);
  };

  const sectorVulnSnapshotsMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Communications',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.communications
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Financial Services',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.financialServices
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Food and Agriculture',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.foodAndAgriculture
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Healthcare and Public Health',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.healthcareAndPublicHealth
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Information Technology',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.informationTechnology
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Transportation Systems',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.transportationSystems
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Water and Wastewater Systems',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.waterAndWastewater
      },
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const learningCenterMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'CISA Resources',
      path: 'https://www.cisa.gov',
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Sector Vulnerability Snapshots',
      users: STANDARD_USER,
      // Nest sectorVulnSnapshotsMenuItems here
      subMenuItems: sectorVulnSnapshotsMenuItems
    },
    {
      menuItemTitle: 'User Guide',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.userGuide
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'VS FAQ',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.faq
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'VS Glossary',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.glossary
      },
      users: STANDARD_USER
    },

    {
      menuItemTitle: 'VS Methodology',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.methodology
      },
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleLogoClick();
    }
  };

  const handleMenuClick = async (item: MenuItemType) => {
    if (item.path) {
      window.open(item.path, '_blank');
    } else if (item.objectStoreParams) {
      try {
        const response = await apiPost<{ url: string }>(
          ENDPOINTS.OBJECT_STORE_PRESIGNED_URL,
          {
            body: item.objectStoreParams
          }
        );
        if (response.url) {
          window.open(response.url, '_blank');
        } else {
          logger.error('Header.handleMenuClick: Presigned URL missing', {
            item: item.objectStoreParams
          });
        }
      } catch (err) {
        logger.error('Failed to fetch presigned url:', err);
      }
    }
  };

  const headerLogo = (
    <>
      <Box
        component="img"
        src={cisaLogo}
        sx={{ height: 60 }}
        alt="Cybersecurity & Infrastructure Security Agency Logo"
      />
      <Typography
        variant="h1"
        sx={{
          fontSize: '22px',
          color: 'primary.darker',
          ml: 1
        }}
      >
        CyHy Dashboard
      </Typography>
    </>
  );

  const allMenuItems: { [section: string]: MenuItemType[] }[] = [
    { 'Vulnerability Scanning': vulnScanningMenuItems },
    { 'Findings Library': inventoryMenuItems },
    { 'Learning Center': learningCenterMenuItems },
    { Support: supportMenuItems },
    userLevel > 1 ? { 'Admin Hub': adminHubMenuItems } : {},
    { 'My Account': userMenuItems }
  ];

  const headerLogoWrapper = (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'left',
        width: '100%'
      }}
    >
      <Button
        component={Box}
        onClick={handleLogoClick}
        onKeyDown={handleKeyDown}
        aria-label="Navigate to VS Dashboard"
        role="link"
        tabIndex={0}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'left',
          pr: 1,
          py: 0,
          pl: 0,
          transition: 'margin-left 0.3s ease-in-out',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'transparent',
            textDecoration: 'none',
            '.MuiTypography-root': {
              color: 'primary.main'
            }
          },
          '&:active': {
            backgroundColor: 'transparent'
          },
          '&:focus-visible': {
            outline: `2px solid`,
            outlineOffset: '2px'
          }
        }}
      >
        {headerLogo}
      </Button>
    </Box>
  );

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: 'neutrals.white',
        borderBottom: '0.5px solid',
        borderColor: 'neutrals.light',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '84px',
        zIndex: (theme) => theme.zIndex.appBar
      }}
    >
      <Toolbar disableGutters sx={{ maxWidth: '1152px', width: '100%', p: 0 }}>
        {userLevel > 0 ? headerLogoWrapper : headerLogo}
        {userLevel > 0 && (
          <>
            {allMenuItems.map((sectionObj, index) => {
              const [title, menuItems] = Object.entries(sectionObj)[0] || [];
              const padding =
                userLevel === 1 && title === 'Learning Center'
                  ? 6
                  : userLevel === 1
                    ? 1
                    : 0;
              if (!title || !menuItems) {
                return null;
              }
              return (
                <Box key={title + index} sx={{ mr: padding }}>
                  <NavMenuButton
                    title={title}
                    menuItems={menuItems}
                    onMenuItemClick={handleMenuClick}
                  />
                </Box>
              );
            })}
            <IconButton
              sx={{
                display: { xs: 'flex', xl: 'none' },
                color: 'primary.dark'
              }}
              aria-label="Open mobile menu"
              aria-haspopup="true"
              aria-controls={openDrawer ? 'mobile-menu' : undefined}
              aria-expanded={openDrawer ? 'true' : undefined}
              onClick={toggleDrawer(!openDrawer)}
            >
              <MenuIcon />
            </IconButton>
            <NavMenuDrawer
              openDrawer={openDrawer}
              toggleDrawer={toggleDrawer}
              menuItems={allMenuItems}
              onMenuItemClick={handleMenuClick}
            />
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};
