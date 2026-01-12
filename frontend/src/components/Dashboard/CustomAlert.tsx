import React from 'react';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Typography from '@mui/material/Typography';

interface CustomAlertProps {
  headerMsg?: string;
  bodyMsg?: React.ReactNode;
  isAlertActive?: boolean;
  hasOnClose?: boolean;
}

const CustomAlert: React.FC<CustomAlertProps> = ({
  headerMsg = 'No Data Found',
  bodyMsg = null,
  isAlertActive = true,
  hasOnClose = false
}) => {
  const [open, setOpen] = React.useState(true);
  const defaultMsg = (
    <>
      No data was found for this organization. Contact CyHy team through the
      Support menu.
    </>
  );
  if (!isAlertActive || !open) {
    return null;
  }
  return (
    <Alert
      severity="info"
      sx={{ width: '100%', py: 1 }}
      {...(hasOnClose && { onClose: () => setOpen(false) })}
    >
      <AlertTitle
        variant="largeBody"
        color="primary.darker"
        sx={{ fontWeight: 700, mb: 1 }}
      >
        {headerMsg}
      </AlertTitle>
      <Typography variant="body1" color="primary.darker" fontWeight={600}>
        {bodyMsg || defaultMsg}
      </Typography>
    </Alert>
  );
};

export default CustomAlert;
