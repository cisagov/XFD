import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import { Box, Typography, ButtonBase } from '@mui/material';
import { styled } from '@mui/material/styles';
import { Result } from 'context/SearchProvider';
// @ts-ignore:next-line
import { parseISO, formatDistanceToNow } from 'date-fns';
import DOMPurify from 'dompurify';

// Sync this with the backend client in es-client.ts.
export interface WebpageRecord {
  webpage_id: string;
  webpage_createdAt: Date;
  webpage_updatedAt: Date;
  webpage_syncedAt: Date;
  webpage_lastSeen: Date;
  webpage_s3Key: string;
  webpage_url: string;
  webpage_status: string | number;
  webpage_domainId: string;
  webpage_discoveredById: string;

  // Added before elasticsearch insertion (not present in the database):
  suggest?: { input: string | string[]; weight: number }[];
  parent_join?: {
    name: 'webpage';
    parent: string;
  };
  webpage_body?: string;
}

interface Highlight {
  webpage_body: string[];
}

interface Props extends Result {
  onDomainSelected(domainId: string): void;
  selected?: boolean;
  inner_hits?: {
    webpage?: {
      hits: {
        hits: { _source: WebpageRecord; highlight: Highlight }[];
        max_score: number;
        total: {
          value: number;
          relation: string;
        };
      };
    };
  };
}

const StyledButtonBase = styled(ButtonBase)(({ theme }) => ({
  display: 'block',
  textAlign: 'left',
  width: '100%',
  borderRadius: theme.shape.borderRadius,
  border: `2px solid #DCDEE0`,
  padding: theme.spacing(2),
  marginBottom: '12px',
  cursor: 'pointer',
  backgroundColor: theme.palette.background.paper,
  '&:hover': {
    backgroundColor: theme.palette.primary.light
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.primary.main}`,
    outlineOffset: 2,
    backgroundColor: theme.palette.primary.light
  }
}));

const filterExpanded = (
  data: any[],
  isExpanded: boolean,
  count: number = 3
) => {
  return isExpanded ? data : data.slice(0, count);
};

export const ResultCard: React.FC<Props> = (props) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const {
    id,
    name,
    ip,
    updated_at,
    services,
    vulnerabilities,
    inner_hits,
    onDomainSelected
  } = props;

  const toggleExpanded = (key: string) => {
    setExpanded((expanded) => ({
      ...expanded,
      [key]: expanded[key] ? !expanded[key] : true
    }));
  };

  let last_seen;

  const history = useHistory();
  try {
    last_seen = formatDistanceToNow(parseISO(updated_at.raw));
  } catch (e) {
    last_seen = '';
  }

  const onClick = () => {
    onDomainSelected(id.raw);
    history.push(`/inventory/domain/${id.raw}`);
  };

  const ports = services.raw.reduce(
    (acc, nextService) => [...acc, nextService.port],
    []
  );

  const products = services.raw.reduce(
    (acc, nextService) => [
      ...acc,
      ...nextService.products.map(
        (p: any) => `${p.name}${p.version ? ' ' + p.version : ''}`
      )
    ],
    []
  );

  const vulns = vulnerabilities.raw.reduce(
    (acc, nextVuln) => [...acc, nextVuln.cve],
    []
  );

  const data = [];
  if (products.length > 0) {
    data.push({
      label: `Product${products.length > 1 ? 's' : ''}`,
      count: products.length,
      value: filterExpanded(
        [...Array.from(new Set(products))],
        Boolean(expanded.products),
        8
      ).join(', '),
      onExpand: () => toggleExpanded('products'),
      expansionText:
        products.length <= 8 ? null : expanded.products ? 'less' : 'more'
    });
  }
  if (vulns.length > 0) {
    data.push({
      label: vulns.length > 1 ? 'Findings' : 'Finding',
      count: vulns.length
    });
  }
  if (inner_hits?.webpage?.hits?.hits?.length! > 0) {
    const { hits } = inner_hits!.webpage!.hits!;
    data.push({
      label: `matching webpage${hits.length > 1 ? 's' : ''}`,
      count: hits.length,
      value: hits.map((e, idx) => (
        <React.Fragment key={idx}>
          <small>
            <strong>{e._source.webpage_url}</strong>
            <br />
            {e.highlight?.webpage_body?.map((body, idx) => (
              <React.Fragment key={idx}>
                <code
                  dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(body, { ALLOWED_TAGS: ['em'] })
                  }}
                />
              </React.Fragment>
            ))}
          </small>
        </React.Fragment>
      ))
    });
  }

  return (
    <StyledButtonBase
      aria-label={`View domain details for ${name.raw}`}
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        width="100%"
      >
        <Typography
          variant="h5"
          sx={{ color: '#07648D', fontWeight: 400, wordBreak: 'break-all' }}
        >
          {name.raw}
        </Typography>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption" sx={{ color: '#4e4e4e' }}>
            Last Seen
          </Typography>
          <Typography variant="body2" sx={{ color: '#3D4551' }}>
            {last_seen} ago
          </Typography>
        </Box>
      </Box>
      {ip.raw && (
        <Box display="flex" justifyContent="space-between" mt={2}>
          <Box>
            <Typography variant="caption" sx={{ color: '#4e4e4e' }}>
              IP
            </Typography>
            <Typography variant="body2" sx={{ color: '#3D4551' }}>
              {ip.raw}
            </Typography>
          </Box>
          {ports.length > 0 && (
            <Box textAlign="right">
              <Typography variant="caption" sx={{ color: '#4e4e4e' }}>
                <Typography
                  component="span"
                  sx={{ color: 'error.light', fontWeight: 'bold' }}
                >
                  {ports.length}
                </Typography>
                {` Port${ports.length > 1 ? 's' : ''}`}
              </Typography>
              <Typography variant="body2" sx={{ color: '#3D4551' }}>
                {ports.join(', ')}
              </Typography>
            </Box>
          )}
        </Box>
      )}
      {data.map(({ label, value, count, onExpand, expansionText }) => (
        <Box key={label} mt={2}>
          <Typography variant="caption" sx={{ color: '#4e4e4e' }}>
            {count !== undefined && (
              <Typography
                component="span"
                sx={{ color: 'error.light', fontWeight: 'bold' }}
              >
                {count}{' '}
              </Typography>
            )}
            {label}
          </Typography>
          <Typography variant="body2" sx={{ color: '#3D4551' }}>
            {value}
            {expansionText && (
              <Box
                sx={{
                  ml: 1,
                  px: 0,
                  minWidth: 'auto',
                  color: 'secondary.main',
                  textTransform: 'none'
                }}
              >
                {expansionText}
              </Box>
            )}
          </Typography>
        </Box>
      ))}
    </StyledButtonBase>
  );
};
