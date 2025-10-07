import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardActions,
  IconButton,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
  Alert
} from '@mui/material';
import Grid from '@mui/material/Grid';
import { SelectChangeEvent } from '@mui/material/Select';
import {
  CheckCircleOutline,
  Delete,
  Edit,
  InfoOutlined,
  UploadFile as UploadFileIcon,
  Download as DownloadIcon
} from '@mui/icons-material';
import {
  DataGrid,
  gridClasses,
  GridColDef,
  GridRenderCellParams
} from '@mui/x-data-grid';
import InfoDialog from 'components/Dialog/InfoDialog';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';

const SECTORS = [
  'Energy',
  'Finance',
  'Healthcare',
  'Transportation',
  'Water',
  'Government'
];

const ACTIVE_REPORTS_KEY = 'activeReports';
const ARCHIVED_REPORTS_KEY = 'archivedReports';

function saveReportsToStorage(
  active: SectorReportFile[],
  archived: SectorReportFile[]
) {
  localStorage.setItem(ACTIVE_REPORTS_KEY, JSON.stringify(active));
  localStorage.setItem(ARCHIVED_REPORTS_KEY, JSON.stringify(archived));
}

function loadReportsFromStorage() {
  const active = JSON.parse(localStorage.getItem(ACTIVE_REPORTS_KEY) || '[]');
  const archived = JSON.parse(
    localStorage.getItem(ARCHIVED_REPORTS_KEY) || '[]'
  );
  return { active, archived };
}

interface SectorReportFile {
  id?: string;
  filename: string;
  sector: string;
  uploaded_by: string;
  uploaded_at: string;
  status: 'active' | 'archived';
  file?: File;
  fileUrl?: string;
}

const initialReportValues: SectorReportFile = {
  filename: '',
  sector: '',
  uploaded_by: '',
  uploaded_at: '',
  status: 'active'
};

export const SectorReports: React.FC = () => {
  const [activeReports, setActiveReports] = useState<SectorReportFile[]>(
    () => loadReportsFromStorage().active
  );
  const [archivedReports, setArchivedReports] = useState<SectorReportFile[]>(
    () => loadReportsFromStorage().archived
  );
  const [formValues, setFormValues] =
    useState<SectorReportFile>(initialReportValues);
  const [addBtnToggle, setAddBtnToggle] = useState(false);
  const [formDialogToggle, setFormDialogToggle] = useState(false);
  const [infoDialogToggle, setInfoDialogToggle] = useState(false);
  const [deleteDialogToggle, setDeleteDialogToggle] = useState(false);
  const [rowToDelete, setRowToDelete] =
    useState<SectorReportFile>(initialReportValues);
  const [formDisabled, setFormDisabled] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [infoDialogValues, setInfoDialogValues] = useState({
    icon: <CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />,
    title: 'Success',
    content: 'The report was updated successfully.'
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const tableStyling = {
    [`& .${gridClasses.cell}`]: { py: 1 },
    minHeight: { xs: '250px', md: 'unset' }
  };

  // Fetch reports from backend
  const fetchReports = async () => {
    try {
      const res = await fetch('/api/sector-reports');
      if (!res.ok) throw new Error('Failed to fetch reports');
      const data = await res.json();
      const active = data.files.filter(
        (r: SectorReportFile) => r.status === 'active'
      );
      const archived = data.files.filter(
        (r: SectorReportFile) => r.status === 'archived'
      );
      setActiveReports(active);
      setArchivedReports(archived);
    } catch (e: any) {
      setError(e.message || 'Error fetching reports');
    }
  };

  useEffect(() => {
    saveReportsToStorage(activeReports, archivedReports);
  }, [activeReports, archivedReports]);

  useEffect(() => {
    fetchReports();
  }, []);

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setFormValues((prev) => ({
        ...prev,
        filename: files[0].name,
        file: files[0]
      }));
      setFormDisabled(false);
    }
  };

  // Handle sector selection
  const handleSectorChange = (event: SelectChangeEvent<string>) => {
    setFormValues((prev) => ({
      ...prev,
      sector: event.target.value as string
    }));
    setFormDisabled(false);
  };

  // Handle upload
  const handleUpload = () => {
    if (!formValues.file || !formValues.sector) {
      setError('Please select a file and sector.');
      return;
    }
    setError(null);

    // Create a URL for the PDF file
    const fileUrl = URL.createObjectURL(formValues.file);

    const newReport: SectorReportFile = {
      ...formValues,
      id: Math.random().toString(36).substr(2, 9),
      uploaded_by: 'Mock User',
      uploaded_at: new Date().toISOString(),
      status: 'active',
      filename: formValues.file.name,
      file: formValues.file,
      fileUrl // Add this property for download/view
    };

    setActiveReports((prev) => [...prev, newReport]);
    setAddBtnToggle(false);
    setFormValues(initialReportValues);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Handle download
  const handleDownload = async (filename: string) => {
    try {
      const res = await fetch(
        `/api/sector-reports/download/${encodeURIComponent(filename)}`
      );
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || 'Error downloading file');
    }
  };

  // Handle delete
  const handleDelete = async () => {
    try {
      const res = await fetch(
        `/api/sector-reports/delete/${encodeURIComponent(rowToDelete.filename)}`,
        {
          method: 'DELETE'
        }
      );
      if (!res.ok) throw new Error('Delete failed');
      fetchReports();
      setDeleteDialogToggle(false);
      setInfoDialogValues({
        icon: <CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />,
        title: 'Success',
        content: 'The report was deleted successfully.'
      });
      setInfoDialogToggle(true);
    } catch (e: any) {
      setError(e.message || 'Error deleting file');
    }
  };

  const isGlobalAdmin = true;

  const handleArchive = (report: SectorReportFile) => {
    setActiveReports((prev) => prev.filter((r) => r.id !== report.id));
    setArchivedReports((prev) => [...prev, { ...report, status: 'archived' }]);
  };

  // Update columns for activeReports to include Archive button
  const activeColumns: GridColDef[] = [
    { field: 'filename', headerName: 'File Name', flex: 2, sortable: true },
    { field: 'sector', headerName: 'Sector', flex: 1, sortable: true },
    {
      field: 'uploaded_by',
      headerName: 'Uploaded By',
      flex: 1,
      sortable: true
    },
    {
      field: 'uploaded_at',
      headerName: 'Uploaded At',
      flex: 1,
      sortable: true,
      renderCell: (params: GridRenderCellParams) =>
        new Date(params.value as string).toLocaleString()
    },
    {
      field: 'download',
      headerName: 'Download',
      flex: 0.5,
      sortable: false,
      renderCell: (params: GridRenderCellParams) =>
        params.row.fileUrl ? (
          <IconButton
            color="primary"
            aria-label="download"
            href={params.row.fileUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <DownloadIcon />
          </IconButton>
        ) : null
    },
    ...(isGlobalAdmin
      ? [
          {
            field: 'archive',
            headerName: 'Archive',
            flex: 0.5,
            sortable: false,
            renderCell: (params: GridRenderCellParams) => (
              <IconButton
                color="secondary"
                aria-label="archive"
                onClick={() => handleArchive(params.row)}
              >
                <Edit />
              </IconButton>
            )
          },
          {
            field: 'delete',
            headerName: 'Delete',
            flex: 0.5,
            sortable: false,
            renderCell: (params: GridRenderCellParams) => (
              <IconButton
                color="primary"
                aria-label="delete"
                onClick={() => {
                  setRowToDelete(params.row);
                  setDeleteDialogToggle(true);
                }}
              >
                <Delete />
              </IconButton>
            )
          }
        ]
      : [])
  ];

  // Add report card
  const createReportCard = (
    <Grid container justifyContent="center">
      <Grid size={{ xs: 12, sm: 8 }}>
        <Card sx={{ p: 3 }}>
          <Typography variant="h6" pb={2} fontWeight="500">
            Upload Sector Report
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 8 }}>
              <Button
                variant="contained"
                startIcon={<UploadFileIcon />}
                onClick={() => fileInputRef.current?.click()}
              >
                Choose File
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <Typography variant="body2" mt={1}>
                {formValues.filename ? formValues.filename : 'No file selected'}
              </Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 8 }}>
              <Select
                displayEmpty
                size="small"
                id="sector"
                value={formValues.sector}
                name="sector"
                onChange={handleSectorChange}
                fullWidth
                renderValue={
                  formValues.sector !== ''
                    ? undefined
                    : () => (
                        <Typography color="#bdbdbd">Select a Sector</Typography>
                      )
                }
                error={!formValues.sector}
              >
                {SECTORS.map((sector) => (
                  <MenuItem key={sector} value={sector}>
                    {sector}
                  </MenuItem>
                ))}
              </Select>
            </Grid>
          </Grid>
          <CardActions>
            <Button
              variant="outlined"
              sx={{ mt: 2 }}
              onClick={() => setAddBtnToggle(false)}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              sx={{ mt: 2 }}
              onClick={handleUpload}
              disabled={!formValues.filename || !formValues.sector}
            >
              Submit
            </Button>
          </CardActions>
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </Card>
      </Grid>
    </Grid>
  );

  const confirmDeleteDialog = (
    <ConfirmDialog
      isOpen={deleteDialogToggle}
      onClose={() => setDeleteDialogToggle(false)}
      onConfirm={handleDelete}
      onCancel={() => setDeleteDialogToggle(false)}
      title={'Delete Report'}
      content={<>Are you sure you want to permanently remove this report?</>}
    />
  );

  return (
    <Box sx={{ px: { xs: 2, md: 6 }, py: 4 }}>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, sm: 8 }}>
          <Typography variant="h5" gutterBottom>
            Sector Reports
          </Typography>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Box display="flex" justifyContent="flex-end">
            <Button
              variant="contained"
              onClick={() => {
                setAddBtnToggle(!addBtnToggle);
                setFormValues(initialReportValues);
              }}
              disabled={addBtnToggle === true}
            >
              Add +
            </Button>
          </Box>
        </Grid>
        {addBtnToggle && <Grid size={{ xs: 12 }}>{createReportCard}</Grid>}
        <Grid size={{ xs: 12 }}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" pb={2} fontWeight="500">
              Active Sector Reports
            </Typography>
            {activeReports.length === 0 ? (
              <Alert
                icon={<InfoOutlined fontSize="inherit" />}
                severity="info"
                role="alert"
              >
                There are no active sector reports at this time.
              </Alert>
            ) : (
              <DataGrid
                rows={activeReports}
                columns={activeColumns}
                getRowHeight={() => 'auto'}
                sx={tableStyling}
                hideFooterPagination={true}
                disableRowSelectionOnClick
              />
            )}
          </Paper>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" pb={2} fontWeight="500">
              Archived Sector Reports
            </Typography>
            {archivedReports.length === 0 ? (
              <Alert
                icon={<InfoOutlined fontSize="inherit" />}
                severity="info"
                role="alert"
              >
                There are no archived sector reports at this time.
              </Alert>
            ) : (
              <DataGrid
                rows={archivedReports}
                columns={activeColumns}
                getRowHeight={() => 'auto'}
                sx={tableStyling}
                disableRowSelectionOnClick
              />
            )}
          </Paper>
        </Grid>
        {confirmDeleteDialog}
        <InfoDialog
          isOpen={infoDialogToggle}
          handleClick={() => setInfoDialogToggle(false)}
          icon={infoDialogValues.icon}
          title={<Typography variant="h4">{infoDialogValues.title}</Typography>}
          content={
            <Typography variant="body1">{infoDialogValues.content}</Typography>
          }
        />
      </Grid>
    </Box>
  );
};

export default SectorReports;
