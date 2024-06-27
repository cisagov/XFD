import React, { useRef, useState } from 'react';
import { Button, Label, FormGroup } from '@trussworks/react-uswds';
import { FileInput } from 'components';
import { useAuthContext } from 'context';
import Papa from 'papaparse';
import * as FileSaver from 'file-saver';
import { Paper } from '@mui/material';

interface ImportProps<T> {
  // Plural name of the model.
  name: string;

  // Callback that handles data on import (usually saves the data).
  onImport: (e: T[]) => void;

  fieldsToImport: string[];
}

export interface ExportProps<T> {
  // Plural name of the model.
  name: string;

  // List of fields to export.
  fieldsToExport?: string[];

  // Return data to be exported.
  getDataToExport: () => Partial<T>[] | Promise<Partial<T>[]> | Promise<string>;
}

// interface ImportExportProps<T> extends ImportProps<T>, ExportProps<T> {}

export const Import = <T extends object>(props: ImportProps<T>) => {
  const { setLoading } = useAuthContext();
  const { name, onImport, fieldsToImport } = props;
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [results, setResults] = React.useState<T[] | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [key, setKey] = useState(Math.random().toString());

  const parseCSV = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || !event.target.files.length) {
      return;
    }
    const file = event.target.files[0];
    setSelectedFile(file); // Store the selected file in state.
    setLoading((l) => l + 1);

    const parsedResults: T[] = await new Promise((resolve, reject) =>
      Papa.parse(event.target.files![0], {
        header: true,
        dynamicTyping: true,
        complete: ({ data, errors }) =>
          errors.length ? reject(errors) : resolve(data as T[])
      })
    );
    setLoading((l) => l - 1);
    setResults(parsedResults); // Store the parsed CSV in state.
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  // Handle submission of uploaded CSV.
  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (results) {
      onImport(results);
      deleteFile();
    }
  };

  // Clear uploaded file.
  const deleteFile = () => {
    setSelectedFile(null);
    setResults(null);
    setKey(Math.random().toString()); // Change the key.

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Import {name}</h2>
      <FormGroup>
        <Label htmlFor="import">
          File must be in a CSV format, header must include the following
          fields: <br /> {fieldsToImport.join(', ')}
        </Label>
        <FileInput
          key={key}
          id="import"
          accept=".csv"
          onChange={(e) => parseCSV(e)}
        />
        {selectedFile && (
          <Paper sx={{ width: 'fit-content' }}>
            <p style={{ marginLeft: '0.5rem' }}>
              Selected file: {selectedFile.name}
              <Button
                type="button"
                outline
                onClick={deleteFile}
                title="Delete file"
                style={{
                  fontSize: '1rem',
                  padding: '0.5rem',
                  marginLeft: '1rem'
                }}
              >
                X
              </Button>
            </p>
          </Paper>
        )}
        <Button outline type="submit" style={{ marginTop: '0.5rem' }}>
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
  if (typeof data === 'string') {
    setLoading((l) => l - 1);
    window.open(data);
    return;
  }
  const csv = Papa.unparse({
    fields: props.fieldsToExport ?? [],
    data: data
  });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  FileSaver.saveAs(blob, `${filename}.csv`);
  setLoading((l) => l - 1);
};

export const ImportExport = <T extends object>(props: ImportProps<T>) => {
  const { name, onImport, fieldsToImport } = props;
  return (
    <>
      <Import name={name} onImport={onImport} fieldsToImport={fieldsToImport} />
    </>
  );
};
