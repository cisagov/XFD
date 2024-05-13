import React from 'react';
import { Box, Button, Grid, Typography, Radio, Divider } from '@mui/material';
import { isResourceVisible } from './helpers/index';
import { IconFilter } from './components/index';
import { Stack } from '@mui/system';

interface Props {
  categories: Category[];
}

export interface Category {
  entries: Entry[];
  name: string;
}

export interface Entry {
  question: Question;
  selection: string;
}

interface Question {
  description: string;
  longForm: string;
  name: string;
  number: string;
  resources: Resource[];
}

interface Resource {
  description: string;
  name: string;
  type: string;
  url: string;
}
// Concatenates the last one or two characters of a string
const questionNumber = (n: string) => {
  return n.charAt(n.length - 2) === '0' ? n.slice(-1) : n.slice(-2);
};

export const RSCQuestion: React.FC<Props> = ({ categories }) => {
  return (
    <Box>
      {categories.map((category, catIndex) => (
        <Box
          key={catIndex}
          sx={{
            marginBottom: 4,
            pageBreakInside: 'avoid' // Prevent page breaks inside categories for PDF
          }}
        >
          <Typography
            variant="h5"
            gutterBottom
            component="div"
            sx={{ marginTop: 2, color: '#1976d2' }}
            id={category.name}
            style={{ fontWeight: 'bold', color: '#003E67' }}
          >
            {category.name}
          </Typography>
          {category.entries.map((entry, entryIndex) => (
            <Box
              key={entryIndex}
              sx={{
                width: '100%',
                bgcolor: '#F5FAFC',
                padding: 2,
                borderRadius: 2,
                marginBottom: 2,
                border: '.1rem solid #B8D9E8',
                pageBreakInside: 'avoid', // Prevent page breaks inside questions for PDF
                '@media print': {
                  marginBottom: 4 // Increase this value to add more space between questions in the PDF only
                }
              }}
            >
              <Typography
                variant="h6"
                gutterBottom
                style={{ color: '#003E67' }}
                sx={{
                  marginTop: 2,
                  color: '#1976d2',
                  '&:focus': {
                    outline: '2px solid #000' // Change this to the desired outline style
                  }
                }}
                tabIndex={0}
              >
                Question {questionNumber(entry.question.number)}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                {entry.question.longForm}
              </Typography>
              {entry.question.description && (
                <Typography variant="body2" sx={{ marginBottom: 2 }}>
                  {entry.question.description}
                </Typography>
              )}
              <Typography variant="subtitle2" gutterBottom>
                <Grid
                  container
                  sx={{
                    alignItems: 'center',
                    backgroundColor: 'white',
                    width: 'fit-content',
                    border: '.1rem solid #0078AE',
                    borderRadius: 1
                  }}
                >
                  <Grid item marginLeft={'-0.25em'}>
                    <Radio checked={true} disabled={true} />
                  </Grid>
                  <Grid
                    item
                    paddingRight={'0.5em'}
                    style={{ color: '#0078AE', fontWeight: 'bold' }}
                  >
                    {entry.selection}
                  </Grid>
                </Grid>
              </Typography>
              {entry.question.resources.length > 0 &&
                isResourceVisible(entry.selection) && (
                  <Box
                    sx={{
                      bgcolor: 'white',
                      borderRadius: 1,
                      padding: 2,
                      marginTop: 1
                    }}
                  >
                    <Typography
                      variant="h6"
                      gutterBottom
                      style={{ color: '#003E67' }}
                    >
                      Recommended Resources
                    </Typography>
                    {entry.question.resources.map((resource, resIndex) => (
                      <Box
                        key={resIndex}
                        sx={{
                          paddingBottom: 1,
                          marginBottom: 1
                        }}
                      >
                        <Stack spacing={2}>
                          <Stack
                            direction="row"
                            spacing={2}
                            alignItems="center"
                          >
                            <IconFilter type={resource.type} />
                            <Typography
                              variant="subtitle1"
                              style={{ color: '#00528' }}
                            >
                              {resource.type.charAt(0).toUpperCase() +
                                resource.type.slice(1)}
                            </Typography>
                          </Stack>

                          <Typography
                            variant="subtitle2"
                            style={{ color: '#0078ae' }}
                          >
                            {resource.name}
                          </Typography>
                          <Typography variant="body2">
                            {resource.description}
                          </Typography>
                          <Button
                            variant="contained"
                            href={resource.url}
                            target="_blank"
                            style={{
                              color: 'white',
                              backgroundColor: '#0078ae'
                            }}
                            sx={{
                              width: 'fit-content',
                              '@media print': {
                                boxShadow: 'none' // Remove shadows when printing
                              }
                            }}
                          >
                            Visit Resource
                          </Button>
                          <Divider />
                        </Stack>
                      </Box>
                    ))}
                  </Box>
                )}
            </Box>
          ))}
        </Box>
      ))}
    </Box>
  );
};
