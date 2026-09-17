import React from 'react';
import type { AppType } from '../../types/api';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';
import { Badge } from '../ui/Badge';

interface Step05CompleteProps {
  selectedApps: AppType[];
  onLaunchInvestigation: () => void;
  onGoToWorkspace: () => void;
}

export const Step05Complete: React.FC<Step05CompleteProps> = ({
  selectedApps,
  onLaunchInvestigation,
  onGoToWorkspace,
}) => {
  return (
    <div className="max-w-xl mx-auto py-8 font-mono text-center">
      <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-950/40 border border-emerald-700/60 mb-4 text-emerald-400 text-2xl">
        ✓
      </div>

      <h2 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5] mb-2">
        You're ready to investigate.
      </h2>
      <p className="text-xs text-[#A1A1AA] max-w-md mx-auto leading-relaxed mb-8">
        Surge has configured your local workspace session with permission-aware access. It can now
        correlate operational metrics, code deployments, and team reports.
      </p>

      {/* Connected Summary */}
      <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg max-w-md mx-auto mb-8 text-left">
        <div className="text-[11px] text-[#71717A] uppercase mb-3 font-semibold">
          Active Workspace Channels
        </div>
        <div className="space-y-2">
          {selectedApps.map((app) => (
            <div key={app} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-[#F5F5F5]">
                <SourceIcon app={app} size={16} />
                <span className="capitalize">{app}</span>
              </div>
              <Badge variant="verified">READY</Badge>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <Button
          size="md"
          variant="primary"
          onClick={onLaunchInvestigation}
          className="w-full sm:w-auto text-xs px-6"
        >
          Start Your First Investigation →
        </Button>
        <Button
          size="md"
          variant="secondary"
          onClick={onGoToWorkspace}
          className="w-full sm:w-auto text-xs"
        >
          Go to Control Room
        </Button>
      </div>
    </div>
  );
};
