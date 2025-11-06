import React from 'react';
import { Grid, Chip, Typography } from '@mui/material';
import { PendingDomain, OrganizationTag } from 'types';

export interface ListInputProps {
  type: 'root_domains' | 'ip_blocks' | 'tags';
  label: string;
  organization: any;
  userType?: string;
  setOrganization: Function;
  setDialog: (dialog: any) => void;
  setInputValue: (val: string) => void;
  setIsSaveDisabled: (val: boolean) => void;
  chosenTags?: string[];
  setChosenTags?: (val: string[]) => void;
  localTags?: string[];
  setLocalTags?: (tags: string[]) => void;
  disableAddButton?: boolean;
  disableDelete?: boolean;
}

const ListInput: React.FC<ListInputProps> = ({
  type,
  label,
  organization,
  userType,
  setOrganization,
  setDialog,
  setInputValue,
  setIsSaveDisabled,
  chosenTags,
  setChosenTags,
  localTags,
  setLocalTags,
  disableAddButton = false,
  disableDelete = false
}) => {
  if (!organization) return null;

  const values: (string | OrganizationTag)[] = organization[type];

  const handleDelete = (index: number) => {
    const updated = [...values];
    updated.splice(index, 1);
    setOrganization({ ...organization, [type]: updated });

    if (
      type === 'tags' &&
      chosenTags &&
      setChosenTags &&
      localTags &&
      setLocalTags
    ) {
      const updatedTags = [...chosenTags];
      updatedTags.splice(index, 1);
      setChosenTags(updatedTags);
      setLocalTags(updatedTags);
    }

    setIsSaveDisabled(false);
  };

  return (
    <Grid container spacing={1}>
      <Grid my={1} size={{ xs: 12, sm: 3, lg: 2 }}>
        <Typography variant="body2">{label}</Typography>
      </Grid>
      {values.map((value, index) => (
        <Grid key={index}>
          {disableDelete ? (
            <Chip
              color="primary"
              label={typeof value === 'string' ? value : value.name}
              disabled={userType === 'globalView'}
            />
          ) : (
            <Chip
              color="primary"
              label={typeof value === 'string' ? value : value.name}
              onDelete={() => handleDelete(index)}
              disabled={userType === 'globalView'}
            />
          )}
        </Grid>
      ))}
      {type === 'root_domains' &&
        organization.pending_domains?.map(
          (domain: PendingDomain, index: number) => (
            <Grid key={index}>
              {disableDelete ? (
                <Chip
                  sx={{ backgroundColor: '#C4C4C4' }}
                  label={`${domain.name} (verification pending)`}
                  onClick={() => {
                    setInputValue(domain.name);
                    setDialog({ open: true, type, label, stage: 1 });
                  }}
                  disabled={userType === 'globalView'}
                />
              ) : (
                <Chip
                  sx={{ backgroundColor: '#C4C4C4' }}
                  label={`${domain.name} (verification pending)`}
                  onDelete={() => {
                    const updated = organization.pending_domains.filter(
                      (_: any, i: number) => i !== index
                    );
                    setOrganization({
                      ...organization,
                      pending_domains: updated
                    });
                  }}
                  onClick={() => {
                    setInputValue(domain.name);
                    setDialog({ open: true, type, label, stage: 1 });
                  }}
                  disabled={userType === 'globalView'}
                />
              )}
            </Grid>
          )
        )}
      {(type === 'root_domains' || userType === 'globalAdmin') &&
        !disableAddButton && (
          <Grid>
            <Chip
              label="ADD"
              variant="outlined"
              color="secondary"
              onClick={() => setDialog({ open: true, type, label, stage: 0 })}
              disabled={userType === 'globalView'}
            />
          </Grid>
        )}
    </Grid>
  );
};

export default ListInput;
