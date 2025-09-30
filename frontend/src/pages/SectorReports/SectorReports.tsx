import React, { useRef, useState, useEffect } from 'react';
import {
  Box,
  Button,
  Container,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  IconButton,
  CircularProgress,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import { SelectChangeEvent } from '@mui/material/Select';

//Example Sectors, should be fetched from backend when page is implemented
const SECTORS = [
  'Energy',
  'Finance',
  'Healthcare',
  'Transportation',
  'Water',
  'Government'
];

interface SectorReportFile {
  filename: string;
  sector: string;
  uploaded_by: string;
  uploaded_at: string;
}

export const SectorReports: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSector, setSelectedSector] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<SectorReportFile[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userSectors, setUserSectors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  //Fetch user sectors/files
  useEffect(() => {
    fetch('/api/user/sectors')
      .then((res) => res.json())
      .then((data) => setUserSectors(data.sectors || []))
      .catch(() => setUserSectors([]));

    fetchFiles();
  }, []);

  //Fetch list of files from backend
  const fetchFiles = async () => {
    setLoadingFiles(true);
    setError(null);
    try {
      const res = await fetch('/api/sector-reports');
      if (!res.ok) throw new Error('Failed to fetch files');
      const data = await res.json();
      setFiles(data.files || []);
    } catch (e: any) {
      setError(e.message || 'Error fetching files');
    } finally {
      setLoadingFiles(false);
    }
  };

  //File selection handling
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  //Handles changing sectors (not sure if this idea will work longterm if we're pulling sectors for users form the backend)
  const handleSectorChange = (event: SelectChangeEvent<string>) => {
    setSelectedSector(event.target.value as string);
  };

  //File upload handling
  const handleUpload = async () => {
    if (!selectedFile || !selectedSector) {
      setError('Please select a file and sector.');
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('sector', selectedSector);
      const res = await fetch('/api/sector-reports/upload', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) throw new Error('Upload failed');
      setSelectedFile(null);
      setSelectedSector('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchFiles();
    } catch (e: any) {
      setError(e.message || 'Error uploading file');
    } finally {
      setUploading(false);
    }
  };

  // Handle file download
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

  // Handle file delete (admin only)
  const handleDelete = async (filename: string) => {
    setError(null);
    try {
      const res = await fetch(
        `/api/sector-reports/delete/${encodeURIComponent(filename)}`,
        {
          method: 'DELETE'
        }
      );
      if (!res.ok) throw new Error('Delete failed');
      fetchFiles();
    } catch (e: any) {
      setError(e.message || 'Error deleting file');
    }
  };

  // Filter files by user's sectors (access control)
  const visibleFiles = files.filter((file) =>
    userSectors.includes(file.sector)
  );

  // Optional: sector filter for viewing
  const [filterSector, setFilterSector] = useState<string>('All');
  const filteredFiles =
    filterSector === 'All'
      ? visibleFiles
      : visibleFiles.filter((file) => file.sector === filterSector);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" mb={3}>
        Sector Reports Archive
      </Typography>
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" mb={2}>
          Upload New Sector Report
        </Typography>
        <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <Button
            variant="contained"
            startIcon={<UploadFileIcon />}
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            Choose File
          </Button>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Sector</InputLabel>
            <Select
              value={selectedSector}
              label="Sector"
              onChange={handleSectorChange}
            >
              {SECTORS.map((sector) => (
                <MenuItem key={sector} value={sector}>
                  {sector}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            color="primary"
            onClick={handleUpload}
            disabled={!selectedFile || !selectedSector || uploading}
          >
            {uploading ? <CircularProgress size={20} /> : 'Upload'}
          </Button>
          <Typography variant="body2">
            {selectedFile ? selectedFile.name : 'No file selected'}
          </Typography>
        </Box>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>
      <Paper sx={{ p: 3 }}>
        <Box display="flex" alignItems="center" mb={2} gap={2}>
          <Typography variant="h6">Archived Reports</Typography>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Filter by Sector</InputLabel>
            <Select
              value={filterSector}
              label="Filter by Sector"
              onChange={(e) => setFilterSector(e.target.value)}
            >
              <MenuItem value="All">All</MenuItem>
              {SECTORS.map((sector) => (
                <MenuItem key={sector} value={sector}>
                  {sector}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        {loadingFiles ? (
          <CircularProgress />
        ) : (
          <List>
            {filteredFiles.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No reports available for your sector(s).
              </Typography>
            )}
            {filteredFiles.map((file) => (
              <ListItem
                key={file.filename}
                secondaryAction={
                  <>
                    <IconButton
                      edge="end"
                      aria-label="download"
                      onClick={() => handleDownload(file.filename)}
                    >
                      <DownloadIcon />
                    </IconButton>
                    {userSectors.includes('admin') && (
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() => handleDelete(file.filename)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    )}
                  </>
                }
              >
                <ListItemText
                  primary={file.filename}
                  secondary={`Sector: ${file.sector} | Uploaded by: ${file.uploaded_by} | ${new Date(
                    file.uploaded_at
                  ).toLocaleString()}`}
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>
    </Container>
  );
};

export default SectorReports;
