import Papa from 'papaparse';
import * as FileSaver from 'file-saver';

export interface ExportProps<T> {
  name: string;
  fieldsToExport?: string[];
  getDataToExport: () =>
    | Partial<T>[]
    | Promise<Partial<T>[]>
    | Promise<string | null>;
}

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
