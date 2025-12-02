import { useCallback, useState } from 'react';
import { useAuthContext } from 'context';
import { ENDPOINTS } from '@/constants/endpoints';
import { logger } from '@/utils/logger';
import { format } from 'date-fns';
import { User } from 'types';

export interface ApprovedBy {
  id: string;
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  user_type: string;
  region_id: string;
  state: string;
}

export interface UserType extends User {
  lastLoggedInString?: string | null | undefined;
  dateToUSigned?: string | null | undefined;
  orgs?: string | null | undefined;
  org_acronym?: string | null | undefined;
  full_name: string;
  approved_by?: ApprovedBy | null;
  date_approved?: string | null;
}

interface UseFetchUsersResult {
  users: UserType[];
  isLoading: boolean;
  error: string;
  setUsers: Function;
  fetchUsers: () => Promise<void>;
  deleteUser: (row: UserType) => Promise<DeleteResult>;
}

interface DeleteResult {
  success: boolean;
  errorMessage: string;
}

export const useUserApi = (): UseFetchUsersResult => {
  const { user, apiDelete, apiGet } = useAuthContext();
  const [users, setUsers] = useState<UserType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setError('');

    try {
      const rows: UserType[] = await apiGet<UserType[]>(ENDPOINTS.USERS);

      // Data Transformation/Formatting Logic (Moved from component)
      rows.forEach((row) => {
        row.lastLoggedInString = row.last_logged_in
          ? format(new Date(row.last_logged_in), 'MM-dd-yyyy hh:mm a')
          : 'None';
        row.dateToUSigned = row.date_accepted_terms
          ? format(new Date(row.date_accepted_terms), 'MM-dd-yyyy hh:mm a')
          : 'None';
        row.orgs = row.roles
          ? row.roles
              .filter((role) => role.approved)
              .map((role) => role.organization.name)
              .join(', ')
          : 'None';
        row.full_name = `${row.first_name} ${row.last_name}`;
        row.org_acronym = row.roles[0]?.organization.acronym || '';
      });

      // Assuming 'filteredRows' logic was placeholder or regional filtering
      // is handled elsewhere. We set the transformed rows directly.
      setUsers(rows);
    } catch (e: any) {
      logger.error('useFetchUsers failed:', { error: e });
      setError(e.message || 'Failed to fetch users.');
      setUsers([]);
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, user?.user_type, user?.region_id]); // Included user dependencies for memoization

  const deleteUser = useCallback(
    async (row: UserType): Promise<DeleteResult> => {
      let errorMessage = '';

      try {
        await apiDelete(ENDPOINTS.USER.replace('{user_id}', String(row.id)), {
          body: {}
        });

        // Update state: remove the deleted user
        setUsers((prevUsers) => prevUsers.filter((user) => user.id !== row.id));

        return { success: true, errorMessage: '' };
      } catch (e: any) {
        errorMessage = e.message || 'Unknown deletion error';
        logger.error('useUserApi.deleteUser failed:', {
          error: e,
          userId: row.id
        });
        return { success: false, errorMessage };
      }
    },
    [apiDelete]
  );

  return {
    users,
    isLoading,
    error,
    setUsers,
    fetchUsers,
    deleteUser
  };
};
