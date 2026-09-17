import React, { useState } from 'react';
import type {
  EvidenceOut,
  HypothesisOut,
  ActionOut,
  ClaimOut,
} from '../../types/api';
import { SourceIcon } from '../ui/SourceIcon';
import { Badge } from '../ui/Badge';

interface EvidenceCanvasProps {
  evidence: EvidenceOut[];
  hypotheses: HypothesisOut[];
  actions: ActionOut[];
  claims: ClaimOut[];
  selectedEvidenceId?: string;
  selectedHypothesisId?: string;
  onSelectEvidence?: (id: string) => void;
  onSelectHypothesis?: (id: string) => void;
}

export const EvidenceCanvas: React.FC<EvidenceCanvasProps> = ({
  evidence,
  hypotheses,
  actions,
  claims,
  selectedEvidenceId,
  selectedHypothesisId,
  onSelectEvidence,
  onSelectHypothesis,
}) => {
  const [viewMode, setViewMode] = useState<'graph' | 'digest'>('graph');

  // Group evidence by source app
  const sheetsEvidence = evidence.filter((e) => e.source_app.toLowerCase().includes('sheet'));
  const githubEvidence = evidence.filter((e) => e.source_app.toLowerCase().includes('git'));
  const slackEvidence = evidence.filter((e) => e.source_app.toLowerCase().includes('slack'));

  const sortedHypotheses = [...hypotheses].sort((a, b) => b.confidence - a.confidence);

  return (
    <div className="flex flex-col h-full bg-[#0B0B0D] border border-[#1A1A1F] rounded overflow-hidden">
      {/* Top View Mode Switch */}
      <div className="px-4 py-2.5 bg-[#111114]/80 border-b border-[#1A1A1F] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-[#F5F5F5] uppercase tracking-wider">
            Analysis Canvas
          </span>
          <span className="text-[10px] font-mono text-[#71717A]">
            {viewMode === 'graph' ? 'Correlation DAG' : 'Claims Grounding'}
          </span>
        </div>

        <div className="flex items-center bg-[#050505] p-0.5 rounded border border-[#24242B] font-mono text-xs">
          <button
            onClick={() => setViewMode('graph')}
            className={`px-3 py-1 rounded transition-colors cursor-pointer ${
              viewMode === 'graph'
                ? 'bg-indigo-950/80 text-indigo-300 font-bold border border-indigo-800/60'
                : 'text-[#71717A] hover:text-[#A1A1AA]'
            }`}
          >
            Graph View
          </button>
          <button
            onClick={() => setViewMode('digest')}
            className={`px-3 py-1 rounded transition-colors cursor-pointer ${
              viewMode === 'digest'
                ? 'bg-indigo-950/80 text-indigo-300 font-bold border border-indigo-800/60'
                : 'text-[#71717A] hover:text-[#A1A1AA]'
            }`}
          >
            Claims Digest
          </button>
        </div>
      </div>

      {/* Main Canvas Body */}
      <div className="flex-1 overflow-auto p-4 bg-[#050505]/50">
        {viewMode === 'graph' ? (
          <div className="min-w-[700px] h-full flex flex-col justify-between py-2">
            {/* SVG Interactive Relationship DAG */}
            <div className="grid grid-cols-4 gap-6 h-full font-mono text-xs">
              {/* Column 1: Connected Sources */}
              <div className="flex flex-col gap-3 justify-center">
                <div className="text-[10px] uppercase font-bold text-[#71717A] mb-1">
                  1. Data Sources
                </div>

                <div className="p-3 bg-[#0E0E11] border border-[#1A1A1F] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <SourceIcon app="sheets" size={16} />
                    <span className="font-bold text-[#F5F5F5]">Sheets</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded">
                    {sheetsEvidence.length} items
                  </span>
                </div>

                <div className="p-3 bg-[#0E0E11] border border-[#1A1A1F] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <SourceIcon app="github" size={16} />
                    <span className="font-bold text-[#F5F5F5]">GitHub</span>
                  </div>
                  <span className="text-[10px] text-indigo-400 bg-indigo-950/40 px-1.5 py-0.5 rounded">
                    {githubEvidence.length} items
                  </span>
                </div>

                <div className="p-3 bg-[#0E0E11] border border-[#1A1A1F] rounded flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <SourceIcon app="slack" size={16} />
                    <span className="font-bold text-[#F5F5F5]">Slack</span>
                  </div>
                  <span className="text-[10px] text-amber-400 bg-amber-950/40 px-1.5 py-0.5 rounded">
                    {slackEvidence.length} items
                  </span>
                </div>
              </div>

              {/* Column 2: Correlated Evidence */}
              <div className="flex flex-col gap-2 justify-center">
                <div className="text-[10px] uppercase font-bold text-[#71717A] mb-1">
                  2. Evidence Artifacts
                </div>

                {evidence.slice(0, 5).map((e) => {
                  const isSelected = selectedEvidenceId === e.id;
                  return (
                    <div
                      key={e.id}
                      onClick={() => onSelectEvidence?.(e.id)}
                      className={`p-2 rounded border transition-all cursor-pointer truncate ${
                        isSelected
                          ? 'bg-[#1A1A24] border-indigo-500 text-indigo-200'
                          : 'bg-[#0B0B0D] border-[#1A1A1F] hover:border-[#2A2A35] text-[#A1A1AA]'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-1 text-[10px]">
                        <SourceIcon app={e.source_app} size={11} />
                        <span className="font-bold uppercase text-[#F5F5F5]">{e.source_app}</span>
                        <span className="text-[#71717A] ml-auto">
                          {Math.round(e.relevance_score * 100)}%
                        </span>
                      </div>
                      <div className="text-[11px] truncate text-[#F5F5F5]">{e.title}</div>
                    </div>
                  );
                })}
                {evidence.length > 5 && (
                  <div className="text-center text-[10px] text-[#71717A]">
                    + {evidence.length - 5} more items in corpus
                  </div>
                )}
              </div>

              {/* Column 3: Competing Hypotheses */}
              <div className="flex flex-col gap-2 justify-center">
                <div className="text-[10px] uppercase font-bold text-[#71717A] mb-1">
                  3. Competing Hypotheses
                </div>

                {sortedHypotheses.map((h, i) => {
                  const isLeader = i === 0;
                  const isSelected = selectedHypothesisId === h.id;
                  const pct = Math.round(h.confidence * 100);

                  return (
                    <div
                      key={h.id}
                      onClick={() => onSelectHypothesis?.(h.id)}
                      className={`p-2.5 rounded border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-[#17171C] border-indigo-500'
                          : isLeader
                          ? 'bg-indigo-950/20 border-indigo-800/60'
                          : 'bg-[#0B0B0D] border-[#1A1A1F] hover:border-[#24242B]'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className={`font-bold text-[11px] ${
                            isLeader ? 'text-emerald-400' : 'text-[#F5F5F5]'
                          }`}
                        >
                          {h.label || h.kind}
                        </span>
                        <span
                          className={`font-bold ${
                            isLeader ? 'text-emerald-400' : 'text-zinc-400'
                          }`}
                        >
                          {pct}%
                        </span>
                      </div>
                      <div className="text-[10px] text-[#71717A]">
                        {h.independent_sources?.length || 0} source(s)
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Column 4: Proposed Action & Verification */}
              <div className="flex flex-col gap-3 justify-center">
                <div className="text-[10px] uppercase font-bold text-[#71717A] mb-1">
                  4. Action & Verification
                </div>

                {actions.length === 0 ? (
                  <div className="p-4 bg-[#0B0B0D] border border-dashed border-[#1A1A1F] rounded text-center text-[#71717A] text-[11px]">
                    No action decided yet
                  </div>
                ) : (
                  actions.map((act) => (
                    <div
                      key={act.id}
                      className="p-3 bg-[#0E0E11] border border-indigo-900/60 rounded space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-amber-400 uppercase text-[10px]">
                          {act.action_type}
                        </span>
                        <Badge variant="warning">{act.risk_level}</Badge>
                      </div>

                      <div className="text-xs text-[#F5F5F5] font-semibold truncate">
                        {act.title}
                      </div>

                      <div className="pt-2 border-t border-[#1A1A1F] flex items-center justify-between text-[10px]">
                        <span className="text-[#71717A]">Status:</span>
                        <span className="text-emerald-400 font-bold">
                          {act.verification_status === 'VERIFIED'
                            ? 'VERIFIED ✓'
                            : act.execution_status}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Digest Mode: Claims grounding list */
          <div className="space-y-3 font-mono text-xs max-w-4xl mx-auto">
            <div className="p-3 bg-[#111114] border border-[#1A1A1F] rounded text-xs text-[#A1A1AA]">
              <strong>Grounded Claims Digest:</strong> Surge requires claims made in the diagnosis to
              reference specific, non-fabricated evidence records from connected tools.
            </div>

            {claims.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-xs text-[#71717A]">
                No synthesized claims yet.
              </div>
            ) : (
              claims.map((claim) => (
                <div
                  key={claim.id}
                  className={`p-3 rounded border ${
                    claim.grounded
                      ? 'bg-[#0B0B0D] border-[#1A1A1F]'
                      : 'bg-red-950/20 border-red-800/60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-[#71717A]">#{claim.position}</span>
                      <span className="font-bold text-[10px] text-indigo-400 uppercase">
                        {claim.claim_type}
                      </span>
                    </div>
                    <Badge variant={claim.grounded ? 'verified' : 'danger'}>
                      {claim.grounded ? 'GROUNDED' : 'UNSUPPORTED'}
                    </Badge>
                  </div>

                  <div className="text-xs text-[#F5F5F5] leading-relaxed mb-2">
                    {claim.text}
                  </div>

                  {claim.evidence_ids?.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] text-[#71717A]">
                      <span>Evidence links:</span>
                      <span className="text-[#A1A1AA]">{claim.evidence_ids.join(', ')}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
