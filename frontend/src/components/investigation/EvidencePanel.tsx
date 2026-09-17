import React, { useState } from 'react';
import type { EvidenceOut } from '../../types/api';
import { SourceIcon } from '../ui/SourceIcon';
import { Badge } from '../ui/Badge';

interface EvidencePanelProps {
  evidence: EvidenceOut[];
  selectedId?: string;
  onSelect?: (id: string) => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidence,
  selectedId,
  onSelect,
}) => {
  const [filterApp, setFilterApp] = useState<string>('ALL');

  const filtered = evidence.filter((e) => {
    if (filterApp === 'ALL') return true;
    return e.source_app.toLowerCase() === filterApp.toLowerCase();
  });

  return (
    <div className="flex flex-col h-full bg-[#0B0B0D] border border-[#1A1A1F] rounded overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-[#1A1A1F] bg-[#111114]/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-[#F5F5F5] uppercase tracking-wider">
            Evidence Corpus
          </span>
          <span className="text-[11px] font-mono text-[#71717A] bg-[#17171C] px-1.5 py-0.5 rounded border border-[#24242B]">
            {evidence.length} items
          </span>
        </div>

        {/* Source App Filter */}
        <div className="flex items-center gap-1 font-mono text-[11px]">
          {['ALL', 'SHEETS', 'GITHUB', 'SLACK'].map((app) => (
            <button
              key={app}
              onClick={() => setFilterApp(app)}
              className={`px-2 py-0.5 rounded transition-colors cursor-pointer ${
                filterApp === app
                  ? 'bg-indigo-950/60 text-indigo-300 border border-indigo-800/60'
                  : 'text-[#71717A] hover:text-[#A1A1AA]'
              }`}
            >
              {app}
            </button>
          ))}
        </div>
      </div>

      {/* List of Evidence Cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 font-mono text-xs">
        {filtered.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-xs text-[#71717A]">
            No evidence retrieved yet.
          </div>
        ) : (
          filtered.map((item) => {
            const isSelected = selectedId === item.id;
            const isFact = item.epistemic_type === 'observation';
            const isComputed = item.epistemic_type === 'computed_observation';
            const isAbsence = item.epistemic_type === 'absence_check';

            return (
              <div
                key={item.id}
                onClick={() => onSelect?.(item.id)}
                className={`p-3 rounded border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#17171C] border-indigo-500 shadow-md ring-1 ring-indigo-500/30'
                    : isFact
                    ? 'bg-[#111114] border-[#2A2A35] hover:border-[#383848]'
                    : 'bg-[#0E0E11] border-[#1A1A1F] hover:border-[#24242B]'
                }`}
              >
                {/* Metadata Row */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <SourceIcon app={item.source_app} size={14} />
                    <span className="font-bold text-[#F5F5F5] uppercase text-[11px]">
                      {item.source_app}
                    </span>
                    <span className="text-[10px] text-[#71717A]">{item.source_record_id}</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {/* Material Epistemic Distinction */}
                    {isFact && (
                      <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border bg-emerald-950/60 text-emerald-300 border-emerald-800/60 tracking-wider">
                        FACT / OBSERVATION
                      </span>
                    )}
                    {isComputed && (
                      <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border bg-indigo-950/60 text-indigo-300 border-indigo-800/60 tracking-wider">
                        COMPUTED
                      </span>
                    )}
                    {isAbsence && (
                      <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded border bg-amber-950/60 text-amber-300 border-amber-800/60 tracking-wider">
                        ABSENCE CHECK
                      </span>
                    )}
                    <Badge variant={item.connector_mode === 'REAL' ? 'real' : 'demo'}>
                      {item.connector_mode}
                    </Badge>
                  </div>
                </div>

                {/* Claim Title */}
                <div className="font-medium text-[#F5F5F5] leading-snug mb-1.5">{item.title}</div>

                {/* Snippet / Normalized Content */}
                {item.snippet && (
                  <div className="p-2 bg-[#050505] rounded border border-[#1A1A1F] text-[11px] text-[#A1A1AA] leading-relaxed mb-2 font-mono whitespace-pre-wrap">
                    {item.snippet}
                  </div>
                )}

                {/* Hypotheses Relations */}
                <div className="flex flex-wrap items-center gap-1.5 text-[10px] pt-1">
                  {item.supports_hypothesis_ids?.length > 0 && (
                    <span className="text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded border border-emerald-900/40">
                      + Supports: {item.supports_hypothesis_ids.join(', ')}
                    </span>
                  )}
                  {item.contradicts_hypothesis_ids?.length > 0 && (
                    <span className="text-red-400 bg-red-950/30 px-1.5 py-0.5 rounded border border-red-900/40 font-bold">
                      - Contradicts: {item.contradicts_hypothesis_ids.join(', ')}
                    </span>
                  )}
                  <span className="text-[#71717A] ml-auto">
                    score: {(item.relevance_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
