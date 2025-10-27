import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAuthContext } from 'context/AuthContext';
import { TermsOfUse } from 'components/Dialog/TermsOfUse/TermsOfUse';

interface TermsGateProps {
  children: React.ReactNode;
}

const TermsGate: React.FC<TermsGateProps> = ({ children }) => {
  const { user, userMustSign } = useAuthContext();
  const location = useLocation();

  console.log('TermsGate Debug:', {
    user: user
      ? {
          isRegistered: user.isRegistered,
          invite_pending: user.invite_pending
        }
      : null,
    userMustSign,
    pathname: location.pathname
  });

  if (user?.isRegistered && !user?.invite_pending && userMustSign) {
    return <TermsOfUse />;
  }

  return <>{children}</>;
};

export default TermsGate;
