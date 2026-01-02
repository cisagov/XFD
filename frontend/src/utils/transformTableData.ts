import { formatDate, parseISO } from 'date-fns';
import { User } from 'types';

export const transformUserData = (data: User[]): User[] => {
  return data.map(({ roles, ...user }) => ({
    ...user,
    roles,
    organizations: roles.map((role) => ' ' + role.organization.name),
    org_acronym: roles[0]?.organization.acronym || '',
    organizations_display: roles
      .map((role) => role.organization.name)
      .join(', '),
    last_logged_in: user.last_logged_in
      ? formatDate(parseISO(user.last_logged_in), 'MM/dd/yyyy hh:mm a')
      : 'None'
  }));
};
