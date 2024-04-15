import React from 'react';
import {
  Box,
  Button,
  Card,
  CardActions,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Switch,
  TextField,
  Typography
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { Delete, Edit } from '@mui/icons-material';
import {
  DataGrid,
  gridClasses,
  GridColDef,
  GridRenderCellParams
} from '@mui/x-data-grid';
import { format, isAfter, parseISO } from 'date-fns';
import { useAuthContext } from 'context';
import { initialNotificationValues, MaintenanceNotification } from 'types';

type DateValidatorResult = [boolean, string];

const formReadableDate = (date: string) => {
  const parsedDate = new Date(date);
  return format(parsedDate, 'yyyy-MM-dd HH:mm');
};

const humanReadableDate = (date: string) => {
  const parsedDate = new Date(date);
  return format(parsedDate, 'LLL dd, yyyy hh:mm a');
};

const dateValidator = (
  startDateStr: string,
  endDateStr: string
): DateValidatorResult => {
  const startDate = parseISO(startDateStr);
  const endDate = parseISO(endDateStr);
  const currentDate = new Date();
  if (!isAfter(startDate, currentDate)) {
    return [true, 'Start date must be in the future.'];
  } else if (!isAfter(endDate, currentDate)) {
    return [true, 'End date must be in the future.'];
  } else if (!isAfter(endDate, startDate)) {
    return [true, 'Start date must come before the end date.'];
  }
  return [false, ''];
};

const initialFormErrorValues = {
  maintenanceType: false,
  message: false
};

export const Notifications: React.FC = () => {
  const { apiGet, user } = useAuthContext();
  const [formValues, setFormValues] = React.useState<MaintenanceNotification>(
    initialNotificationValues
  );
  const [activeNotification, setActiveNotification] = React.useState(
    initialNotificationValues
  );
  const [inactiveNotifications, setInactiveNotifications] = React.useState([
    initialNotificationValues
  ]);
  const [addBtnToggle, setAddBtnToggle] = React.useState(false);
  const [dialogToggle, setDialogToggle] = React.useState(false);
  const [checked, setChecked] = React.useState(false);
  const [isDateInvalid, setIsDateInvalid] = React.useState<DateValidatorResult>(
    [false, '']
  );
  const [formErrors, setFormErrors] = React.useState(initialFormErrorValues);

  const tableStyling = {
    [`& .${gridClasses.cell}`]: { py: 1 },
    minHeight: { xs: '250px', md: 'unset' }
  };

  const fetchNotifications = React.useCallback(async () => {
    try {
      const rows = await apiGet('/notifications');
      const activeRow = rows.find(
        (row: { status: string }) => row.status === 'active'
      );
      const inactiveRows = rows.filter(
        (row: MaintenanceNotification) => row.status !== 'active'
      );
      setActiveNotification(activeRow);
      setInactiveNotifications(inactiveRows);
    } catch (e: any) {
      console.log(e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiGet]);

  React.useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns: GridColDef[] = [
    {
      field: 'maintenanceType',
      headerName: 'Type',
      flex: 0.5,
      renderCell: (cellValues: any) => {
        return <>{cellValues.value.toUpperCase()}</>;
      }
    },
    {
      field: 'timeFrame',
      headerName: 'Time Frame',
      flex: 1.5,
      minWidth: 180,
      renderCell: (cellValues: GridRenderCellParams) => {
        const startDate = humanReadableDate(cellValues.row.startDatetime);
        const endDate = humanReadableDate(cellValues.row.endDatetime);
        return (
          <>
            {startDate} to
            <br /> {endDate}
          </>
        );
      }
    },
    { field: 'updatedBy', headerName: 'Admin Email', flex: 2 },
    { field: 'message', headerName: 'Message', flex: 3, minWidth: 200 },
    {
      field: 'update',
      headerName: 'Update',
      flex: 0.4,
      minWidth: 50,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            color="primary"
            onClick={() => {
              cellValues.row.startDatetime = formReadableDate(
                cellValues.row.startDatetime
              );
              cellValues.row.endDatetime = formReadableDate(
                cellValues.row.endDatetime
              );
              if (cellValues.row.status === 'active') {
                setChecked(true);
              } else {
                setChecked(false);
              }
              setFormValues(cellValues.row);
              setDialogToggle(true);
            }}
          >
            <Edit />
          </IconButton>
        );
      }
    },
    {
      field: 'delete',
      headerName: 'Delete',
      flex: 0.4,
      minWidth: 50,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            color="primary"
            onClick={() => {
              console.log(cellValues.row);
            }}
          >
            <Delete />
          </IconButton>
        );
      }
    }
  ];

  const handleResetForm = () => {
    setDialogToggle(false);
    setAddBtnToggle(false);
    setFormValues(initialNotificationValues);
    setFormErrors(initialFormErrorValues);
    setIsDateInvalid([false, '']);
  };

  const handleChange = (event: SelectChangeEvent | any) => {
    setFormValues((values) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
  };

  const onSwitchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setChecked(event.target.checked);
    if (event.target.checked) {
      setFormValues((values) => ({
        ...values,
        status: 'active'
      }));
    } else {
      setFormValues((values) => ({
        ...values,
        status: 'inactive'
      }));
    }
  };

  const submitForm = () => {
    setIsDateInvalid(
      dateValidator(formValues.startDatetime, formValues.endDatetime)
    );
    const body = {
      id: formValues.id,
      maintenanceType: formValues.maintenanceType,
      status: formValues.status,
      updatedBy: user?.email,
      message: formValues.message,
      startDatetime: formValues.startDatetime,
      endDatetime: formValues.endDatetime
    };
    const { maintenanceType, message } = formValues;
    const newFormErrors = {
      maintenanceType: !maintenanceType,
      message: !message
    };
    setFormErrors(newFormErrors);
    if (Object.values(newFormErrors).some((error) => error)) {
      return;
    }
    // if making a POST and not PUT, remove id because it will be autogenerated
    // delete body.id;
    console.log(body);
  };
  const formContents = (
    <Grid container spacing={1}>
      <Grid item xs={12}>
        <Typography variant="body1" pb={1}>
          Maintenance Type
        </Typography>
        <Select
          displayEmpty
          size="small"
          id="maintenanceType"
          value={formValues.maintenanceType}
          name="maintenanceType"
          onChange={handleChange}
          fullWidth
          renderValue={
            formValues.maintenanceType !== ''
              ? undefined
              : () => (
                  <Typography color="#bdbdbd">
                    Select a Maintenance Type
                  </Typography>
                )
          }
          error={formErrors.maintenanceType}
        >
          <MenuItem value="minor">
            Minor: User login is still available
          </MenuItem>
          <MenuItem value="major">
            Major: Standard user login is not available
          </MenuItem>
        </Select>
        {formErrors.maintenanceType && (
          <Typography pl={2} variant="caption" color="error.main">
            Maintenance type is required
          </Typography>
        )}
      </Grid>
      <Grid item sm={12} md={6}>
        <Typography variant="body1" pb={1} pt={2}>
          Start Date and Time
        </Typography>
        <TextField
          id="startDatetime"
          name="startDatetime"
          size="small"
          fullWidth
          type="datetime-local"
          onChange={handleChange}
          value={formValues.startDatetime}
          error={isDateInvalid[0]}
        />
      </Grid>
      <Grid item sm={12} md={6}>
        <Typography variant="body1" pb={1} pt={2}>
          End Date and Time
        </Typography>
        <TextField
          id="endDatetime"
          name="endDatetime"
          size="small"
          fullWidth
          type="datetime-local"
          onChange={handleChange}
          defaultValue={formValues.endDatetime}
          error={isDateInvalid[0]}
        />
      </Grid>
      <Grid item xs={12}>
        {isDateInvalid[0] && (
          <Typography pl={2} variant="caption" color="error.main">
            {isDateInvalid[1]}
          </Typography>
        )}
      </Grid>
      <Grid item xs={12}>
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
        ></TextField>
      </Grid>
      <Grid item xs={12}>
        <Typography variant="body1" pt={2}>
          Status
        </Typography>
        <Switch onChange={onSwitchChange} checked={checked} sx={{ ml: -1 }} />
        Active
        <Typography variant="body2">
          * Only one notification can be active at a time. Setting a
          notification to active will automatically replace the current active
          one regardless of its duration.
        </Typography>
      </Grid>
    </Grid>
  );
  const createNotificationCard = (
    <Grid item xs={12} sm={10} md={8} lg={7} mt={3}>
      <Card sx={{ p: 3 }}>
        <Typography variant="h6" pb={2} fontWeight="500">
          Create a Notification
        </Typography>
        {formContents}
        <CardActions>
          <Button variant="outlined" sx={{ mt: 2 }} onClick={handleResetForm}>
            Cancel
          </Button>
          <Button variant="contained" sx={{ mt: 2 }} onClick={submitForm}>
            Submit
          </Button>
        </CardActions>
      </Card>
    </Grid>
  );
  const editNotificationDialog = (
    <Dialog open={dialogToggle} onClose={() => setDialogToggle(false)}>
      <DialogTitle>Update Notification</DialogTitle>
      <DialogContent>{formContents}</DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={handleResetForm}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={() => setDialogToggle(false)}
          autoFocus
        >
          Submit
        </Button>
      </DialogActions>
    </Dialog>
  );
  return (
    <Grid container>
      <Grid item xs={12} sm={8}>
        <Typography variant="h5">Maintenance Notifications</Typography>
      </Grid>
      <Grid item xs={12} sm={4}>
        <Box display="flex" justifyContent="flex-end">
          <Button
            variant="contained"
            onClick={() => {
              setAddBtnToggle(!addBtnToggle);
              setFormValues(initialNotificationValues);
            }}
            disabled={addBtnToggle === true}
          >
            Add New +
          </Button>
        </Box>
      </Grid>
      {addBtnToggle && createNotificationCard}
      <Grid item xs={12} my={5}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Active Notification
          </Typography>
          <DataGrid
            rows={[activeNotification]}
            columns={columns}
            getRowHeight={() => 'auto'}
            sx={tableStyling}
            hideFooterPagination={true}
            disableRowSelectionOnClick
          />
        </Paper>
      </Grid>
      <Grid item xs={12} mb={5}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Inactive Notifications
          </Typography>
          <DataGrid
            rows={inactiveNotifications}
            columns={columns}
            getRowHeight={() => 'auto'}
            sx={tableStyling}
            disableRowSelectionOnClick
          />
        </Paper>
      </Grid>
      {editNotificationDialog}
    </Grid>
  );
};

export default Notifications;
