import React from 'react';
import type { HypothesisOut } from '../../types/api';

interface HypothesisPanelProps {
  hypotheses: HypothesisOut[];
  selectedId?: string;
  onSelect?: (id: string) => void;
}

export const HypothesisPanel: React.FC<HypothesisPanelProps> = ({
  hypotheses,
  selectedId,
  onSelect,
}) => {
  // Sort by rank / confidence desc
  const sorted = [...hypotheses].sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="flex flex-col h-full bg-[#0B0B0D] border border-[#1A1A1F] rounded overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-[#1A1A1F] bg-[#111114]/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-[#F5F5F5] uppercase tracking-wider">
            Competing Hypotheses
          </span>
          <span className="text-[11px] font-mono text-[#71717A] bg-[#17171C] px-1.5 py-0.5 rounded border border-[#24242B]">
            {hypotheses.length} candidates
          </span>
        </div>
        <span className="text-[10px] font-mono text-[#71717A]">
          Posterior Probability
        </span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 font-mono text-xs">
        {sorted.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-xs text-[#71717A]">
            No hypotheses evaluated yet.
          </div>
        ) : (
          sorted.map((h, idx) => {
            const isSelected = selectedId === h.id;
            const isLeader = idx === 0;
            const hasContradictions = h.contradicting_evidence_ids?.length > 0;
            const pct = Math.round(h.confidence * 100);
            const priorPct = Math.round(h.prior * 100);

            return (
              <div
                key={h.id}
                onClick={() => onSelect?.(h.id)}
                className={`p-3 rounded border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#17171C] border-indigo-500 shadow-md ring-1 ring-indigo-500/30'
                    : isLeader
                    ? 'bg-[#111114] border-indigo-900/60'
                    : 'bg-[#0E0E11] border-[#1A1A1F] hover:border-[#24242B]'
                }`}
              >
                {/* Header row */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${
                        isLeader
                          ? 'bg-indigo-950 text-indigo-300 border-indigo-800'
                          : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                      }`}
                    >
                      RANK #{idx + 1}
                    </span>
                    <span className="font-bold text-[#F5F5F5] text-xs truncate max-w-[180px]">
                      {h.label || h.kind}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#71717A]">prior: {priorPct}%</span>
                    <span
                      className={`text-sm font-bold ${
                        isLeader
                          ? 'text-emerald-400'
                          : pct > 30
                          ? 'text-indigo-300'
                          : 'text-zinc-400'
                      }`}
                    >
                      {pct}%
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-[#1A1A1F] h-1.5 rounded-full mb-2.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isLeader
                        ? 'bg-emerald-500'
                        : pct > 30
                        ? 'bg-indigo-500'
                        : 'bg-zinc-600'
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>

                {/* Statement / Rationale */}
                <div className="text-[11px] text-[#A1A1AA] leading-relaxed mb-2">
                  {h.statement || h.rationale}
                </div>

                {/* Evidence Support & Contradictions */}
                <div className="space-y-1 text-[10px] pt-2 border-t border-[#1A1A1F]">
                  <div className="flex items-center justify-between text-[#71717A]">
                    <span>Independent sources:</span>
                    <span className="text-[#A1A1AA] font-bold">
                      {h.independent_sources?.length ? h.independent_sources.join(', ') : 'none'}
                    </span>
                  </div>

                  {h.supporting_evidence_ids?.length > 0 && (
                    <div className="text-emerald-400">
                      + Supported by {h.supporting_evidence_ids.length} evidence items
                    </div>
                  )}

                  {hasContradictions ? (
                    <div className="text-red-400 font-bold bg-red-950/20 px-1.5 py-0.5 rounded border border-red-900/40">
                      ⚠ Contradicted by {h.contradicting_evidence_ids.length} evidence items
                    </div>
                  ) : (
                    <div className="text-[#71717A]">No contradictions found</div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
