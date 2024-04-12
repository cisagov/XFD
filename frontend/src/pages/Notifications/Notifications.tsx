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
import { format } from 'date-fns';
import { useAuthContext } from 'context';
import { initialNotificationValues, MaintenanceNotification } from 'types';

const formReadableDate = (date: string) => {
  const parsedDate = new Date(date);
  return format(parsedDate, 'yyyy-MM-dd HH:mm');
};

const humanReadableDate = (date: string) => {
  const parsedDate = new Date(date);
  return format(parsedDate, 'LLL dd, yyyy hh:mm a');
};

export const Notifications: React.FC = () => {
  const { apiGet } = useAuthContext();
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
  const formContents = (
    <>
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
      >
        <MenuItem value="minor">Minor: User login is still available</MenuItem>
        <MenuItem value="major">
          Major: Standard user login is not available
        </MenuItem>
      </Select>
      <Typography variant="body1" py={2}>
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
      />
      <Typography variant="body1" py={2}>
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
      />
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
      ></TextField>
      <Typography variant="body1" pt={2}>
        Status
      </Typography>
      <Switch onChange={onSwitchChange} checked={checked} sx={{ ml: -1 }} />
      Active
      <Typography variant="body2">
        * Only one notification can be active at a time. Setting a notification
        to active will automatically replace the current active one regardless
        of its duration.
      </Typography>
    </>
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
          <Button
            variant="contained"
            sx={{ mt: 2 }}
            onClick={() => console.log(formValues)}
          >
            Submit
          </Button>
        </CardActions>
      </Card>
    </Grid>
  );
  const editNotificationDialog = (
    <React.Fragment>
      <Button variant="outlined" onClick={() => setDialogToggle(true)}>
        Open alert dialog
      </Button>
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
    </React.Fragment>
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
            onClick={() => setAddBtnToggle(!addBtnToggle)}
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
