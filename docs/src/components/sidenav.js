import React from 'react';
import { Link } from 'gatsby';
import classNames from 'classnames';

/*
  The sidenav is not loaded by default on the main pages. To include this navigation you can
  add "sidenav: [sidenav name]" in the front-matter of your markdown pages.
  The keys of SIDENAV_ITEMS specify allowed sidenav names.
*/

const SIDENAV_ITEMS = {
  dev: [
    { text: 'Quickstart', link: '/docs/dev/quickstart/' },
    { text: 'Overall System Architecture', link: '/docs/dev/architecture/' },
    { text: 'Frontend', link: '/docs/dev/frontend/' },
    { text: 'REST API', link: '/docs/dev/rest-api/' },
    { text: 'Database', link: '/docs/dev/database/' },
    { text: 'Worker', link: '/docs/dev/worker/' },
    // { text: 'Scheduler', link: '/dev/scheduler/' },
    { text: 'Search', link: '/docs/dev/search/' },
    { text: 'Analytics', link: '/docs/dev/analytics/' },
    { text: 'Deployment', link: '/docs/dev/deployment/' },
    { text: 'Setting up your own instance', link: '/docs/dev/own-instance/' },
    { text: 'Contribution Guidelines', link: '/docs/dev/guidelines/' },
  ],
  'user-guide': [
    { text: 'Quickstart', link: '/docs/user-guide/quickstart/' },
    {
      text: 'Crossfeed Product Overview',
      link: '/docs/user-guide/product-overview/',
    },
    { text: 'Administration', link: '/docs/user-guide/administration/' },
  ],
};

const SidenavBase = ({ current, headings, items }) => {
  const SidenavItem = ({ link, children }) => {
    const isSelected = current === link;

    return (
      <>
        <li className="usa-sidenav__item">
          <Link to={link} className={classNames({ 'usa-current': isSelected })}>
            {children}
          </Link>
          {isSelected && (
            <ul className="usa-sidenav__sublist">
              {/* Only include level 3 headings (###) */}
              {headings
                .filter((e) => e.depth === 3)
                .map(({ value, depth }) => (
                  <li className="usa-sidenav__item" key={value}>
                    <a href={`#${value.replace(/\s/g, '-').toLowerCase()}`}>
                      <span
                        style={{
                          display: 'block',
                          paddingLeft: `${depth - 3}em`,
                        }}
                      >
                        {value}
                      </span>
                    </a>
                  </li>
                ))}
            </ul>
          )}
        </li>
      </>
    );
  };
  return (
    <aside className="usa-layout-docs-sidenav desktop:grid-col-3 padding-bottom-4">
      <nav>
        <ul className="usa-sidenav">
          {items.map((item) => (
            <SidenavItem link={item.link} key={item.link}>
              {item.text}
            </SidenavItem>
          ))}
        </ul>
      </nav>
    </aside>
  );
};

export const Sidenav = (props) => {
  const items = SIDENAV_ITEMS[props.sidenav];
  return items ? <SidenavBase items={items} {...props} /> : null;
};
