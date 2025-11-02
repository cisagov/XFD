import { useEffect } from 'react';

export const MatomoTracker = () => {
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL;
    const matomoPath = import.meta.env.VITE_MATOMO_URL;
    const siteId = import.meta.env.VITE_MATOMO_SITEID;

    if (!apiUrl || !matomoPath) {
      console.error('Matomo configuration missing.');
      return;
    }

    const matomoTrackingApiUrl = `${apiUrl}/matomo/matomo.php`;
    const matomoJsUrl = `${apiUrl}/matomo/matomo.js`;

    // Inject Matomo tracking logic
    const _paq = (window._paq = window._paq || []);
    _paq.push(['setTrackerUrl', matomoTrackingApiUrl]);
    _paq.push(['setSiteId', siteId]);
    _paq.push(['trackPageView']);
    _paq.push(['enableLinkTracking']);

    const script = document.createElement('script');
    script.src = matomoJsUrl;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

  return null;
};
