import React from 'react';
import {
  Button,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { Delete } from '@mui/icons-material';
import {
  DataGrid,
  gridClasses,
  GridColDef,
  GridRenderCellParams
} from '@mui/x-data-grid';

type InputFormValues = {
  id: string;
  maintenanceType: string;
  status: string;
  updatedAt: string;
  updatedBy: string;
  message: string;
};

const initialInputFormValues = {
  id: '',
  maintenanceType: '',
  status: '',
  updatedAt: '',
  updatedBy: '',
  message: ''
};

// Test data. Will be removed once update to backend is added.
const rows = [
  {
    id: '1',
    maintenanceType: 'minor',
    status: 'active',
    updatedAt: '12/12/2024',
    updatedBy: 'john.smith@test.com',
    message:
      'Crossfeed has scheduled minor server maintenance on 3/28/2024 from 8:00AM to 5:00PM. Access to your Crossfeed settings will be limited. We apologize for the inconvenience. For further information, please reach out to admin@crossfeed.com.'
  }
];

export const Notifications: React.FC = () => {
  const [values, setValues] = React.useState<InputFormValues>(
    initialInputFormValues
  );

  const columns: GridColDef[] = [
    { field: 'id' },
    {
      field: 'maintenanceType',
      headerName: 'Type',
      flex: 1,
      renderCell: (cellValues: any) => {
        console.log(cellValues.value);
        return <>{cellValues.value.toUpperCase()}</>;
      }
    },
    { field: 'updatedAt', headerName: 'Created Date', flex: 1 },
    { field: 'updatedBy', headerName: 'Admin Email', flex: 1 },
    { field: 'message', headerName: 'Message', flex: 3 },
    {
      field: 'delete',
      headerName: 'Delete',
      flex: 0.4,
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

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
  > = (e) => onChange(e.target.name, e.target.value);

  const onChange = (name: string, value: any) => {
    setValues((values) => ({
      ...values,
      [name]: value
    }));
  };

  const handleChange = (event: SelectChangeEvent) => {
    setValues((values) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
  };

  return (
    <Grid container>
      <Grid item xs={12} mb={3}>
        <Typography variant="h5">Maintenance Notifications</Typography>
      </Grid>
      <Grid item xs={12} mb={5}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Active Notifications
          </Typography>
          <DataGrid
            rows={rows}
            columns={columns}
            getRowHeight={() => 'auto'}
            sx={{
              [`& .${gridClasses.cell}`]: {
                py: 1
              }
            }}
          />
        </Paper>
      </Grid>
      <Grid item xs={12} sm={10} md={7}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Create a Notification
          </Typography>
          <Typography variant="body1" pb={1}>
            Maintenance Type
          </Typography>
          <Select
            displayEmpty
            size="small"
            id="maintenanceType"
            value={values.maintenanceType}
            name="maintenanceType"
            onChange={handleChange}
            fullWidth
            renderValue={
              values.maintenanceType !== ''
                ? undefined
                : () => (
                    <Typography color="#bdbdbd">
                      Select a Maintenance Type
                    </Typography>
                  )
            }
          >
            <MenuItem value="minor">
              Minor: User login is still available
            </MenuItem>
            <MenuItem value="major">
              Major: Standard user login is not available
            </MenuItem>
          </Select>
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
            value={values.message}
            onChange={onTextChange}
          ></TextField>
          <Button variant="contained" sx={{ mt: 2 }}>
            Submit
          </Button>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default Notifications;
