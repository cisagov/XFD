import React from 'react';

/**
 * Define a structural clone of the library's InspectParams.
 * Important: `codeInfo` is OPTIONAL here to match the lib.
 */
export type InspectParams = {
  codeInfo?: {
    relativePath?: string;
    absolutePath?: string;
    lineNumber?: number | string;
    columnNumber?: number | string;
  };
};

type Props = {
  onClickElement?: (params: InspectParams) => void;
  children?: React.ReactNode;
};

export function DevInspector({ onClickElement, children }: Props) {
  // No inspector in production bundles
  if (!import.meta.env.DEV) return <>{children}</>;

  // Lazy-load so the module is only pulled in during dev
  const Inspector = React.useMemo(
    () =>
      React.lazy(() =>
        import('react-dev-inspector').then((m) => ({ default: m.Inspector }))
      ),
    []
  );

  // Guard the optional param and forward
  const handleClick = React.useCallback(
    (clickedParams: InspectParams) => {
      if (!onClickElement) return;
      if (!clickedParams?.codeInfo) return;
      onClickElement(clickedParams);
    },
    [onClickElement]
  );

  return (
    <React.Suspense fallback={<>{children}</>}>
      <Inspector disableLaunchEditor onClickElement={handleClick} />
      {children}
    </React.Suspense>
  );
}
