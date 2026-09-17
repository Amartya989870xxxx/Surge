import React from 'react';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';

interface Step01WelcomeProps {
  onNext: () => void;
  onSkip: () => void;
}

export const Step01Welcome: React.FC<Step01WelcomeProps> = ({ onNext, onSkip }) => {
  return (
    <div className="max-w-xl mx-auto py-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-950/40 border border-indigo-800/60 mb-4">
          <SourceIcon app="surge" size={24} />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F5F5] mb-3">
          Let's connect the signals Surge needs.
        </h1>
        <p className="text-sm text-[#A1A1AA] leading-relaxed">
          Surge investigates operational anomalies by correlating evidence across the tools your team
          already uses. In the next steps, you will select which apps to connect and review the
          exact permissions requested.
        </p>
      </div>

      {/* Honest Local Session & Demo Banner */}
      <div className="p-4 bg-[#111114] border border-[#24242B] rounded-lg mb-8 font-mono text-xs text-[#A1A1AA]">
        <div className="text-[#F5F5F5] font-bold mb-1 flex items-center gap-1.5">
          <span>ℹ</span> Local Workspace Session Notice
        </div>
        <div className="leading-relaxed text-[11px] text-[#71717A]">
          This session runs in local workspace mode. The Surge backend does not provide a
          multi-tenant authentication or password service. Preferences and session markers are stored
          locally to coordinate investigations.
        </div>
      </div>

      {/* Tri-source preview */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="p-3 bg-[#0B0B0D] border border-[#1A1A1F] rounded text-center">
          <SourceIcon app="sheets" size={20} className="mx-auto mb-1.5" />
          <div className="font-mono text-xs font-semibold text-[#F5F5F5]">Sheets</div>
          <div className="text-[10px] text-[#71717A] mt-0.5">Metrics & funnels</div>
        </div>
        <div className="p-3 bg-[#0B0B0D] border border-[#1A1A1F] rounded text-center">
          <SourceIcon app="github" size={20} className="mx-auto mb-1.5" />
          <div className="font-mono text-xs font-semibold text-[#F5F5F5]">GitHub</div>
          <div className="text-[10px] text-[#71717A] mt-0.5">Deployments & issues</div>
        </div>
        <div className="p-3 bg-[#0B0B0D] border border-[#1A1A1F] rounded text-center">
          <SourceIcon app="slack" size={20} className="mx-auto mb-1.5" />
          <div className="font-mono text-xs font-semibold text-[#F5F5F5]">Slack</div>
          <div className="text-[10px] text-[#71717A] mt-0.5">Team reports</div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-[#1A1A1F]">
        <button
          onClick={onSkip}
          className="text-xs font-mono text-[#71717A] hover:text-[#A1A1AA] cursor-pointer"
        >
          Skip for now (enter Demo mode)
        </button>

        <Button size="md" variant="primary" onClick={onNext} className="font-mono text-xs">
          Choose Apps →
        </Button>
      </div>
    </div>
  );
};
