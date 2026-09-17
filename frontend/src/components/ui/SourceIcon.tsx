import React from 'react';

interface SourceIconProps {
  app: string;
  className?: string;
  size?: number;
}

export const SourceIcon: React.FC<SourceIconProps> = ({ app, className = '', size = 16 }) => {
  const norm = app.toLowerCase();

  if (norm === 'sheets' || norm.includes('sheet') || norm.includes('google')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`inline-block ${className}`}
      >
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#10B981" strokeWidth="1.5" />
        <line x1="3" y1="9" x2="21" y2="9" stroke="#10B981" strokeWidth="1.5" />
        <line x1="3" y1="15" x2="21" y2="15" stroke="#10B981" strokeWidth="1.5" />
        <line x1="9" y1="3" x2="9" y2="21" stroke="#10B981" strokeWidth="1.5" />
      </svg>
    );
  }

  if (norm === 'github' || norm.includes('git')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`inline-block ${className}`}
      >
        <path
          d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"
          stroke="#A1A1AA"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (norm === 'slack') {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`inline-block ${className}`}
      >
        <rect x="4" y="4" width="6" height="6" rx="2" stroke="#F59E0B" strokeWidth="1.5" />
        <rect x="14" y="4" width="6" height="6" rx="2" stroke="#6366F1" strokeWidth="1.5" />
        <rect x="4" y="14" width="6" height="6" rx="2" stroke="#10B981" strokeWidth="1.5" />
        <rect x="14" y="14" width="6" height="6" rx="2" stroke="#EF4444" strokeWidth="1.5" />
      </svg>
    );
  }

  // Surge mark (abstract triangular convergent vector)
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`inline-block ${className}`}
    >
      <path
        d="M12 2L2 19.5H22L12 2Z"
        stroke="#818CF8"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="14" r="2" fill="#818CF8" />
    </svg>
  );
};
