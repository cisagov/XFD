import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import { VideoLibrary, Article, LibraryBooks } from '@mui/icons-material';
import { isResourceVisible } from './helpers/index';

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

// const isResourceVisible = (response: string) => {
//   const r = response.toLowerCase();
//   return r === "no" || r === "not in scope" || r === "not started" ? true : false;
// }

export const RSCQuestion: React.FC<Props> = ({ categories }) => {
  return (
    <div>
      {categories.map((category, catIndex) => (
        <Box key={catIndex} sx={{ marginBottom: 4 }}>
          <Typography
            variant="h5"
            gutterBottom
            component="div"
            sx={{ marginTop: 2, color: '#1976d2' }}
          >
            {category.name}
          </Typography>
          {category.entries.map((entry, entryIndex) => (
            <Box
              key={entryIndex}
              sx={{
                width: '100%',
                bgcolor: '#f0f0f0',
                padding: 2,
                borderRadius: 2,
                marginBottom: 2
              }}
            >
              <Typography variant="h6" gutterBottom>
                Question {entry.question.number}
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
                Response: {entry.selection}
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
                    <Typography variant="h6" gutterBottom>
                      Recommended Resources
                    </Typography>
                    {entry.question.resources.map((resource, resIndex) => (
                      <Box
                        key={resIndex}
                        sx={{
                          borderBottom: '1px solid #ccc',
                          paddingBottom: 1,
                          marginBottom: 1
                        }}
                      >
                        <Typography variant="subtitle1">
                          <VideoLibrary />
                          {resource.type.charAt(0).toUpperCase() +
                            resource.type.slice(1)}
                        </Typography>
                        <Typography variant="subtitle2">
                          {resource.name}
                        </Typography>
                        <Typography variant="body2">
                          {resource.description}
                        </Typography>
                        <Button
                          variant="outlined"
                          color="primary"
                          href={resource.url}
                          target="_blank"
                        >
                          Visit Resource
                        </Button>
                      </Box>
                    ))}
                  </Box>
                )}
            </Box>
          ))}
        </Box>
      ))}
    </div>
  );
};
