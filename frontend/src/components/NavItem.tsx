import React, { useState } from 'react';
import { styled } from '@mui/material/styles';
import { NavLink } from 'react-router-dom';

interface Props {
  path?: string;
  title: string | JSX.Element;
  exact?: boolean;
  onClick?: any;
}

export const NavItem: React.FC<Props> = (props) => {
  const { title, path, exact } = props;

  return (
    <Root>
      <NavLink
        to={path || '/'}
        activeClassName={path !== '#' ? classesNav.activeLink : classesNav.link}
        className={classesNav.link}
        exact={exact}
      >
        {title}
      </NavLink>
    </Root>
  );
};

//Styling
const PREFIX = 'NavItem';

const classesNav = {
  inner: `${PREFIX}-inner`,
  menuButton: `${PREFIX}-menuButton`,
  activeLink: `${PREFIX}-activeLink`,
  activeMobileLink: `${PREFIX}-activeMobileLink`,
  link: `${PREFIX}-link`,
  userLink: `${PREFIX}-userLink`
};

// TODO jss-to-styled codemod: The Fragment root was replaced by div. Change the tag if needed.
const Root = styled('div')(({ theme }) => ({
  [`& .${classesNav.inner}`]: {
    maxWidth: 1440,
    width: '100%',
    margin: '0 auto'
  },

  [`& .${classesNav.menuButton}`]: {
    marginRight: theme.spacing(2),
    display: 'block',
    [theme.breakpoints.up('lg')]: {
      display: 'none'
    }
  },

  [`& .${classesNav.activeLink}`]: {
    '&:after': {
      content: "''",
      position: 'absolute',
      bottom: 0,
      left: 6,
      width: '85%',
      height: 2,
      backgroundColor: 'white'
    }
  },

  [`& .${classesNav.activeMobileLink}`]: {
    fontWeight: 700,
    '&:after': {
      content: "''",
      position: 'absolute',
      top: 0,
      bottom: 0,
      left: 0,
      height: '100%',
      width: '85%',
      backgroundColor: theme.palette.primary.main
    }
  },

  [`& .${classesNav.link}`]: {
    position: 'relative',
    color: 'white',
    textDecoration: 'none',
    margin: `0 ${theme.spacing()}px`,
    padding: theme.spacing(),
    borderBottom: '2px solid transparent',
    fontWeight: 600
  },

  [`& .${classesNav.userLink}`]: {
    display: 'flex',
    alignItems: 'center',
    '& svg': {
      marginRight: theme.spacing()
    }
  }
}));
