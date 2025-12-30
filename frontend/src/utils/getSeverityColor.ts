export const getSeverityColor = ({ id }: { id: string }) => {
  id = id.charAt(0).toUpperCase() + id.slice(1).toLowerCase();
  if (id === 'N/A' || id === '') return '';
  else if (id === 'Low') return '#FFB38A';
  else if (id === 'Medium') return '#EC7633';
  else if (id === 'High') return '#C33200';
  else if (id === 'Critical') return '#731A00';
  else return '';
};

export const getSeverityLevelColorMap = (theme: any) => ({
  low: theme.palette.secondary.light,
  medium: theme.palette.secondary.main,
  high: theme.palette.secondary.dark,
  critical: theme.palette.secondary.darker,
  all: theme.palette.primary.dark
});

export const severityColor = (severity: string | null) => {
  switch (severity) {
    case 'critical':
      return 'secondary.darker';
    case 'high':
      return 'secondary.dark';
    case 'medium':
      return 'secondary.main';
    case 'low':
      return 'secondary.light';
    default:
      return '#000000';
  }
};
