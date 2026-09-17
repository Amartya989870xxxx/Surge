import React from 'react';

interface PanelProps {
  children: React.ReactNode;
  header?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

export const Panel: React.FC<PanelProps> = ({
  children,
  header,
  actions,
  className = '',
  bodyClassName = 'p-4',
}) => {
  return (
    <div
      className={`bg-[#0B0B0D] border border-[#1A1A1F] rounded flex flex-col overflow-hidden ${className}`}
    >
      {header && (
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1A1A1F] bg-[#111114]/50">
          <div className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
            {header}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={`flex-1 overflow-auto ${bodyClassName}`}>{children}</div>
    </div>
  );
};
