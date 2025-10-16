import React, { useRef, useState } from 'react';
import {
  Button,
  Paper,
  Typography,
  FormGroup,
  FormLabel,
  Box
} from '@mui/material';
import Papa from 'papaparse';
import * as FileSaver from 'file-saver';
import { FileInput } from 'components';
import { useAuthContext } from 'context';

interface ImportProps<T> {
  name: string;
  onImport: (e: T[]) => void;
  fieldsToImport: string[];
}

export interface ExportProps<T> {
  name: string;
  fieldsToExport?: string[];
  getDataToExport: () =>
    | Partial<T>[]
    | Promise<Partial<T>[]>
    | Promise<string | null>;
}

export const Import = <T extends object>(props: ImportProps<T>) => {
  const { setLoading } = useAuthContext();
  const { name, onImport, fieldsToImport } = props;
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [results, setResults] = useState<T[] | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [key, setKey] = useState(Math.random().toString());

  const parseCSV = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files?.length) return;

    const file = event.target.files[0];
    setSelectedFile(file);
    setLoading((l) => l + 1);

    const reader = new FileReader();
    reader.onload = async () => {
      const text = (reader.result as string).replace(/^\uFEFF/, ''); // strip BOM
      try {
        const parsedResults: T[] = await new Promise((resolve, reject) =>
          Papa.parse<T>(text, {
            header: true,
            dynamicTyping: true,
            skipEmptyLines: true,
            complete: ({ data, errors }) =>
              errors.length ? reject(errors) : resolve(data)
          })
        );
        setResults(parsedResults);
      } catch (err) {
        console.error('Parse error:', err);
      } finally {
        setLoading((l) => l - 1);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    };
    reader.readAsText(file);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (results) {
      onImport(results);
      deleteFile();
    }
  };

  const deleteFile = () => {
    setSelectedFile(null);
    setResults(null);
    setKey(Math.random().toString());
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <form onSubmit={handleSubmit}>
      <Typography variant="h5" gutterBottom mt={3} mb={1}>
        Import {name}
      </Typography>
      <FormGroup>
        <FormLabel htmlFor="import">
          <Typography variant="body2" color="neutrals.main" mb={1}>
            The file must be in CSV format.
          </Typography>
          <Typography variant="body2" color="neutrals.main" mb={1}>
            The header must be on the first line and include the following
            fields:
          </Typography>
          <Typography variant="body2" color="neutrals.dark">
            {fieldsToImport.join(', ')}
          </Typography>
        </FormLabel>
        <Box mt={1}>
          <FileInput
            key={key}
            id="import"
            accept=".csv"
            onChange={(e) => parseCSV(e)}
          />
        </Box>
        {selectedFile && (
          <Paper
            sx={{
              mt: 2,
              px: 2,
              py: 1,
              display: 'flex',
              alignItems: 'center',
              width: 'fit-content'
            }}
          >
            <Typography variant="body2">
              Selected file: {selectedFile.name}
            </Typography>
            <Button
              type="button"
              onClick={deleteFile}
              title="Delete file"
              size="small"
              color="error"
              sx={{ ml: 2 }}
            >
              Remove
            </Button>
          </Paper>
        )}

        <Button
          variant="contained"
          type="submit"
          sx={{ mt: 2, width: 'fit-content' }}
          disabled={!selectedFile}
        >
          Upload CSV
        </Button>
      </FormGroup>
    </form>
  );
};

export const exportCSV = async <T extends object>(
  props: ExportProps<T>,
  setLoading: React.Dispatch<React.SetStateAction<number>>
) => {
  const filename = `${props.name}-${new Date().toISOString()}`;
  setLoading((l) => l + 1);
  const data = await props.getDataToExport();
  if (data == null) return;

  if (typeof data === 'string') {
    const link = document.createElement('a');
    link.href = data;
    link.download = `${filename}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setLoading((l) => l - 1);
    return;
  }

  const csv = Papa.unparse({
    fields: props.fieldsToExport ?? [],
    data
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  FileSaver.saveAs(blob, `${filename}.csv`);
  setLoading((l) => l - 1);
};

export const ImportExport = <T extends object>(props: ImportProps<T>) => {
  const { name, onImport, fieldsToImport } = props;
  return (
    <Import name={name} onImport={onImport} fieldsToImport={fieldsToImport} />
  );
};
