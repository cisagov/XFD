import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import {
  Button,
  Checkbox,
  FormControlLabel,
  Typography,
  Box,
  Stack,
  Alert
} from '@mui/material';
import { useAuthContext } from 'context';
import { User } from 'types';

export const TermsOfUse: React.FC = () => {
  const history = useHistory();
  const [accepted, setAccepted] = useState<boolean>(false);
  const [showWarning, setShowWarning] = useState<boolean>(false);
  const { user, setUser, apiPost, maximumRole, touVersion } = useAuthContext();

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault();
    if (!accepted) {
      setShowWarning(true);
      return;
    }
    setShowWarning(false);
    try {
      const updated: User = await apiPost(`/users/me/acceptTerms`, {
        body: { version: touVersion }
      });
      setUser(updated);
      history.push('/', {
        message: 'Your account has been successfully created.',
        showFirstLoginPopup: true
      });
    } catch (e: any) {
      // handle error
    }
  };

  const adminItems = [
    'You have authority to authorize scanning/evaluation of the public-facing networks and systems you submit within CyHy Dashboard and you authorize CISA to conduct any such scans/evaluation through CyHy Dashboard;',
    'You agree to promptly update or change the information used to identify the public-facing networks and systems to be scanned/evaluated pursuant to this authorization;',
    'You agree to comply with any notification or authorization requirement that any third party that operates or maintains your public-facing networks or systems may impose on external vulnerability scanning services, modifying any CyHy Dashboard scans associated with your account if external scanning of those resources is later prohibited;',
    'You accept that, while CyHy Dashboard will use best efforts to conduct scans in a way that minimizes risk to your organization’s systems and networks, CyHy Dashboard scanning activities creates some risk of degradation in performance to your organization’s systems and networks;',
    'You agree that CISA may share data gathered by CyHy Dashboard with other federal agencies with cybersecurity responsibilities, with the Multi-State Information Sharing and Analysis Center, and with the Election Infrastructure Information Sharing and Analysis Center;',
    'You are authorized to make the above certifications on your organization’s behalf;'
  ];

  const notItems = [
    'Use the CyHy Dashboard service in violation of any applicable law;',
    'Access or attempt to access any CyHy Dashboard account other than your own; and',
    'Introduce malware to the CyHy Dashboard platform or otherwise impair, harm, or disrupt the functioning or integrity of the platform in any way;'
  ];

  const Bullet = () => (
    <Box
      component="span"
      sx={{ fontWeight: 'bold', pr: 1, fontSize: 18, lineHeight: 1.7 }}
      aria-hidden="true"
    >
      •
    </Box>
  );

  return (
    <Box
      sx={{ width: '100%', display: 'flex', justifyContent: 'center', py: 4 }}
    >
      <Box
        component="form"
        onSubmit={onSubmit}
        noValidate
        sx={{
          width: '100%',
          maxWidth: 600,
          bgcolor: 'background.paper',
          boxShadow: (theme) => theme.shadows[1],
          borderRadius: 1,
          p: { xs: 2, sm: 3 },
          boxSizing: 'border-box'
        }}
      >
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          width="100%"
          sx={{ gap: 2, py: 4, maxWidth: 800, mx: 'auto' }}
        >
          <Typography
            variant="h4"
            align="center"
            gutterBottom
            sx={{ fontWeight: 'bold', mb: 2 }}
          >
            Terms of Use
          </Typography>
          <Typography sx={{ lineHeight: 4, width: '100%', pl: 3 }}>
            You must read and sign the Terms of Use before using CyHy Dashboard.
          </Typography>
          <Typography sx={{ lineHeight: 2, pl: 2 }}>
            CyHy Dashboard is a free, self-service tool offered by the
            Department of Homeland Security’s Cybersecurity and Infrastructure
            Security Agency (CISA). Using both passive and active processes,
            CyHy Dashboard can continuously evaluate the cybersecurity posture
            of your public-facing, internet-accessible network assets for
            vulnerabilities or configuration issues.
          </Typography>
          <Typography sx={{ lineHeight: 4, width: '100%', pl: 3 }}>
            Users can only view data provided to or collected by CyHy Dashboard.
          </Typography>
          {maximumRole === 'admin' && (
            <Typography
              align="left"
              sx={{ lineHeight: 2, width: '100%', pl: 2 }}
            >
              Once you create a CyHy Dashboard administrator account, input the
              Internet Protocol (IP) addresses or domains to be continuously
              evaluated, and select the scanning/evaluation protocols to be
              used, CyHy Dashboard will collect data about the sites you
              specified from multiple publicly-available resources, including
              through active interactions with your sites, if that option is
              selected by you. CyHy Dashboard will also examine any
              publicly-available, internet-accessible resources that appear to
              be related or otherwise associated with IPs or domains you have
              provided us to evaluate, presenting you with a list of those
              related sites for your awareness.
            </Typography>
          )}
          <Typography align="left" sx={{ lineHeight: 2, width: '100%', pl: 2 }}>
            By creating a CyHy Dashboard{' '}
            {maximumRole === 'admin' ? 'administrator' : 'view only'} account
            and using this service, you request CISA’s technical assistance to
            detect vulnerabilities and configuration issues through CyHy
            Dashboard and agree to the following:
          </Typography>
          <Stack sx={{ width: '100%', maxWidth: 700, pl: 4 }}>
            {maximumRole === 'admin' &&
              adminItems.map((item, idx) => (
                <Box
                  key={`admin-item-${idx}`}
                  display="flex"
                  alignItems="flex-start"
                >
                  <Bullet />
                  <Typography sx={{ lineHeight: 1.7 }} align="left">
                    {item}
                  </Typography>
                </Box>
              ))}
            <Box display="flex" alignItems="flex-start">
              <Bullet />
              <Typography sx={{ lineHeight: 1.7 }} align="left">
                You accept that CISA may modify or discontinue the CyHy
                Dashboard service at any time;
              </Typography>
            </Box>
            <Box display="flex" alignItems="flex-start">
              <Bullet />
              <Typography sx={{ lineHeight: 1.7 }} align="left">
                You acknowledge that use of CyHy Dashboard is governed
                exclusively by federal law and that CISA provides no warranties
                of any kind relating to any aspect of your use of CyHy
                Dashboard, including that CyHy Dashboard may detect only a
                limited range of vulnerabilities or configuration issues and
                that there is no guarantee that CyHy Dashboard will detect any
                or all vulnerabilities or configuration issues present in your
                system;
              </Typography>
            </Box>
            <Box display="flex" alignItems="flex-start">
              <Bullet />
              <Box>
                <Typography align="left" sx={{ lineHeight: 1.7 }}>
                  You agree to not:
                </Typography>
                <Stack spacing={1} sx={{ pl: 3, pt: 1 }}>
                  {notItems.map((item, idx) => (
                    <Box
                      key={`not-item-${idx}`}
                      display="flex"
                      alignItems="flex-start"
                    >
                      <Bullet />
                      <Typography sx={{ lineHeight: 1.7 }} align="left">
                        {item}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            </Box>
            <Box display="flex" alignItems="flex-start">
              <Bullet />
              <Typography sx={{ lineHeight: 1.7 }} align="left">
                You accept that, at CISA’s sole discretion, CISA may terminate
                or suspend your access to the CyHy Dashboard service due to
                violation of these terms or any other reason.
              </Typography>
            </Box>
          </Stack>
          <Typography align="center" sx={{ mt: 1 }}>
            ToU version {touVersion}
          </Typography>
          {showWarning && (
            <Typography color="error" sx={{ mb: 1 }}>
              You must accept the Terms and Conditions to continue.
            </Typography>
          )}
          <FormControlLabel
            control={
              <Checkbox
                required
                checked={accepted}
                onChange={(e) => {
                  setAccepted(e.target.checked);
                  if (e.target.checked) {
                    setShowWarning(false);
                  }
                }}
                name="accept"
                color="primary"
              />
            }
            label="I accept the above Terms and Conditions."
            sx={{ mb: -1 }}
          />
          <Typography align="center" sx={{ mb: 1, lineHeight: 1 }}>
            <strong>Name:</strong> {user?.full_name}
          </Typography>
          <Typography align="center" sx={{ mb: 0, lineHeight: 1 }}>
            <strong>Email:</strong> {user?.email}
          </Typography>
          <Button type="submit" variant="contained" sx={{ mt: 0 }}>
            Submit
          </Button>
        </Box>
      </Box>
    </Box>
  );
};
