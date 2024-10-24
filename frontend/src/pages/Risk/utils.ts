import { VulnSeverities } from './Risk';

export const resultsPerPage = 30;
export const getSingleColor = () => {
  return '#F23AB8';
};

export const getTooltipColor = () => {
  return '#FFFFFF';
};

export const getAllVulnColor = () => {
  return '#ce80ed';
};
export const getSeverityColor = ({ id }: { id: string }) => {
  if (id === 'N/A' || id === '') return '#EFF1F5';
  else if (id === 'Low') return '#ffe100';
  else if (id === 'Medium') return '#f66e1f';
  else if (id === 'High') return '#ed240e';
  else if (id === 'Other') return '#6BA7F5';
  else return '#540C03';
};
export const getCVSSColor = (score: number) => {
  if (!score || score === 0) return ['#EFF1F5', 'NONE'];
  else if (0.1 <= score && score <= 3.9) return ['#ffe100', 'LOW'];
  else if (4 <= score && score <= 6.9) return ['#fd913f', 'MEDIUM'];
  else if (7 <= score && score <= 8.9) return ['#f13a25', 'HIGH'];
  else if (9 <= score && score <= 10) return ['#ab0225', 'CRITICAL'];
  else return '#540C03';
};
export const offsets: any = {
  Vermont: [50, -8],
  'New Hampshire': [34, 2],
  Massachusetts: [30, -1],
  'Rhode Island': [28, 2],
  Connecticut: [35, 10],
  'New Jersey': [34, 1],
  Delaware: [33, 0],
  Maryland: [47, 10],
  'District of Columbia': [49, 21]
};

export const sevLabels = ['', 'Low', 'Medium', 'High', 'Critical'];

// Create severity object for Open Vulnerability chips
export const severities: VulnSeverities[] = [
  { label: 'All', sevList: ['', 'Low', 'Medium', 'High', 'Critical'] },
  { label: 'Critical', sevList: ['Critical'] },
  { label: 'High', sevList: ['High'] },
  { label: 'Medium', sevList: ['Medium'] },
  { label: 'Low', sevList: ['Low'] }
];

export const getServicesColor = ({ id }: { id: string }) => {
  if (id === 'null' || id === '') return '#EFF1F5';
  else if (id === 'http') return '#2cb9ff';
  else if (id === 'https') return '#0e8cd6';
  else if (id === 'rdp') return '#0063b4';
  else if (id === 'ftp') return '#2a6ebb';
  else if (id === 'ssh') return '#5792ff';
  else return '#540C03';
};

export const delay = (ms: number) => new Promise((res) => setTimeout(res, ms));
