import React, { useLayoutEffect, useRef, useState } from 'react';
import {
  Button,
  Dialog as MuiDialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  type PaperProps
} from '@mui/material';

type DialogComponentProps = {
  isOpen: boolean;
  onClose?: (...args: any[]) => void;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  content: React.ReactNode;
  disabled?: boolean;
  screenWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** Set to false if you want to disable the size animation entirely */
  animateSize?: boolean;
  /** ms for the size animation */
  durationMs?: number;
};

/** Measures its children and animates height between changes. */
const AnimatedHeight: React.FC<
  React.PropsWithChildren<{ animate?: boolean; durationMs?: number }>
> = ({ children, animate = true, durationMs = 200 }) => {
  const innerRef = useRef<HTMLDivElement | null>(null);
  const [height, setHeight] = useState<number | null>(null);

  useLayoutEffect(() => {
    const el = innerRef.current;
    if (!el) return;

    // Measure immediately
    const measure = () => setHeight(el.scrollHeight);

    measure();

    // Watch for size changes
    let ro: ResizeObserver | null = null;
    if ('ResizeObserver' in window) {
      ro = new ResizeObserver(() => measure());
      ro.observe(el);
    } else {
      // Fallback: measure on next tick when children likely changed
      const id = requestAnimationFrame(measure);
      return () => cancelAnimationFrame(id);
    }
    return () => {
      ro?.disconnect();
    };
  }, [children]);

  const style: React.CSSProperties = animate
    ? {
        height: height == null ? 'auto' : `${height}px`,
        overflow: 'hidden',
        transition: `height ${durationMs}ms ease`
      }
    : {};

  return (
    <div style={style}>
      <div ref={innerRef}>{children}</div>
    </div>
  );
};

const AnimatedConfirmDialog: React.FC<DialogComponentProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onCancel,
  title,
  content,
  disabled = false,
  screenWidth = 'sm',
  animateSize = true,
  durationMs = 200
}) => {
  const paperProps: PaperProps = animateSize
    ? {
        sx: {
          // Hide overflow so vertical animation looks clean
          overflow: 'hidden',
          // Use a plain string instead of a function to avoid DevTools warnings
          transition: `width ${durationMs}ms ease, max-width ${durationMs}ms ease`
        }
      }
    : {};

  return (
    <MuiDialog
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth={screenWidth}
      PaperProps={paperProps}
    >
      <DialogTitle>{title}</DialogTitle>

      {/* Animate vertical size changes inside the dialog */}
      <DialogContent sx={{ p: 0 }}>
        <AnimatedHeight animate={animateSize} durationMs={durationMs}>
          {/* Put your padded content in here so the measured height is accurate */}
          <div style={{ padding: 24 }}>{content}</div>
        </AnimatedHeight>
      </DialogContent>

      <DialogActions sx={{ pb: 3, pr: 3 }}>
        <Button size="large" variant="text" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="large"
          variant="contained"
          onClick={onConfirm}
          disabled={disabled}
        >
          Confirm
        </Button>
      </DialogActions>
    </MuiDialog>
  );
};

export default AnimatedConfirmDialog;
