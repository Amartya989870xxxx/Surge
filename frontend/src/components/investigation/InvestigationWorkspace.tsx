import React, { useState, useEffect, useCallback, useRef } from 'react';
import type {
  InvestigationDetailOut,
  EventOut,
  EvidenceOut,
  HypothesisOut,
  ActionOut,
  ClaimOut,
} from '../../types/api';
import {
  getInvestigation,
  getInvestigationEvents,
  getInvestigationEvidence,
  getInvestigationHypotheses,
  getInvestigationActions,
  getInvestigationClaims,
  approveAction,
  cancelInvestigation,
  rerunInvestigation,
} from '../../lib/api/investigations';
import { InvestigationStream, type StreamStatus } from '../../lib/sse/investigationStream';
import { InvestigationHeader } from './InvestigationHeader';
import { EventTimeline } from './EventTimeline';
import { EvidenceCanvas } from './EvidenceCanvas';
import { EvidencePanel } from './EvidencePanel';
import { HypothesisPanel } from './HypothesisPanel';
import { ActionApprovalCard } from './ActionApprovalCard';
import { VerificationCard } from './VerificationCard';
import { DegradedNotice } from './DegradedNotice';

interface InvestigationWorkspaceProps {
  investigationId: string;
  onNavigateToNew?: (id: string) => void;
  onBackToOverview?: () => void;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  investigationId,
  onNavigateToNew,
  onBackToOverview,
}) => {
  const [investigation, setInvestigation] = useState<InvestigationDetailOut | null>(null);
  const [events, setEvents] = useState<EventOut[]>([]);
  const [evidence, setEvidence] = useState<EvidenceOut[]>([]);
  const [hypotheses, setHypotheses] = useState<HypothesisOut[]>([]);
  const [actions, setActions] = useState<ActionOut[]>([]);
  const [claims, setClaims] = useState<ClaimOut[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('connecting');

  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>();
  const [selectedHypothesisId, setSelectedHypothesisId] = useState<string | undefined>();
  const [cancelling, setCancelling] = useState(false);
  const [rerunning, setRerunning] = useState(false);

  const streamRef = useRef<InvestigationStream | null>(null);

  // Load initial investigation data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [inv, evts, evd, hyps, acts, clms] = await Promise.all([
        getInvestigation(investigationId),
        getInvestigationEvents(investigationId, 0),
        getInvestigationEvidence(investigationId),
        getInvestigationHypotheses(investigationId),
        getInvestigationActions(investigationId),
        getInvestigationClaims(investigationId),
      ]);

      setInvestigation(inv);
      setEvents(evts);
      setEvidence(evd);
      setHypotheses(hyps);
      setActions(acts);
      setClaims(clms);
    } catch (err: any) {
      setError(err.message || 'Failed to load investigation');
    } finally {
      setLoading(false);
    }
  }, [investigationId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Connect to SSE stream
  useEffect(() => {
    if (!investigationId) return;

    const stream = new InvestigationStream(
      investigationId,
      {
        onEvent: (event: EventOut) => {
          setEvents((prev) => {
            // Avoid duplicates
            if (prev.some((e) => e.sequence === event.sequence)) return prev;
            return [...prev, event];
          });

          // Refresh structured entities upon key milestones
          if (
            ['EVIDENCE', 'ANOMALY'].includes(event.event_type) ||
            event.category === 'EVIDENCE'
          ) {
            getInvestigationEvidence(investigationId).then(setEvidence).catch(() => {});
          }
          if (
            ['HYPOTHESIS_UPDATED', 'HYPOTHESES_GENERATED', 'SYNTHESIS'].includes(
              event.event_type
            ) ||
            event.category === 'HYPOTHESIS'
          ) {
            getInvestigationHypotheses(investigationId).then(setHypotheses).catch(() => {});
          }
          if (
            ['ACTION_PROPOSED', 'ACTION_DECIDED', 'ACTION_EXECUTED', 'ACTION_VERIFIED'].includes(
              event.event_type
            ) ||
            event.category === 'ACTION' ||
            event.category === 'VERIFICATION'
          ) {
            getInvestigationActions(investigationId).then(setActions).catch(() => {});
          }
          if (
            ['STATUS_CHANGED', 'COMPLETED', 'FAILED', 'CANCELLED'].includes(event.event_type)
          ) {
            getInvestigation(investigationId).then(setInvestigation).catch(() => {});
          }
        },
        onStatusChange: (status) => {
          setStreamStatus(status);
        },
      },
      events.length > 0 ? events[events.length - 1].sequence : 0
    );

    streamRef.current = stream;

    return () => {
      stream.close();
      streamRef.current = null;
    };
  }, [investigationId]);

  const handleDecideAction = async (actionId: string, approved: boolean, comment?: string) => {
    const updated = await approveAction(investigationId, {
      action_id: actionId,
      approved,
      comment,
      decided_by: 'user',
    });
    setActions((prev) => prev.map((a) => (a.id === actionId ? updated : a)));
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelInvestigation(investigationId);
      loadData();
    } finally {
      setCancelling(false);
    }
  };

  const handleRerun = async () => {
    setRerunning(true);
    try {
      const res = await rerunInvestigation(investigationId);
      if (onNavigateToNew) {
        onNavigateToNew(res.id);
      } else {
        window.location.hash = `#/app/investigations/${res.id}`;
      }
    } finally {
      setRerunning(false);
    }
  };

  if (loading && !investigation) {
    return (
      <div className="flex-1 flex items-center justify-center p-12 text-xs font-mono text-[#71717A]">
        Connecting to investigation {investigationId}...
      </div>
    );
  }

  if (error || !investigation) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center font-mono">
        <div className="text-red-400 text-sm font-bold mb-2">Investigation Error</div>
        <p className="text-xs text-[#A1A1AA] mb-4">{error || 'Investigation not found'}</p>
        <button
          onClick={onBackToOverview}
          className="text-xs text-indigo-400 hover:underline"
        >
          ← Back to Overview
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#050505] text-[#F5F5F5] overflow-hidden">
      {/* Top Header */}
      <InvestigationHeader
        investigation={investigation}
        onCancel={handleCancel}
        onRerun={handleRerun}
        cancelling={cancelling}
        rerunning={rerunning}
      />

      {/* Main 3-Column / Grid Workspace */}
      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-3 p-3">
        {/* Left Column: Live Event Stream */}
        <div className="lg:col-span-3 h-[400px] lg:h-full overflow-hidden">
          <EventTimeline events={events} streamStatus={streamStatus} />
        </div>

        {/* Center Column: Interactive Canvas & Actions */}
        <div className="lg:col-span-5 h-full overflow-y-auto space-y-3 flex flex-col">
          {/* Degraded Notice if connectors failed */}
          {investigation.degraded && (
            <DegradedNotice missingSources={investigation.missing_sources} />
          )}

          {/* Central Correlation Canvas */}
          <div className="flex-1 min-h-[360px]">
            <EvidenceCanvas
              evidence={evidence}
              hypotheses={hypotheses}
              actions={actions}
              claims={claims}
              selectedEvidenceId={selectedEvidenceId}
              selectedHypothesisId={selectedHypothesisId}
              onSelectEvidence={(id) => setSelectedEvidenceId(id)}
              onSelectHypothesis={(id) => setSelectedHypothesisId(id)}
            />
          </div>

          {/* Actions & Verification Section */}
          {actions.map((action) => (
            <div key={action.id} className="space-y-3">
              <ActionApprovalCard action={action} onDecide={handleDecideAction} />
              {action.verification && <VerificationCard verification={action.verification} />}
            </div>
          ))}
        </div>

        {/* Right Column: Competing Hypotheses & Evidence Corpus */}
        <div className="lg:col-span-4 h-full overflow-hidden flex flex-col gap-3">
          <div className="h-1/2 overflow-hidden">
            <HypothesisPanel
              hypotheses={hypotheses}
              selectedId={selectedHypothesisId}
              onSelect={(id) => setSelectedHypothesisId(id)}
            />
          </div>
          <div className="h-1/2 overflow-hidden">
            <EvidencePanel
              evidence={evidence}
              selectedId={selectedEvidenceId}
              onSelect={(id) => setSelectedEvidenceId(id)}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
