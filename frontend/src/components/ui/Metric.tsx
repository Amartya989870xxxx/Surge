import React from 'react';

interface MetricProps {
  label: string;
  value: React.ReactNode;
  subtext?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  status?: 'good' | 'warning' | 'bad' | 'neutral';
  className?: string;
}

export const Metric: React.FC<MetricProps> = ({
  label,
  value,
  subtext,
  status = 'neutral',
  className = '',
}) => {
  const statusColors = {
    good: 'text-emerald-400',
    warning: 'text-amber-400',
    bad: 'text-red-400',
    neutral: 'text-[#F5F5F5]',
  };

  return (
    <div className={`p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded ${className}`}>
      <div className="text-[11px] font-mono uppercase tracking-wider text-[#71717A] mb-1">
        {label}
      </div>
      <div className={`text-2xl font-mono font-bold tracking-tight ${statusColors[status]}`}>
        {value}
      </div>
      {subtext && <div className="text-xs text-[#A1A1AA] mt-1">{subtext}</div>}
    </div>
  );
};
