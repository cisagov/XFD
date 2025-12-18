import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline';
import Delete from '@mui/icons-material/Delete';
import Edit from '@mui/icons-material/Edit';
import InfoOutlined from '@mui/icons-material/InfoOutlined';
import {
  gridClasses,
  GridColDef,
  GridRenderCellParams
} from '@mui/x-data-grid';
import { isAfter, parseISO } from 'date-fns';
import { formReadableDate, humanReadableDate, toEST } from 'utils/dateUtils';
import { useAuthContext } from 'context';
import { initialNotificationValues, MaintenanceNotification } from 'types';
import InfoDialog from 'components/Dialog/InfoDialog';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import NotificationForm from 'components/Notifications/NotificationForm';
import NotificationTable from 'components/Notifications/NotificationTable';
import { useSubmitForm } from '@/hooks/Notifications/useNotificationSubmit';
import { useNotificationApiCall } from '@/hooks/Notifications/useNotificationApiCall';
import { useNotificationAction } from '@/hooks/Notifications/useNotificationAction';
import { useDeleteNotification } from '@/hooks/Notifications/useDeleteNotification';
import { useFetchNotification } from '@/hooks/Notifications/useFetchNotification';

const dateValidator = (
  startDateStr: string,
  endDateStr: string
): [boolean, string] => {
  const start_date = parseISO(startDateStr);
  const end_date = parseISO(endDateStr);
  const currentDate = new Date();
  if (!isAfter(start_date, currentDate)) {
    return [true, 'Start date must be in the future.'];
  } else if (!isAfter(end_date, currentDate)) {
    return [true, 'End date must be in the future.'];
  } else if (!isAfter(end_date, start_date)) {
    return [true, 'Start date must come before the end date.'];
  }
  return [false, ''];
};

const initialFormErrorValues = {
  maintenance_type: false,
  message: false,
  start_datetime: false,
  end_datetime: false,
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
  const { apiDelete, apiGet, apiPost, user } = useAuthContext();
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

  const fetchNotifications = useFetchNotification(
    apiGet,
    setActiveNotification,
    setInactiveNotifications,
    initialNotificationValues
  );

  React.useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const columns: GridColDef[] = [
    {
      field: 'maintenance_type',
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
        const start_date = humanReadableDate(cellValues.row.start_datetime);
        const end_date = humanReadableDate(cellValues.row.end_datetime);
        return (
          <>
            {start_date} to
            <br /> {end_date}
          </>
        );
      }
    },
    { field: 'updated_by', headerName: 'Admin Email', flex: 2 },
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
              cellValues.row.start_datetime = formReadableDate(
                toEST(cellValues.row.start_datetime)
              );
              cellValues.row.end_datetime = formReadableDate(
                toEST(cellValues.row.end_datetime)
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

  const handleApiCall = useNotificationApiCall(
    setInfoDialogValues,
    setInfoDialogToggle
  );

  const handleNotificationAction = useNotificationAction({
    apiPost,
    apiDelete,
    handleApiCall
  });

  const deleteNotification = useDeleteNotification({
    rowToDelete,
    setActiveNotification,
    setInactiveNotifications,
    initialNotificationValues,
    inactiveNotifications,
    handleNotificationAction
  });

  const submitForm = useSubmitForm({
    formValues,
    setFormErrors,
    setActiveNotification,
    setInactiveNotifications,
    initialNotificationValues,
    activeNotification,
    inactiveNotifications,
    user: user ?? {},
    handleNotificationAction,
    dateValidator
  });

  const confirmEditNotificationDialog = (
    <ConfirmDialog
      isOpen={formDialogToggle}
      onClose={() => setFormDialogToggle(false)}
      onConfirm={() => submitForm('update')}
      onCancel={handleResetForm}
      title={'Update Notification'}
      content={
        <NotificationForm
          formValues={formValues}
          formErrors={formErrors}
          checked={checked}
          disabled={formDisabled}
          onSwitchChange={onSwitchChange}
          onCancel={handleResetForm}
          onSubmit={() => submitForm('update')}
          isEdit={true}
          setFormValues={setFormValues}
          setFormDisabled={setFormDisabled}
        />
      }
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
      <Grid size={{ xs: 12, sm: 8 }}>
        <Typography variant="h5">Maintenance Notifications</Typography>
      </Grid>
      <Grid size={{ xs: 12, sm: 4 }}>
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
      {addBtnToggle && (
        <Grid size={{ xs: 12, sm: 10, md: 8, lg: 7 }} mt={3}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" pb={2} fontWeight="500">
              Create a Notification
            </Typography>
            <NotificationForm
              formValues={formValues}
              formErrors={formErrors}
              checked={checked}
              disabled={formDisabled}
              onSwitchChange={onSwitchChange}
              onCancel={handleResetForm}
              onSubmit={() => submitForm('post')}
              isEdit={false}
              setFormValues={setFormValues}
              setFormDisabled={setFormDisabled}
            />
          </Card>
        </Grid>
      )}
      <Grid size={{ xs: 12 }} my={5}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Active Notification
          </Typography>
          {activeNotification.status === 'active' ? (
            <>
              <NotificationTable
                title="Active Notification"
                rows={[activeNotification]}
                columns={columns}
                tableStyling={tableStyling}
                hideFooterPagination={true}
              >
                <Typography variant="body2" mt={1}>
                  * Only one notification can be active at a time and be shown
                  on the login screen.
                  <br />* Only admins will be able to login during major
                  maintenance. Login is unaffected for minor maintenance.
                  <br />* Dates are shown in US Eastern Time.
                </Typography>
              </NotificationTable>
            </>
          ) : (
            <Alert
              icon={
                <InfoOutlined
                  fontSize="inherit"
                  role="img"
                  aria-hidden="false"
                  aria-label="Information Alert"
                />
              }
              severity="info"
              role="alert"
            >
              There is no active maintenance notification at this time. To make
              a notification active, add a new one or update an inactive one.
            </Alert>
          )}
        </Paper>
      </Grid>
      <Grid size={{ xs: 12 }} mb={5}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Inactive Notifications
          </Typography>
          {inactiveNotifications.length === 0 ? (
            <Alert
              icon={
                <InfoOutlined
                  fontSize="inherit"
                  role="img"
                  aria-hidden="false"
                  aria-label="Information Alert"
                />
              }
              severity="info"
              role="alert"
            >
              There are no inactive maintenance notifications at this time. The
              unused inactive notifications will be shown here.
            </Alert>
          ) : (
            <>
              <NotificationTable
                title="Inactive Notifications"
                rows={inactiveNotifications}
                columns={columns}
                tableStyling={tableStyling}
              >
                <Typography variant="body2" mt={1}>
                  * Dates are shown in US Eastern Time.
                </Typography>
              </NotificationTable>
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
