import React from 'react';
import type { InvestigationDetailOut } from '../../types/api';
import { Badge } from '../ui/Badge';
import { StatusDot } from '../ui/StatusDot';
import { Button } from '../ui/Button';

interface InvestigationHeaderProps {
  investigation: InvestigationDetailOut;
  onCancel?: () => void;
  onRerun?: () => void;
  cancelling?: boolean;
  rerunning?: boolean;
}

export const InvestigationHeader: React.FC<InvestigationHeaderProps> = ({
  investigation,
  onCancel,
  onRerun,
  cancelling = false,
  rerunning = false,
}) => {
  const isTerminal = ['COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT'].includes(
    investigation.status
  );

  const statusVariant = {
    CREATED: 'neutral' as const,
    PLANNING: 'investigation' as const,
    INVESTIGATING: 'investigation' as const,
    SYNTHESIZING: 'investigation' as const,
    AWAITING_APPROVAL: 'warning' as const,
    EXECUTING: 'investigation' as const,
    VERIFYING: 'investigation' as const,
    COMPLETED: 'verified' as const,
    PARTIAL: 'warning' as const,
    FAILED: 'danger' as const,
    CANCELLED: 'neutral' as const,
    TIMED_OUT: 'danger' as const,
  }[investigation.status] || 'neutral';

  return (
    <div className="bg-[#0B0B0D] border-b border-[#1A1A1F] px-6 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex flex-col gap-1.5 min-w-0">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="font-mono text-xs font-semibold text-[#F5F5F5] tracking-wide">
            {investigation.id}
          </span>

          <Badge variant={statusVariant}>
            <StatusDot
              status={
                statusVariant === 'verified'
                  ? 'success'
                  : statusVariant === 'warning'
                  ? 'warning'
                  : statusVariant === 'danger'
                  ? 'danger'
                  : statusVariant === 'investigation'
                  ? 'info'
                  : 'neutral'
              }
              pulse={!isTerminal}
              size="sm"
            />
            <span>{investigation.status.replace('_', ' ')}</span>
          </Badge>

          <Badge variant={investigation.connector_mode === 'REAL' ? 'real' : 'demo'}>
            {investigation.connector_mode} MODE
          </Badge>

          {investigation.degraded && (
            <Badge variant="warning">DEGRADED COVERAGE</Badge>
          )}

          {investigation.scenario_id && (
            <span className="text-[11px] font-mono text-[#71717A]">
              scenario: {investigation.scenario_id}
            </span>
          )}
        </div>

        <h1 className="text-sm md:text-base font-semibold text-[#F5F5F5] truncate max-w-3xl">
          {investigation.title || investigation.request}
        </h1>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {investigation.duration_ms != null && (
          <div className="text-xs font-mono text-[#71717A]">
            Duration: <span className="text-[#A1A1AA]">{(investigation.duration_ms / 1000).toFixed(2)}s</span>
          </div>
        )}

        {!isTerminal && onCancel && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onCancel}
            loading={cancelling}
            className="text-xs text-red-400 hover:text-red-300"
          >
            Cancel Investigation
          </Button>
        )}

        {isTerminal && onRerun && (
          <Button
            size="sm"
            variant="secondary"
            onClick={onRerun}
            loading={rerunning}
            className="text-xs font-mono"
          >
            Rerun Investigation ↺
          </Button>
        )}
      </div>
    </div>
  );
};
