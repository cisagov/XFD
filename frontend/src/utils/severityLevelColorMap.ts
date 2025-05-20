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
