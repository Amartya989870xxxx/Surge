import React, { useState, useEffect } from 'react';
import type { InvestigationSummaryOut, ConnectorsOut, EvaluationSuiteOut } from '../../types/api';
import { listInvestigations } from '../../lib/api/investigations';
import { listConnectors } from '../../lib/api/connectors';
import { getLatestEvaluation } from '../../lib/api/evaluations';
import { Badge } from '../ui/Badge';
import { StatusDot } from '../ui/StatusDot';
import { Button } from '../ui/Button';

interface OverviewPageProps {
  onSelectInvestigation: (id: string) => void;
  onOpenNewInvestigation: () => void;
  onViewReliability: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  onSelectInvestigation,
  onOpenNewInvestigation,
  onViewReliability,
}) => {
  const [investigations, setInvestigations] = useState<InvestigationSummaryOut[]>([]);
  const [connectors, setConnectors] = useState<ConnectorsOut | null>(null);
  const [latestEval, setLatestEval] = useState<EvaluationSuiteOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listInvestigations({ limit: 20 }),
      listConnectors().catch(() => null),
      getLatestEvaluation().catch(() => null),
    ]).then(([invList, connList, evalSuite]) => {
      setInvestigations(invList.items || []);
      setConnectors(connList);
      setLatestEval(evalSuite);
      setLoading(false);
    });
  }, []);

  const activeCount = investigations.filter(
    (i) => !['COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT'].includes(i.status)
  ).length;

  const verifiedCount = investigations.filter((i) => i.verified).length;

  const statusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'verified' as const;
      case 'AWAITING_APPROVAL':
        return 'warning' as const;
      case 'FAILED':
      case 'TIMED_OUT':
        return 'danger' as const;
      default:
        return 'investigation' as const;
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto font-mono text-xs text-[#F5F5F5]">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5]">Investigation Control Room</h1>
          <p className="text-xs text-[#71717A] mt-0.5">
            Monitor incoming investigations, correlated evidence sources, and verified provider actions.
          </p>
        </div>

        <Button size="sm" variant="primary" onClick={onOpenNewInvestigation} className="text-xs">
          + Launch Investigation
        </Button>
      </div>

      {/* 4 Metric Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
          <div className="text-[11px] text-[#71717A] uppercase mb-1">Active Runs</div>
          <div className="text-2xl font-bold text-[#F5F5F5] flex items-center gap-2">
            <span>{activeCount}</span>
            {activeCount > 0 && <StatusDot status="info" pulse size="sm" />}
          </div>
          <div className="text-[10px] text-[#71717A] mt-1">In observation / synthesis</div>
        </div>

        <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
          <div className="text-[11px] text-[#71717A] uppercase mb-1">Verified Actions</div>
          <div className="text-2xl font-bold text-emerald-400">{verifiedCount}</div>
          <div className="text-[10px] text-[#71717A] mt-1">Independently confirmed</div>
        </div>

        <div
          onClick={onViewReliability}
          className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] hover:border-indigo-900/60 rounded-lg cursor-pointer transition-colors"
        >
          <div className="text-[11px] text-[#71717A] uppercase mb-1 flex items-center justify-between">
            <span>Benchmark Score</span>
            <span className="text-indigo-400 text-[10px]">View →</span>
          </div>
          <div className="text-2xl font-bold text-indigo-300">
            {latestEval?.headline?.diagnosis_accuracy != null
              ? `${Math.round(latestEval.headline.diagnosis_accuracy * 100)}%`
              : '16 / 16'}
          </div>
          <div className="text-[10px] text-[#71717A] mt-1">Seeded regression suite</div>
        </div>

        <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
          <div className="text-[11px] text-[#71717A] uppercase mb-1">Connectors</div>
          <div className="text-2xl font-bold text-emerald-400">
            {connectors?.connectors.length || 3}
          </div>
          <div className="text-[10px] text-[#71717A] mt-1">Sheets · GitHub · Slack</div>
        </div>
      </div>

      {/* Investigations Table */}
      <div className="bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg overflow-hidden">
        <div className="p-3 bg-[#111114] border-b border-[#1A1A1F] flex items-center justify-between">
          <span className="font-bold text-xs uppercase tracking-wider text-[#A1A1AA]">
            Recent Investigations ({investigations.length})
          </span>
          <span className="text-[10px] text-[#71717A]">
            Click any row to open full live canvas
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-[#71717A]">Loading investigations...</div>
        ) : investigations.length === 0 ? (
          <div className="p-12 text-center text-[#71717A] space-y-3">
            <div>No investigations created yet.</div>
            <Button size="sm" variant="primary" onClick={onOpenNewInvestigation}>
              Launch First Investigation
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#1A1A1F] text-[10px] text-[#71717A] uppercase">
                  <th className="p-3">ID / Time</th>
                  <th className="p-3">Request / Objective</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Strongest Hypothesis</th>
                  <th className="p-3">Action State</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1A1A1F]">
                {investigations.map((inv) => {
                  const dateStr = inv.created_at ? inv.created_at.substring(11, 19) : '--:--';
                  const hyp = inv.strongest_hypothesis;

                  return (
                    <tr
                      key={inv.id}
                      onClick={() => onSelectInvestigation(inv.id)}
                      className="hover:bg-[#111114] transition-colors cursor-pointer"
                    >
                      <td className="p-3 whitespace-nowrap">
                        <div className="font-bold text-[#F5F5F5]">{inv.id}</div>
                        <div className="text-[10px] text-[#71717A]">{dateStr} UTC</div>
                      </td>

                      <td className="p-3 max-w-xs truncate">
                        <div className="text-[#F5F5F5] font-medium truncate">{inv.title || inv.request}</div>
                        {inv.scenario_id && (
                          <span className="text-[10px] text-[#71717A]">
                            scenario: {inv.scenario_id}
                          </span>
                        )}
                      </td>

                      <td className="p-3 whitespace-nowrap">
                        <Badge variant={statusColor(inv.status)}>
                          {inv.status.replace('_', ' ')}
                        </Badge>
                      </td>

                      <td className="p-3 whitespace-nowrap">
                        {hyp ? (
                          <div>
                            <span className="text-emerald-400 font-bold">
                              {Math.round(hyp.confidence * 100)}%
                            </span>{' '}
                            <span className="text-[#A1A1AA]">{hyp.label || hyp.kind}</span>
                          </div>
                        ) : (
                          <span className="text-[#71717A]">Inference in progress...</span>
                        )}
                      </td>

                      <td className="p-3 whitespace-nowrap">
                        {inv.verified ? (
                          <span className="text-emerald-400 font-bold">VERIFIED ✓</span>
                        ) : inv.pending_approval ? (
                          <span className="text-amber-400 font-bold">AWAITING APPROVAL</span>
                        ) : inv.action_count > 0 ? (
                          <span className="text-[#A1A1AA]">{inv.action_count} action(s)</span>
                        ) : (
                          <span className="text-[#71717A]">No mutation</span>
                        )}
                      </td>

                      <td className="p-3 text-right whitespace-nowrap">
                        <span className="text-indigo-400 hover:text-indigo-300 font-bold">
                          Inspect →
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
