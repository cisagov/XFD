import type { InspectParams } from './devInspector';

const DEFAULT_CONTAINER_ROOT = '/app';

// Local frontend root directory (set in .env)
const LOCAL_FRONTEND_ROOT =
  (import.meta.env.VITE_LOCAL_FRONTEND_ROOT as string | undefined) || '';

/**
 * Maps the container path in `codeInfo` to your local path and opens the file in VS Code.
 * No impact to prod and only runs when called from DevInspector in dev builds.
 */
export function openInVSCode(
  { codeInfo }: InspectParams,
  opts?: { containerRoot?: string; localRoot?: string }
) {
  if (!codeInfo) return;

  const containerRoot = opts?.containerRoot ?? DEFAULT_CONTAINER_ROOT;
  const localRoot = opts?.localRoot ?? LOCAL_FRONTEND_ROOT;

  let abs = codeInfo.absolutePath;

  // If only a relative path is provided, create a container-absolute path
  if (!abs && codeInfo.relativePath) {
    abs = `${containerRoot}/${codeInfo.relativePath}`.replace(/\/{2,}/g, '/');
  }

  // Handle no absolute path
  if (!abs) return;

  // Translate container path (/app/...) to local host path
  if (localRoot && abs.startsWith(containerRoot)) {
    abs = abs.replace(containerRoot, localRoot);
  }

  // Convert v2 strings for compatability
  const line = Number(codeInfo.lineNumber ?? 1) || 1;
  const col = Number(codeInfo.columnNumber ?? 1) || 1;

  const url = `vscode://file${abs}:${line}:${col}`;
  window.location.href = encodeURI(url);
}
