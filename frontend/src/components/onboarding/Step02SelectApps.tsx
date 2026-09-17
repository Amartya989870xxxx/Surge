import React from 'react';
import type { AppType } from '../../types/api';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';

interface Step02SelectAppsProps {
  selectedApps: AppType[];
  onToggleApp: (app: AppType) => void;
  onNext: () => void;
  onBack: () => void;
}

export const Step02SelectApps: React.FC<Step02SelectAppsProps> = ({
  selectedApps,
  onToggleApp,
  onNext,
  onBack,
}) => {
  const apps: Array<{
    id: AppType;
    name: string;
    role: string;
    detail: string;
    requiredForAction?: boolean;
  }> = [
    {
      id: 'sheets',
      name: 'Google Sheets',
      role: 'Metrics and operational data',
      detail:
        'Surge inspects spreadsheet time-series to observe anomalies and compare funnels.',
    },
    {
      id: 'github',
      name: 'GitHub',
      role: 'Deployments, code changes and verified issues',
      detail:
        'Surge inspects recent production releases, diffs commit changes, and files verified incident issues.',
      requiredForAction: true,
    },
    {
      id: 'slack',
      name: 'Slack',
      role: 'Team context and operational reports',
      detail:
        'Surge searches public engineering channels to corroborate anomaly reports with customer support feedback.',
    },
  ];

  return (
    <div className="max-w-xl mx-auto py-8 font-mono">
      <div className="mb-6">
        <span className="text-xs text-[#818CF8] uppercase tracking-wider">Step 2 of 5</span>
        <h2 className="text-2xl font-bold text-[#F5F5F5] mt-1 mb-2">
          Which signals should Surge use?
        </h2>
        <p className="text-xs text-[#A1A1AA] leading-relaxed">
          Select the apps you want Surge to correlate. You can review the exact permissions and scopes
          on the next screen before connecting.
        </p>
      </div>

      <div className="space-y-3 mb-8">
        {apps.map((app) => {
          const isChecked = selectedApps.includes(app.id);

          return (
            <div
              key={app.id}
              onClick={() => onToggleApp(app.id)}
              className={`p-4 rounded-lg border transition-all cursor-pointer select-none ${
                isChecked
                  ? 'bg-[#111114] border-indigo-500 shadow-md ring-1 ring-indigo-500/20'
                  : 'bg-[#0B0B0D] border-[#1A1A1F] hover:border-[#24242B]'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="pt-0.5">
                    <SourceIcon app={app.id} size={20} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-[#F5F5F5] flex items-center gap-2">
                      <span>{app.name}</span>
                      {app.requiredForAction && (
                        <span className="text-[10px] text-amber-400 bg-amber-950/40 px-1.5 py-0.2 rounded border border-amber-800/40">
                          Action Target
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-[#818CF8] mt-0.5 mb-1">{app.role}</div>
                    <div className="text-[11px] text-[#71717A] leading-relaxed">
                      {app.detail}
                    </div>
                  </div>
                </div>

                <div className="shrink-0 pt-0.5">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {}} // Handled by container onClick
                    className="w-4 h-4 accent-indigo-500 rounded cursor-pointer"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-[#1A1A1F]">
        <Button size="md" variant="ghost" onClick={onBack} className="text-xs">
          ← Back
        </Button>

        <Button
          size="md"
          variant="primary"
          onClick={onNext}
          disabled={selectedApps.length === 0}
          className="text-xs"
        >
          Review Permissions ({selectedApps.length} selected) →
        </Button>
      </div>
    </div>
  );
};
