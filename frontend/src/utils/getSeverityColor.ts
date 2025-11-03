export const getSeverityColor = ({ id }: { id: string }) => {
  id = id.charAt(0).toUpperCase() + id.slice(1).toLowerCase();
  if (id === 'N/A' || id === '') return '';
  else if (id === 'Low') return '#FFB38A';
  else if (id === 'Medium') return '#EC7633';
  else if (id === 'High') return '#C33200';
  else if (id === 'Critical') return '#731A00';
  else return '';
};
