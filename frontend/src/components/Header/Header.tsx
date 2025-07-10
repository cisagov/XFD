import React from 'react';
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
  Typography,
  useTheme
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import cisaLogo from 'assets/cisaSeal.svg';
import { NavMenuButton } from './NavMenuButton';
import { NavMenuDrawer } from './NavMenuDrawer';

export interface MenuItemType {
  menuItemTitle: string;
  path?: string;
  objectStoreParams?: { bucket_name: string; object_key: string };
  users?: number;
  onClick?: any;
  href?: string;
}

// TODO: Update bucket/key names when provided.
const LEARNING_CENTER_DOC_BUCKET_NAME = process.env
  .REACT_APP_LEARNING_CENTER_DOC_BUCKET_NAME as string;

const LEARNING_CENTER_DOC_KEYS = {
  glossary: 'vs_glossary.pdf',
  faq: 'vs_faq.pdf',
  methodology: 'vs_methodology.pdf'
};

export const Header: React.FC = () => {
  const history = useHistory();
  const { apiPost, logout } = useAuthContext();
  const theme = useTheme();
  const { userLevel } = useUserLevel();
  const [openDrawer, setOpenDrawer] = React.useState(false);
  const toggleDrawer = (newOpen: boolean) => () => {
    setOpenDrawer(newOpen);
  };
  const adminHubMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Admin Tools',
      path: '/admin-tools',
      users: GLOBAL_ADMIN
    },
    {
      menuItemTitle: 'User Registration',
      path: '/region-admin-dashboard',
      users: REGIONAL_ADMIN
    },
    {
      menuItemTitle: 'Manage Organizations',
      path: '/organizations',
      users: REGIONAL_ADMIN
    },
    {
      menuItemTitle: 'Manage Users',
      path: '/users',
      users: REGIONAL_ADMIN
    }
  ].filter(({ users }) => users <= userLevel);

  const userMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Account Settings',
      path: '/settings',
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Logout',
      path: '/settings',
      users: STANDARD_USER,
      onClick: logout
    }
  ].filter(({ users }) => users <= userLevel);

  // const scanningResults: MenuItemType[] = [
  //   {
  //     menuItemTitle: 'Overview',
  //     path: '/overview',
  //     users: STANDARD_USER
  //   },
  //   {
  //     menuItemTitle: 'Vulnerability Scanning',
  //     path: '/VSDashboard',
  //     users: STANDARD_USER
  //   }
  // ].filter(({ users }) => users <= userLevel);

  const vulnScanningMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Vulnerability Scanning',
      path: '/VSDashboard',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const supportMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Report Bug',
      path: 'mailto:vulnerability@mail.cisa.dhs.gov?subject=CyHy%20Dashboard%20Bug%20Report&body=1.%20What%20issue%20did%20you%20experience%3F%20Briefly%20describe%20the%20bug.%0A%0A2.%20What%20actions%20did%20you%20take%20before%20the%20bug%20happened%3F%20List%20each%20step%20clearly%20and%20in%20order.%0A%0A3.%20What%20did%20you%20expect%20to%20happen%3F%20Tell%20us%20what%20you%20thought%20should%20happen.%0A%0A4.%20What%20happened%20instead%3F%20Explain%20what%20actually%20happened.%0A%0A5.%20What%20environment%20and%20permissions%20were%20you%20using%3F%20Include%20your%20browser%2C%20operating%20system%2C%20and%20CyHy%20dashboard%20user%20role.%0A%0A6.%20Is%20there%20anything%20else%20we%20should%20know%3F%20Attach%20or%20list%20screenshots%2C%20errors%20messages%2C%20or%20additional%20content.%0A%0ANote%3A%20Please%20try%20refreshing%20the%20browser%2C%20clearing%20cookies%2Fcache%2C%20and%2For%20rebooting%20the%20system%20to%20mitigate%20any%20bugs%20before%20you%20submit.%20Thank%20you%21',
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Send Feedback',
      path: 'mailto:vulnerability@mail.cisa.dhs.gov?subject=Feedback%20for%20the%20CyHy%20Dashboard&body=1.%20What%20worked%20well%20for%20you%3F%0A%20%20%20%20Consider%3A%20Were%20there%20any%20features%20or%20aspects%20of%20the%20dashboard%20that%20really%20stood%20out%20or%20made%20your%20experience%20easier%3F%0A%0A2.%20What%20could%20be%20improved%3F%0A%20%20%20%20Consider%3A%20Did%20you%20run%20into%20any%20challenges%20or%20notice%20something%20that%20could%20work%20better%3F%0A%0A3.%20Was%20it%20easy%20to%20use%3F%0A%20%20%20%20Consider%3A%20How%20intuitive%20did%20you%20find%20the%20dashboard%3F%20Was%20it%20simple%20to%20navigate%20and%20accomplish%20your%20goals%3F%0A%0A4.%20Any%20additional%20suggestions%3F%0A%20%20%20%20Consider%3A%20Is%20there%20anything%20specific%20you%E2%80%99d%20love%20to%20see%20added%20or%20changed%20to%20make%20the%20dashboard%20more%20useful%3F%0A',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const inventoryMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Findings Library',
      path: '/inventory',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const handleLogoClick = () => {
    history.push('/VSDashboard');
  };

  const learningCenterMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'VS Glossary',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.glossary
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
      menuItemTitle: 'VS Methodology',
      objectStoreParams: {
        bucket_name: LEARNING_CENTER_DOC_BUCKET_NAME,
        object_key: LEARNING_CENTER_DOC_KEYS.methodology
      },
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'CISA Resources',
      path: 'https://www.cisa.gov',
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
          '/v1/object-store/presigned-url',
          {
            body: item.objectStoreParams
          }
        );
        if (response.url) {
          window.open(response.url, '_blank');
        } else {
          console.error('Presigned URL missing');
        }
      } catch (err) {
        console.error('Failed to fetch presigned url:', err);
      }
    }
  };

  const headerLogo = (
    <>
      <Box component="img" src={cisaLogo} sx={{ height: 60 }} alt="CISA Logo" />
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
    // { 'Scanning Results': scanningResults },
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
        zIndex: theme.zIndex.FilterDrawerV2 + 1
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
