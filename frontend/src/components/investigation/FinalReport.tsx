import React, { useState, useEffect } from 'react';
import type {
  InvestigationDetailOut,
  HypothesisOut,
  EvidenceOut,
  ClaimOut,
  ActionOut,
} from '../../types/api';
import {
  getInvestigation,
  getInvestigationHypotheses,
  getInvestigationEvidence,
  getInvestigationClaims,
  getInvestigationActions,
} from '../../lib/api/investigations';
import { SourceIcon } from '../ui/SourceIcon';
import { StatusDot } from '../ui/StatusDot';
import { Button } from '../ui/Button';
import { WorkspaceFaviconButton } from '../ui/WorkspaceFaviconButton';

interface FinalReportProps {
  investigationId: string;
  onBackToDashboard: () => void;
}

export const FinalReport: React.FC<FinalReportProps> = ({
  investigationId,
  onBackToDashboard,
}) => {
  const [investigation, setInvestigation] = useState<InvestigationDetailOut | null>(null);
  const [hypotheses, setHypotheses] = useState<HypothesisOut[]>([]);
  const [evidenceList, setEvidenceList] = useState<EvidenceOut[]>([]);
  const [claims, setClaims] = useState<ClaimOut[]>([]);
  const [actions, setActions] = useState<ActionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Typewriter animation state
  const [displayedSummary, setDisplayedSummary] = useState('');
  const [isTypewriterComplete, setIsTypewriterComplete] = useState(false);

  // Selected / Expanded evidence
  const [expandedClaimId, setExpandedClaimId] = useState<string | null>(null);
  const [showConfidenceBreakdown, setShowConfidenceBreakdown] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [inv, hypos, evs, clms, acts] = await Promise.all([
          getInvestigation(investigationId),
          getInvestigationHypotheses(investigationId).catch(() => []),
          getInvestigationEvidence(investigationId).catch(() => []),
          getInvestigationClaims(investigationId).catch(() => []),
          getInvestigationActions(investigationId).catch(() => []),
        ]);

        setInvestigation(inv);
        setHypotheses(hypos);
        setEvidenceList(evs);
        setClaims(clms);
        setActions(acts);
      } catch (err: any) {
        console.error('Failed to load final report data:', err);
        setError(err.message || 'Failed to generate final report');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [investigationId]);

  // Typewriter effect over already-complete final_summary
  useEffect(() => {
    if (!investigation?.final_summary) {
      setDisplayedSummary('Investigation concluded with no final summary text.');
      setIsTypewriterComplete(true);
      return;
    }

    const fullText = investigation.final_summary;
    let currentIdx = 0;
    setDisplayedSummary('');
    setIsTypewriterComplete(false);

    // Speed: 15ms per character chunk
    const interval = setInterval(() => {
      currentIdx += 2;
      if (currentIdx >= fullText.length) {
        setDisplayedSummary(fullText);
        setIsTypewriterComplete(true);
        clearInterval(interval);
      } else {
        setDisplayedSummary(fullText.slice(0, currentIdx));
      }
    }, 15);

    return () => clearInterval(interval);
  }, [investigation?.final_summary]);

  const handleSkipAnimation = () => {
    if (investigation?.final_summary) {
      setDisplayedSummary(investigation.final_summary);
      setIsTypewriterComplete(true);
    }
  };

  const evidenceMap = new Map<string, EvidenceOut>();
  evidenceList.forEach((e) => evidenceMap.set(e.id, e));

  const claimVariant = (type: string) => {
    switch (type.toUpperCase()) {
      case 'FACT':
        return {
          badge: 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60',
          label: 'FACT · Observed',
        };
      case 'INFERENCE':
        return {
          badge: 'bg-indigo-950/40 text-indigo-300 border-indigo-800/60',
          label: 'INFERENCE · Derived',
        };
      case 'HYPOTHESIS':
        return {
          badge: 'bg-purple-950/40 text-purple-300 border-purple-800/60',
          label: 'HYPOTHESIS · Theory',
        };
      case 'RECOMMENDATION':
        return {
          badge: 'bg-amber-950/40 text-amber-300 border-amber-800/60',
          label: 'RECOMMENDATION · Action',
        };
      default:
        return {
          badge: 'bg-zinc-800 text-zinc-300 border-zinc-700',
          label: type,
        };
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-mono text-xs flex items-center justify-center relative">
        <WorkspaceFaviconButton onNavigateWorkspace={onBackToDashboard} />
        <div className="flex flex-col items-center gap-3">
          <StatusDot status="info" pulse size="md" />
          <span className="text-[#A1A1AA]">Assembling final report and evidence traces...</span>
        </div>
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-mono text-xs flex items-center justify-center p-6 relative">
        <WorkspaceFaviconButton onNavigateWorkspace={onBackToDashboard} />
        <div className="max-w-md p-6 bg-[#0A0A0C] border border-red-800/60 rounded-xl text-center shadow-2xl">
          <div className="text-red-400 font-bold mb-2">Failed to load report</div>
          <p className="text-[#A1A1AA] mb-4">{error || 'Investigation not found'}</p>
          <Button size="sm" variant="secondary" onClick={onBackToDashboard} className="rounded-full px-4 py-2 cursor-pointer">
            ← Return to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const confidenceValue =
    investigation.confidence !== null && investigation.confidence !== undefined
      ? Math.round(investigation.confidence * 100)
      : null;

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-mono text-xs flex flex-col antialiased">
      {/* Top Left Workspace Favicon Link */}
      <WorkspaceFaviconButton onNavigateWorkspace={onBackToDashboard} />

      {/* Floating Top Right Controls */}
      <div className="fixed top-4 right-6 z-30 flex items-center gap-2.5">
        {/* Confidence Badge (Labeled strictly "confidence", not probability/certainty per rule 5) */}
        {confidenceValue !== null && (
          <div className="relative">
            <button
              onClick={() => setShowConfidenceBreakdown(!showConfidenceBreakdown)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/70 backdrop-blur-xl border border-white/10 hover:border-indigo-500/50 cursor-pointer transition-colors shadow-lg"
            >
              <span className="text-[10px] text-[#71717A] uppercase tracking-wider">
                Belief Score:
              </span>
              <span className="font-bold text-emerald-400">{confidenceValue}% confidence</span>
              <span className="text-[10px] text-[#71717A]">ⓘ</span>
            </button>

            {showConfidenceBreakdown && (
              <div className="absolute right-0 top-10 w-72 p-3.5 bg-[#0C0C0E] border border-[#2A2A35] rounded-xl shadow-2xl z-20 space-y-2">
                <div className="font-bold text-[#F5F5F5] text-xs">
                  Confidence Breakdown
                </div>
                <p className="text-[10px] text-[#A1A1AA] leading-relaxed">
                  Surge confidence represents epistemic belief grounded by multi-source evidence
                  coverage and absence checks.
                </p>
                {investigation.confidence_breakdown ? (
                  <pre className="p-2 bg-[#050505] rounded border border-[#18181C] text-[10px] text-indigo-300 overflow-x-auto">
                    {JSON.stringify(investigation.confidence_breakdown, null, 2)}
                  </pre>
                ) : (
                  <div className="text-[10px] text-[#71717A]">
                    No breakdown modifiers applied.
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <Button
          size="sm"
          variant="secondary"
          onClick={onBackToDashboard}
          className="rounded-full px-4 py-1.5 bg-white/[0.08] hover:bg-white/[0.15] border border-white/10 text-xs shadow-lg font-medium cursor-pointer"
        >
          New Investigation
        </Button>
      </div>

      {/* Main Report Body */}
      <main className="flex-1 overflow-y-auto px-6 py-8 pt-16 max-w-4xl mx-auto w-full space-y-8">
        {/* Title & Metadata */}
        <div>
          <div className="flex items-center gap-2 text-[10px] text-[#71717A] uppercase tracking-widest mb-1.5">
            <span>Investigation #{investigation.id}</span>
            <span>·</span>
            <span>{new Date(investigation.created_at).toLocaleString()}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#F5F5F5] leading-tight">
            {investigation.title || investigation.request}
          </h1>
        </div>

        {/* 1. Typewriter-Animated Final Summary */}
        <section className="p-6 bg-[#08080A] border border-[#1E1E24] rounded-xl shadow-2xl relative">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#18181C]">
            <div className="flex items-center gap-2">
              <SourceIcon app="surge" size={16} />
              <span className="font-bold text-xs text-[#F5F5F5] uppercase tracking-wider">
                Executive Synthesis
              </span>
            </div>
            {!isTypewriterComplete && (
              <button
                onClick={handleSkipAnimation}
                className="text-[10px] text-[#71717A] hover:text-[#A1A1AA] cursor-pointer underline"
              >
                Skip animation
              </button>
            )}
          </div>

          <div className="text-xs sm:text-sm text-[#E4E4E7] leading-relaxed whitespace-pre-wrap font-sans">
            {displayedSummary}
            {!isTypewriterComplete && (
              <span className="inline-block w-1.5 h-3.5 bg-indigo-400 ml-1 animate-pulse" />
            )}
          </div>
        </section>

        {/* Ranked Competing Hypotheses */}
        {hypotheses.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#18181C]">
              <div>
                <h2 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider">
                  Ranked Competing Hypotheses
                </h2>
                <p className="text-[11px] text-[#71717A]">
                  Candidate theories tested against multi-source evidence and ranked by posterior belief.
                </p>
              </div>
              <span className="text-[11px] text-[#71717A]">{hypotheses.length} evaluated</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {hypotheses.map((h) => {
                const isWinner =
                  h.status === 'supported' ||
                  h.id === investigation.root_cause_hypothesis_id;
                const confPercent = Math.round(h.confidence * 100);
                const priorPercent = Math.round(h.prior * 100);

                return (
                  <div
                    key={h.id}
                    className={`p-4 rounded-lg border transition-all ${
                      isWinner
                        ? 'bg-emerald-950/20 border-emerald-800/60 ring-1 ring-emerald-800/30'
                        : 'bg-[#08080A] border-[#18181C]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-xs text-[#F5F5F5]">{h.label}</span>
                      <span
                        className={`font-mono font-bold text-xs ${
                          isWinner ? 'text-emerald-400' : 'text-[#71717A]'
                        }`}
                      >
                        {confPercent}% confidence
                      </span>
                    </div>
                    <p className="text-[11px] text-[#A1A1AA] leading-relaxed mb-2.5">
                      {h.statement}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-[#71717A] pt-2 border-t border-[#141418]">
                      <span>Prior: {priorPercent}%</span>
                      <span>Rank #{h.rank}</span>
                      <span className={isWinner ? 'text-emerald-400 font-bold' : ''}>
                        {h.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* 2. "What Surge found" / Basis for Reasoning (Claims + Evidence) */}
        <section className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#18181C]">
            <div>
              <h2 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider">
                What Surge Found
              </h2>
              <p className="text-[11px] text-[#71717A]">
                Structured claims categorized by epistemic source with verified evidence traces.
              </p>
            </div>
            <span className="text-[11px] text-[#71717A]">{claims.length} claims</span>
          </div>

          {claims.length === 0 ? (
            <div className="p-6 bg-[#08080A] border border-[#18181C] rounded-lg text-center text-[#52525B]">
              No discrete claims recorded for this run.
            </div>
          ) : (
            <div className="space-y-3">
              {claims.map((c) => {
                const variant = claimVariant(c.claim_type);
                const isExpanded = expandedClaimId === c.id;
                const claimEvidences = (c.evidence_ids || [])
                  .map((eid) => evidenceMap.get(eid))
                  .filter(Boolean) as EvidenceOut[];

                return (
                  <div
                    key={c.id}
                    className="p-4 bg-[#08080A] border border-[#18181C] hover:border-[#26262E] rounded-lg transition-all"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${variant.badge}`}
                      >
                        {variant.label}
                      </span>
                      {c.grounded && (
                        <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-semibold">
                          ✓ Grounded in data
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-[#E4E4E7] leading-relaxed mb-3">{c.text}</p>

                    {/* Linked Evidence Traces */}
                    {claimEvidences.length > 0 && (
                      <div className="pt-2 border-t border-[#141418]">
                        <button
                          onClick={() => setExpandedClaimId(isExpanded ? null : c.id)}
                          className="flex items-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 cursor-pointer"
                        >
                          <span>{isExpanded ? '▼ Hide' : '▶ View'} Evidence ({claimEvidences.length})</span>
                        </button>

                        {isExpanded && (
                          <div className="mt-3 space-y-2 pl-2 border-l border-indigo-500/30">
                            {claimEvidences.map((ev) => (
                              <div
                                key={ev.id}
                                className="p-3 bg-[#0C0C0E] border border-[#1E1E24] rounded text-[11px] space-y-1.5"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <SourceIcon app={ev.source_app} size={14} />
                                    <span className="font-bold text-[#F5F5F5] capitalize">
                                      {ev.source_app}
                                    </span>
                                    <span className="text-[10px] text-[#71717A]">
                                      ({ev.epistemic_type})
                                    </span>
                                  </div>
                                  {ev.url && (
                                    <a
                                      href={ev.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-indigo-400 hover:underline text-[10px]"
                                    >
                                      View Source ↗
                                    </a>
                                  )}
                                </div>
                                <div className="font-semibold text-zinc-300">{ev.title}</div>
                                <div className="text-[11px] text-[#A1A1AA] bg-[#050505] p-2 rounded border border-[#18181C] font-mono whitespace-pre-wrap">
                                  {ev.snippet}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* 3. "What it did" (Actions Executed & Verification Checks) */}
        <section className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#18181C]">
            <div>
              <h2 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider">
                What Surge Did
              </h2>
              <p className="text-[11px] text-[#71717A]">
                Actions executed with human approval and verified via independent state read-back.
              </p>
            </div>
            <span className="text-[11px] text-[#71717A]">{actions.length} actions</span>
          </div>

          {actions.length === 0 ? (
            <div className="p-6 bg-[#08080A] border border-[#18181C] rounded-lg text-center text-[#52525B]">
              No external mutating actions were executed during this investigation.
            </div>
          ) : (
            <div className="space-y-3">
              {actions.map((act) => {
                const isExecuted = act.execution_status === 'SUCCEEDED';
                const isVerified =
                  act.verification_status === 'VERIFIED' ||
                  act.verification?.result === 'passed';

                return (
                  <div
                    key={act.id}
                    className="p-4 bg-[#08080A] border border-[#18181C] rounded-lg space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <SourceIcon app={act.external_app} size={16} />
                        <span className="font-bold text-xs text-[#F5F5F5]">{act.title}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            isExecuted
                              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                              : 'bg-zinc-800 text-zinc-300 border-zinc-700'
                          }`}
                        >
                          {act.execution_status}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            isVerified
                              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                              : 'bg-amber-950/40 text-amber-300 border-amber-800/60'
                          }`}
                        >
                          {isVerified ? 'VERIFIED ✓' : 'VERIFICATION PENDING'}
                        </span>
                      </div>
                    </div>

                    <p className="text-[11px] text-[#A1A1AA] leading-relaxed">{act.rationale}</p>

                    {act.external_url && (
                      <div className="text-[11px]">
                        <span className="text-[#71717A]">Created resource: </span>
                        <a
                          href={act.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-400 hover:underline"
                        >
                          {act.external_url}
                        </a>
                      </div>
                    )}

                    {/* Verification Read-Back Checks */}
                    {act.verification?.checks && act.verification.checks.length > 0 && (
                      <div className="p-3 bg-[#0C0C0E] rounded border border-[#18181C] space-y-1.5">
                        <div className="text-[10px] uppercase text-[#71717A] tracking-wider font-semibold">
                          Verification Checks (Read-Back Validation)
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                          {act.verification.checks.map((chk, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-[11px] text-[#D4D4D8]"
                            >
                              <span
                                className={
                                  chk.passed ? 'text-emerald-400' : 'text-red-400'
                                }
                              >
                                {chk.passed ? '✓' : '✗'}
                              </span>
                              <span>
                                {chk.check || chk.field || 'Check'}:{' '}
                                <strong className="font-normal text-[#A1A1AA]">
                                  {chk.message || (chk.passed ? 'Confirmed' : 'Failed')}
                                </strong>
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* 4. "Suggestions to prevent this in future" (Known backend gap -> Explicit Coming Soon per Rule 4) */}
        <section className="p-6 bg-[#08080A]/60 border border-[#18181C] rounded-xl space-y-2 select-none">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-[#A1A1AA] uppercase tracking-wider">
              Suggestions to Prevent This in Future
            </h2>
            <span className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400 text-[10px]">
              Coming soon
            </span>
          </div>
          <p className="text-[11px] text-[#71717A] leading-relaxed">
            Automated recurrence prevention recommendations and preventive architecture rules are
            actively in development on the backend roadmap. Surge never fabricates preventive
            advice without verifiable model evidence.
          </p>
        </section>

        {/* Bottom Navigation */}
        <div className="pt-6 border-t border-[#18181C] flex items-center justify-between">
          <Button size="md" variant="secondary" onClick={onBackToDashboard}>
            ← Back to Dashboard
          </Button>
          <Button
            size="md"
            variant="primary"
            onClick={onBackToDashboard}
            className="font-bold text-xs"
          >
            Launch Another Investigation →
          </Button>
        </div>
      </main>
    </div>
  );
};
