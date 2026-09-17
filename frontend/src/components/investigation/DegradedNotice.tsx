import React from 'react';

interface DegradedNoticeProps {
  missingSources: string[];
  confidenceAdjustment?: string;
}

export const DegradedNotice: React.FC<DegradedNoticeProps> = ({
  missingSources,
  confidenceAdjustment,
}) => {
  if (!missingSources || missingSources.length === 0) return null;

  return (
    <div className="p-4 bg-amber-950/20 border border-amber-800/60 rounded-lg font-mono text-xs mb-4">
      <div className="flex items-center gap-2 text-amber-400 font-bold uppercase mb-2">
        <span>⚠ CONNECTOR DEGRADED / UNAVAILABLE</span>
      </div>

      <div className="text-[#F5F5F5] mb-2 leading-relaxed">
        Surge detected connectivity failure on:{' '}
        <span className="text-amber-300 font-bold">{missingSources.join(', ').toUpperCase()}</span>.
      </div>

      <div className="p-2 bg-[#050505] rounded border border-[#1A1A1F] text-[#A1A1AA] leading-relaxed mb-2">
        <strong>Evidence Handling Principle:</strong> Missing evidence from unavailable connectors is
        explicitly <em>not</em> treated as contradictory evidence. Surge adjusts confidence bounds to
        reflect lower source diversity.
      </div>

      {confidenceAdjustment && (
        <div className="text-amber-400 text-[11px]">
          Confidence adjusted: {confidenceAdjustment}
        </div>
      )}
    </div>
  );
};
