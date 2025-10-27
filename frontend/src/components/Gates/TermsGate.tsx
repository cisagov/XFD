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

  if (user?.isRegistered && !user?.invite_pending && userMustSign) {
    return <TermsOfUse />;
  }

  return <>{children}</>;
};

export default TermsGate;
