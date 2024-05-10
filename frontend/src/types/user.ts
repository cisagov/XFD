import { Role } from './role';
import { ApiKey } from './api-key';

export interface User {
  id: string;
  createdAt: string;
  updatedAt: string;
  firstName: string;
  lastName: string;
  fullName: string;
  invitePending: boolean;
  userType:
    | 'standard'
    | 'globalView'
    | 'globalAdmin'
    | 'regionalAdmin'
    | 'readySetCyber';
  email: string;
  roles: Role[];
  dateAcceptedTerms: string | null;
  acceptedTermsVersion: string | null;
  lastLoggedIn: string | null;
  apiKeys: ApiKey[];
  regionId?: string | null;
  state?: string | null;
  organizations?: Array<string>;
  isRegistered?: boolean | null;
  loginBlockedByMaintenance?: boolean | false;
}

export const initializeUser: User = {
  id: '',
  createdAt: '',
  updatedAt: '',
  firstName: '',
  lastName: '',
  fullName: '',
  invitePending: true,
  userType: 'standard',
  email: '',
  roles: [],
  dateAcceptedTerms: null,
  acceptedTermsVersion: null,
  lastLoggedIn: null,
  apiKeys: [],
  regionId: null,
  state: null,
  organizations: [],
  isRegistered: null
};
