import React from 'react';
import { useAuthContext } from 'context/AuthContext';
import { TermsOfUse } from 'components/Dialog/TermsOfUse/TermsOfUse';

interface TermsGateProps {
  children: React.ReactNode;
}

const TermsGate: React.FC<TermsGateProps> = ({ children }) => {
  const { user, userMustSign } = useAuthContext();

  if (user?.isRegistered && !user?.invite_pending && userMustSign) {
    return <TermsOfUse />;
  }

  return <>{children}</>;
};

export default TermsGate;
