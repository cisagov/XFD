# CRASM-3996 Working Notes

## Current implementation status

- Standardized completed or in progress for:
  - Organization Members
  - Scan Queue Monitor
  - Scans
  - Notification tables
  - Scan Metrics Summary and HTTP Status Trends
  - Scan Tasks
- Domains and Vulnerabilities empty-grid `Paper` height changed from `minHeight: 500` to `200` after testing showed the pagination footer was visually displaced when no rows were returned.
- All current changes remain uncommitted for developer review.

## Scan Tasks follow-up

- The frontend sends server-side filter requests and now uses the shared 500 ms debounce, persistent grid mounting, active-filter state, and pagination reset behavior.
- The Scan Tasks backend currently only applies `name`, `status`, `organization`, and `tag` filters.
- The Data Grid exposes the `ID` column as filterable, but the backend ignores the submitted `id` filter. This behavior also exists on `develop`; it is not caused by the standardization changes.
- Revisit whether to add backend ID filtering or disable the unsupported ID filter in the UI.
