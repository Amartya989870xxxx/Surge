import React from 'react';

export type StatusDotVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

interface StatusDotProps {
  status?: StatusDotVariant;
  pulse?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusDot: React.FC<StatusDotProps> = ({
  status = 'neutral',
  pulse = false,
  size = 'sm',
  className = '',
}) => {
  const sizeClass = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5';

  const colorClasses: Record<StatusDotVariant, string> = {
    success: 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.5)]',
    warning: 'bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.5)]',
    danger: 'bg-red-400 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
    info: 'bg-indigo-400 shadow-[0_0_8px_rgba(99,102,241,0.5)]',
    neutral: 'bg-zinc-500',
  };

  return (
    <span className={`relative inline-flex items-center justify-center shrink-0 ${className}`}>
      {pulse && (
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${colorClasses[status]}`}
        />
      )}
      <span className={`relative inline-flex rounded-full ${sizeClass} ${colorClasses[status]}`} />
    </span>
  );
};
