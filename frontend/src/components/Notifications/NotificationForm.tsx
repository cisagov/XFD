import React from 'react';
import Button from '@mui/material/Button';
import CardActions from '@mui/material/CardActions';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

interface NotificationFormProps {
  formValues: {
    maintenance_type: string;
    start_datetime: string;
    end_datetime: string;
    message: string;
    status: string;
  };
  formErrors: {
    maintenance_type: boolean;
    message: boolean;
    start_datetime: boolean;
    end_datetime: boolean;
    dateMessage: string;
  };
  checked: boolean;
  disabled?: boolean;
  onSwitchChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onCancel: () => void;
  onSubmit: () => void;
  isEdit?: boolean;
  setFormValues: React.Dispatch<React.SetStateAction<any>>;
  setFormDisabled: React.Dispatch<React.SetStateAction<boolean>>;
}

const NotificationForm: React.FC<NotificationFormProps> = ({
  formValues,
  formErrors,
  checked,
  disabled,
  onSwitchChange,
  onCancel,
  onSubmit,
  isEdit = false,
  setFormValues,
  setFormDisabled
}) => {
  // Matches main file logic for handleChange
  const handleChange = (event: any) => {
    setFormValues((values: any) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
    setFormDisabled(false);
  };

  return (
    <Grid container spacing={1}>
      <Grid size={{ xs: 12 }}>
        <Typography variant="body1" pb={1}>
          Maintenance Type
        </Typography>
        <Select
          displayEmpty
          size="small"
          id="maintenance_type"
          value={formValues.maintenance_type}
          name="maintenance_type"
          onChange={handleChange}
          fullWidth
          renderValue={
            formValues.maintenance_type !== ''
              ? undefined
              : () => (
                  <Typography color="#bdbdbd">
                    Select a Maintenance Type
                  </Typography>
                )
          }
          error={formErrors.maintenance_type}
        >
          <MenuItem value="minor">
            Minor maintenance: Login is available to all users.
          </MenuItem>
          <MenuItem value="major">
            Major maintenance: Login is restricted to admins.
          </MenuItem>
        </Select>
        {formErrors.maintenance_type && (
          <Typography pl={2} variant="caption" color="error.main">
            Maintenance type is required
          </Typography>
        )}
      </Grid>
      <Grid size={{ xs: 12, md: 6 }}>
        <Typography variant="body1" pb={1} pt={2}>
          Start Date and Time
        </Typography>
        <TextField
          id="start_datetime"
          name="start_datetime"
          size="small"
          fullWidth
          type="datetime-local"
          onChange={handleChange}
          value={formValues.start_datetime}
          error={formErrors.start_datetime}
        />
      </Grid>
      <Grid size={{ xs: 12, md: 6 }}>
        <Typography variant="body1" pb={1} pt={2}>
          End Date and Time
        </Typography>
        <TextField
          id="end_datetime"
          name="end_datetime"
          size="small"
          fullWidth
          type="datetime-local"
          onChange={handleChange}
          value={formValues.end_datetime}
          error={formErrors.end_datetime}
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        {formErrors.dateMessage && (
          <Typography pl={2} variant="caption" color="error.main">
            {formErrors.dateMessage}
          </Typography>
        )}
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Typography variant="body2">
          * Dates should be entered in US Eastern Time.
        </Typography>
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Typography variant="body1" pt={2}>
          Maintenance Message
        </Typography>
        <TextField
          placeholder="Enter the Maintenance message to be displayed..."
          size="small"
          margin="dense"
          id="message"
          name="message"
          multiline
          variant="standard"
          rows={5}
          type="text"
          fullWidth
          value={formValues.message}
          onChange={handleChange}
          error={formErrors.message}
          helperText={formErrors.message && 'Message is required'}
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Typography variant="body1" pt={2}>
          Status
        </Typography>
        <Switch onChange={onSwitchChange} checked={checked} sx={{ ml: -1 }} />
        Active
        <Typography variant="body2">
          * Setting a notification to active will automatically replace the
          current active notification.
        </Typography>
      </Grid>
      <Grid size={{ xs: 12 }}>
        <CardActions>
          <Button variant="outlined" sx={{ mt: 2 }} onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="contained"
            sx={{ mt: 2, ml: 2 }}
            onClick={onSubmit}
            disabled={disabled}
          >
            {isEdit ? 'Update' : 'Submit'}
          </Button>
        </CardActions>
      </Grid>
    </Grid>
  );
};

export default NotificationForm;
