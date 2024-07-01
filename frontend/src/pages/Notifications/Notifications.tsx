import React from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
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
import {
  CheckCircleOutline,
  Delete,
  Edit,
  ErrorOutline,
  InfoOutlined
} from '@mui/icons-material';
import {
  DataGrid,
  gridClasses,
  GridColDef,
  GridRenderCellParams
} from '@mui/x-data-grid';
import { isAfter, parseISO } from 'date-fns';
import {
  formReadableDate,
  humanReadableDate,
  toEST,
  toUTC
} from 'utils/dateUtils';
import { useAuthContext } from 'context';
import { initialNotificationValues, MaintenanceNotification } from 'types';
import InfoDialog from 'components/Dialog/InfoDialog';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';

const dateValidator = (
  startDateStr: string,
  endDateStr: string
): [boolean, string] => {
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
  message: false,
  startDatetime: false,
  endDatetime: false,
  dateMessage: ''
};

const initialInfoDialogValues = {
  icon: (
    <CheckCircleOutline
      color="success"
      aria-label="a success icon that displays an outlined circle with a checkmark in the center"
      sx={{ fontSize: '80px' }}
    />
  ),
  title: 'Success',
  content: 'The notification was updated successfully.'
};

export const Notifications: React.FC = () => {
  const { apiDelete, apiGet, apiPost, apiPut, user } = useAuthContext();
  const [formValues, setFormValues] = React.useState<MaintenanceNotification>(
    initialNotificationValues
  );
  const [activeNotification, setActiveNotification] =
    React.useState<MaintenanceNotification>(initialNotificationValues);
  const [inactiveNotifications, setInactiveNotifications] = React.useState<
    MaintenanceNotification[]
  >([]);
  const [addBtnToggle, setAddBtnToggle] = React.useState(false);
  const [formDialogToggle, setFormDialogToggle] = React.useState(false);
  const [infoDialogToggle, setInfoDialogToggle] = React.useState(false);
  const [deleteDialogToggle, setDeleteDialogToggle] = React.useState(false);
  const [rowToDelete, setRowToDelete] = React.useState(
    initialNotificationValues
  );
  const [checked, setChecked] = React.useState(false);
  const [formErrors, setFormErrors] = React.useState(initialFormErrorValues);
  const [infoDialogValues, setInfoDialogValues] = React.useState(
    initialInfoDialogValues
  );
  const [formDisabled, setFormDisabled] = React.useState(true);
  const tableStyling = {
    [`& .${gridClasses.cell}`]: { py: 1 },
    minHeight: { xs: '250px', md: 'unset' }
  };

  const fetchNotifications = React.useCallback(async () => {
    try {
      const rows = await apiGet('/notifications');
      let activeRow;
      const inactiveRows: MaintenanceNotification[] = [];
      for (const row of rows) {
        if (row.status === 'active') {
          activeRow = { ...row };
        } else {
          inactiveRows.push({ ...row });
        }
      }
      if (activeRow) {
        setActiveNotification(activeRow);
      } else {
        setActiveNotification(initialNotificationValues);
      }
      if (inactiveRows.length > 0) {
        setInactiveNotifications(inactiveRows);
      }
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
            aria-label="an icon button that displays a pencil and sends you to edit the selected table entry when clicked"
            onClick={() => {
              cellValues.row.startDatetime = formReadableDate(
                toEST(cellValues.row.startDatetime)
              );
              cellValues.row.endDatetime = formReadableDate(
                toEST(cellValues.row.endDatetime)
              );
              if (cellValues.row.status === 'active') {
                setChecked(true);
              } else {
                setChecked(false);
              }
              setFormValues(cellValues.row);
              setFormDialogToggle(true);
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
            aria-label="an icon button that displays a trash can and sends you to delete the selected table entry when clicked"
            onClick={() => {
              setDeleteDialogToggle(true);
              setRowToDelete(cellValues.row);
            }}
          >
            <Delete />
          </IconButton>
        );
      }
    }
  ];

  const handleResetForm = () => {
    setInfoDialogToggle(false);
    setFormDialogToggle(false);
    setDeleteDialogToggle(false);
    setAddBtnToggle(false);
    setFormValues(initialNotificationValues);
    setFormErrors(initialFormErrorValues);
    setRowToDelete(initialNotificationValues);
    setChecked(false);
    setFormDisabled(true);
    setTimeout(() => {
      setInfoDialogValues(initialInfoDialogValues);
    }, 500); // 0.5 second delay
  };

  const handleChange = (event: SelectChangeEvent | any) => {
    setFormValues((values) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
    setFormDisabled(false);
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
    setFormDisabled(false);
  };

  const handleApiCall = async (
    apiCall: () => Promise<MaintenanceNotification>,
    successMessage: string,
    errorMessage: string
  ) => {
    try {
      const notification = await apiCall();
      setInfoDialogValues((prevState) => ({
        ...prevState,
        content: successMessage
      }));
      setInfoDialogToggle(true);
      return notification;
    } catch (e: any) {
      console.error(e);
      setInfoDialogValues({
        icon: (
          <ErrorOutline
            color="error"
            aria-label="an error icon that displays an outlined circle with a x in the center"
            sx={{ fontSize: '80px' }}
          />
        ),
        title: 'Error',
        content: `${errorMessage} ${e.message}. Check the console log for more details.`
      });
      setInfoDialogToggle(true);
      throw e;
    }
  };

  const handleNotificationAction = async (
    body: MaintenanceNotification,
    apiType: string
  ) => {
    let notification;
    try {
      if (apiType === 'put') {
        notification = await handleApiCall(
          () => apiPut('/notifications/' + body.id, { body }),
          'The notification was successfully updated.',
          'The notification was not able to be updated.'
        );
      } else if (apiType === 'post') {
        notification = await handleApiCall(
          () => apiPost('/notifications/', { body }),
          'The creation of the new notification was successful.',
          'The creation of the new notification was unsuccessful.'
        );
      } else {
        notification = await handleApiCall(
          () => apiDelete('/notifications/' + body.id),
          'The deletion of the notification was successful.',
          'The deletion of the notification was unsuccessful.'
        );
      }
    } catch (error) {
      console.error('Error occurred during handleNotificationAction:', error);
      throw error;
    }
    return notification;
  };

  const deleteNotification = async () => {
    try {
      await handleNotificationAction(rowToDelete, 'delete');
      if (rowToDelete.status === 'active') {
        setActiveNotification(initialNotificationValues);
      } else {
        setInactiveNotifications(
          inactiveNotifications.filter((item) => item.id !== rowToDelete.id)
        );
      }
    } catch (error) {
      console.log('Error occurred during delete request:', error);
    }
  };

  const submitForm = async (apiType: string) => {
    const invalidDate = dateValidator(
      formValues.startDatetime,
      formValues.endDatetime
    );
    const body: MaintenanceNotification = {
      id: formValues.id,
      maintenanceType: formValues.maintenanceType,
      status: formValues.status,
      updatedBy: user?.email || '',
      message: formValues.message,
      startDatetime: toUTC(formValues.startDatetime),
      endDatetime: toUTC(formValues.endDatetime)
    };
    const newFormErrors = {
      maintenanceType: !formValues.maintenanceType,
      message: !formValues.message,
      startDatetime: invalidDate[0],
      endDatetime: invalidDate[0],
      dateMessage: invalidDate[1]
    };
    setFormErrors(newFormErrors);
    if (Object.values(newFormErrors).some((error) => error)) {
      return;
    }
    if (body.status !== 'active') {
      body.status = 'inactive';
    }
    if (apiType === 'put') {
      try {
        const notification = await handleNotificationAction(body, apiType);
        // former active notification
        if (body.id === activeNotification.id) {
          if (notification.status === 'active') {
            setActiveNotification({ ...notification });
          } else {
            setActiveNotification(initialNotificationValues);
            setInactiveNotifications([...inactiveNotifications, notification]);
          }
          // former inactive notification
        } else {
          if (body.status === 'active') {
            const updatedActiveNotification = {
              ...activeNotification,
              status: 'inactive'
            };
            if (updatedActiveNotification.id !== '1') {
              const formerActiveNotification = await handleNotificationAction(
                updatedActiveNotification,
                'put'
              );
              setInactiveNotifications((prevNotifications) => {
                const updatedNotifications = prevNotifications.filter(
                  (row) => row.id !== body.id
                );
                return [...updatedNotifications, formerActiveNotification];
              });
            } else {
              setInactiveNotifications(
                inactiveNotifications.filter((item) => item.id !== body.id)
              );
            }
            setActiveNotification(body);
          } else {
            setInactiveNotifications((prevInactiveNotifications) => {
              return prevInactiveNotifications.map((notification) => {
                if (notification.id === body.id) {
                  return body;
                } else {
                  return notification;
                }
              });
            });
          }
        }
      } catch (error) {
        console.error('Error occurred during put request:', error);
      }
    }
    if (apiType === 'post') {
      try {
        const notification = await handleNotificationAction(body, apiType);
        if (notification.status === 'active') {
          if (activeNotification.status === 'active') {
            const updatedActiveNotification = {
              ...activeNotification,
              status: 'inactive'
            };
            await handleNotificationAction(updatedActiveNotification, 'put');
            setInactiveNotifications([
              ...inactiveNotifications,
              updatedActiveNotification
            ]);
          }
          setActiveNotification(notification);
        } else {
          setInactiveNotifications([...inactiveNotifications, notification]);
        }
      } catch (error) {
        console.error('Error occurred during post request:', error);
      }
    }
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
            Minor maintenance: Login is available to all users.
          </MenuItem>
          <MenuItem value="major">
            Major maintenance: Login is restricted to admins.
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
          error={formErrors.startDatetime}
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
          error={formErrors.endDatetime}
        />
      </Grid>
      <Grid item xs={12}>
        {formErrors.dateMessage && (
          <Typography pl={2} variant="caption" color="error.main">
            {formErrors.dateMessage}
          </Typography>
        )}
      </Grid>
      <Grid item xs={12}>
        <Typography variant="body2">
          * Dates should be entered in US Eastern Time.
        </Typography>
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
          * Setting a notification to active will automatically replace the
          current active notification.
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
          <Button
            variant="contained"
            sx={{ mt: 2 }}
            onClick={() => submitForm('post')}
          >
            Submit
          </Button>
        </CardActions>
      </Card>
    </Grid>
  );

  const confirmEditNotificationDialog = (
    <ConfirmDialog
      isOpen={formDialogToggle}
      onClose={() => setFormDialogToggle(false)}
      onConfirm={() => submitForm('put')}
      onCancel={handleResetForm}
      title={'Update Notification'}
      content={formContents}
      disabled={formDisabled}
    />
  );

  const confirmDeleteNotificationDialog = (
    <ConfirmDialog
      isOpen={deleteDialogToggle}
      onClose={() => setDeleteDialogToggle(false)}
      onConfirm={deleteNotification}
      onCancel={handleResetForm}
      title={'Delete Notification'}
      content={
        <>Are you sure you want to permanently remove this notification?</>
      }
    />
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
          {activeNotification.status === 'active' ? (
            <>
              <DataGrid
                rows={[activeNotification]}
                columns={columns}
                getRowHeight={() => 'auto'}
                sx={tableStyling}
                hideFooterPagination={true}
                disableRowSelectionOnClick
              />
              <Typography variant="body2" mt={1}>
                * Only one notification can be active at a time and be shown on
                the login screen.
                <br />* Only admins will be able to login during major
                maintenance. Login is unaffected for minor maintenance.
                <br />* Dates are shown in US Eastern Time.
              </Typography>
            </>
          ) : (
            <Alert
              icon={
                <InfoOutlined
                  fontSize="inherit"
                  aria-label="an information alert icon that displays an outlined circle with the letter i in the center"
                />
              }
              severity="info"
              role="alert"
              aria-label="an information alert banner to display an information alert icon and text"
            >
              There is no active maintenance notification at this time. To make
              a notification active, add a new one or update an inactive one.
            </Alert>
          )}
        </Paper>
      </Grid>
      <Grid item xs={12} mb={5}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Inactive Notifications
          </Typography>
          {inactiveNotifications.length === 0 ? (
            <Alert
              icon={
                <InfoOutlined
                  fontSize="inherit"
                  aria-label="an information alert icon that displays an outlined circle with the letter i in the center"
                />
              }
              severity="info"
              role="alert"
              aria-label="an information alert banner to display an information alert icon and text"
            >
              There are no inactive maintenance notifications at this time. The
              unused inactive notifications will be shown here.
            </Alert>
          ) : (
            <>
              <DataGrid
                rows={inactiveNotifications}
                columns={columns}
                getRowHeight={() => 'auto'}
                sx={tableStyling}
                disableRowSelectionOnClick
              />
              <Typography variant="body2" mt={1}>
                * Dates are shown in US Eastern Time.
              </Typography>
            </>
          )}
        </Paper>
      </Grid>
      {confirmEditNotificationDialog}
      {confirmDeleteNotificationDialog}
      <InfoDialog
        isOpen={infoDialogToggle}
        handleClick={() => handleResetForm()}
        icon={infoDialogValues.icon}
        title={<Typography variant="h4">{infoDialogValues.title}</Typography>}
        content={
          <Typography variant="body1">{infoDialogValues.content}</Typography>
        }
      />
    </Grid>
  );
};

export default Notifications;
