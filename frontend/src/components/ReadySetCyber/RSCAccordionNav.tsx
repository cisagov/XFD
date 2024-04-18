import React from 'react';
import { Accordion, AccordionDetails, AccordionSummary } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { HashLink } from 'react-router-hash-link';

interface Props {
  categories: Category[];
}

export interface Category {
  name: string;
}

export const RSCAccordionNav: React.FC<Props> = ({ categories }) => {
  return (
    <Accordion>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        aria-controls="panel1a-content"
        id="panel1a-header"
        style={{ outline: 'none' }}
      >
        {' '}
        Categories
      </AccordionSummary>
      {categories.map((category, index) => (
        <AccordionDetails key={index}>
          <HashLink
            style={{ textDecoration: 'none', outline: 'none', color: 'black' }}
            to={`#${category.name}`}
          >
            {category.name}
          </HashLink>
        </AccordionDetails>
      ))}
    </Accordion>
  );
};
