import React from 'react';

export const StatusIcon = ({
  status,
  className = "",
}: {
  status: string;
  className?: string;
}) => {
  const s = status.toUpperCase();
  const sizeClass = "w-4 h-4 shrink-0";
  
  if (s === "RUNNING") {
    // animated rotating ring
    return (
      <svg className={`${sizeClass} animate-spin text-brand ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
      </svg>
    );
  }
  
  if (s === "SUCCEEDED" || s === "COMPLETED") {
    // solid square
    return (
      <svg className={`${sizeClass} text-foreground ${className}`} viewBox="0 0 24 24" fill="currentColor">
        <rect x="5" y="5" width="14" height="14" />
      </svg>
    );
  }
  
  if (s === "FAILED" || s === "PARTIAL_FAILED") {
    // broken diamond
    return (
      <svg className={`${sizeClass} text-foreground ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter">
        <path d="M12 2L2 12L12 22L17 17M22 12L17 7" strokeLinecap="square" />
      </svg>
    );
  }
  
  if (s === "RETRYING") {
    // double circle
    return (
      <svg className={`${sizeClass} text-brand ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="5" />
      </svg>
    );
  }
  
  if (s === "QUEUED") {
    // hollow square
    return (
      <svg className={`${sizeClass} text-foreground-muted ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <rect x="5" y="5" width="14" height="14" />
      </svg>
    );
  }
  
  if (s === "DEAD_LETTERED") {
    // broken square (heavy)
    return (
      <svg className={`${sizeClass} text-foreground ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M5 5h14v14H5z" strokeDasharray="4 4" />
      </svg>
    );
  }
  
  if (s === "CANCELLED") {
    // cross line
    return (
      <svg className={`${sizeClass} text-foreground-muted ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="10" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    );
  }
  
  if (s === "SKIPPED") {
    // dashed circle
    return (
      <svg className={`${sizeClass} text-foreground-muted ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray="4 4">
        <circle cx="12" cy="12" r="10" />
      </svg>
    );
  }

  // PENDING or default: simple dot
  return (
    <svg className={`${sizeClass} text-foreground-muted ${className}`} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
};

export const Icons = {
  Workflow: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" {...props}>
      <circle cx="6" cy="6" r="2" />
      <circle cx="18" cy="6" r="2" />
      <circle cx="6" cy="18" r="2" />
      <circle cx="18" cy="18" r="2" />
      <line x1="6" y1="8" x2="6" y2="16" />
      <line x1="8" y1="6" x2="16" y2="6" />
    </svg>
  ),
  Activity: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter" {...props}>
      <polyline points="3 12 8 12 12 4 16 20 20 12 23 12" />
    </svg>
  ),
  Server: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" {...props}>
      <rect x="2" y="4" width="20" height="6" />
      <rect x="2" y="14" width="20" height="6" />
      <line x1="6" y1="7" x2="6.01" y2="7" />
      <line x1="6" y1="17" x2="6.01" y2="17" />
    </svg>
  ),
  Archive: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" {...props}>
      <rect x="3" y="3" width="18" height="6" />
      <rect x="5" y="9" width="14" height="12" />
      <line x1="10" y1="13" x2="14" y2="13" />
    </svg>
  ),
  Play: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" {...props}>
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  ),
  Code: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter" {...props}>
      <polyline points="8 6 2 12 8 18" />
      <polyline points="16 6 22 12 16 18" />
      <line x1="14" y1="4" x2="10" y2="20" />
    </svg>
  ),
  ChevronRight: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter" {...props}>
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  ChevronDown: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" strokeLinejoin="miter" {...props}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  Close: (props: any) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};
