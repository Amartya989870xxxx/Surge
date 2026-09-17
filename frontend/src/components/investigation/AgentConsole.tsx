import React, { useState, useEffect, useRef } from 'react';
import type { EventOut, ActionOut, InvestigationDetailOut } from '../../types/api';
import {
  getInvestigation,
  getInvestigationActions,
  approveAction,
} from '../../lib/api/investigations';
import { InvestigationStream, type StreamStatus } from '../../lib/sse/investigationStream';
import { SourceIcon } from '../ui/SourceIcon';
import { StatusDot } from '../ui/StatusDot';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { WorkspaceFaviconButton } from '../ui/WorkspaceFaviconButton';

export type NodeId = 'orchestrator' | 'sheets' | 'github' | 'slack' | 'hypothesis' | 'action';

interface AgentConsoleProps {
  investigationId: string;
  onComplete: (investigationId: string) => void;
  onBackToDashboard: () => void;
}

interface NodeMeta {
  id: NodeId;
  name: string;
  role: string;
  categoryLabel: string;
  app: 'surge' | 'sheets' | 'github' | 'slack' | 'hypothesis' | 'action';
}

interface NodeActivityState {
  isWorking: boolean;
  flash: 'succeeded' | 'failed' | null;
  flashTimestamp: number;
}

interface EdgeActivityState {
  pulse: 'forward' | 'reverse' | null;
  status: 'working' | 'succeeded' | 'failed' | null;
  pulseKey: number;
}

const NODES: NodeMeta[] = [
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    role: 'Supervisor · Plan, System & Synthesis',
    categoryLabel: 'PLAN, SYSTEM, POLICY, SUFFICIENCY_CHECK',
    app: 'surge',
  },
  {
    id: 'sheets',
    name: 'Sheets Agent',
    role: 'Funnel metrics & checkout anomalies',
    categoryLabel: 'TOOL_CALL, EVIDENCE, DEGRADED',
    app: 'sheets',
  },
  {
    id: 'github',
    name: 'GitHub Agent',
    role: 'Deployments, commit diffs & issues',
    categoryLabel: 'TOOL_CALL, EVIDENCE, DEGRADED',
    app: 'github',
  },
  {
    id: 'slack',
    name: 'Slack Agent',
    role: 'Incident alerts & support channel signals',
    categoryLabel: 'TOOL_CALL, EVIDENCE, DEGRADED',
    app: 'slack',
  },
  {
    id: 'hypothesis',
    name: 'Hypothesis Engine',
    role: 'Evidence reasoning & candidate ranking',
    categoryLabel: 'HYPOTHESIS, HYPOTHESES_GENERATED',
    app: 'hypothesis',
  },
  {
    id: 'action',
    name: 'Action & Verification',
    role: 'Mitigation, execution & verification',
    categoryLabel: 'ACTION_*, APPROVAL_REQUIRED, VERIFICATION, SYNTHESIS',
    app: 'action',
  },
];

// Node outline icons for Hypothesis and Action
const HypothesisIcon: React.FC<{ size?: number; className?: string }> = ({ size = 16, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={`inline-block ${className}`}
  >
    <circle cx="7" cy="7" r="3" stroke="#A78BFA" strokeWidth="1.5" />
    <circle cx="7" cy="17" r="3" stroke="#A78BFA" strokeWidth="1.5" />
    <circle cx="17" cy="12" r="3" stroke="#A78BFA" strokeWidth="1.5" />
    <path d="M10 7H12L14 10" stroke="#A78BFA" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M10 17H12L14 14" stroke="#A78BFA" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

const ActionIcon: React.FC<{ size?: number; className?: string }> = ({ size = 16, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={`inline-block ${className}`}
  >
    <path
      d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
      stroke="#10B981"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M9 12l2 2 4-4"
      stroke="#10B981"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

function getNodeForEvent(e: EventOut): NodeId {
  const cat = (e.category || '').toUpperCase();
  const type = (e.event_type || '').toUpperCase();
  const app = (e.external_app || '').toLowerCase();
  const tool = (e.tool_name || '').toLowerCase();

  // Specialist apps
  if (app === 'sheets' || cat === 'SHEETS' || tool.includes('sheet')) {
    return 'sheets';
  }
  if (app === 'github' || cat === 'GITHUB' || tool.includes('git')) {
    return 'github';
  }
  if (app === 'slack' || cat === 'SLACK' || tool.includes('slack')) {
    return 'slack';
  }

  // Hypothesis Engine
  if (
    type === 'HYPOTHESES_GENERATED' ||
    type.startsWith('HYPOTHESIS') ||
    cat === 'HYPOTHESIS'
  ) {
    return 'hypothesis';
  }

  // Action & Verification
  if (
    type.startsWith('ACTION') ||
    type === 'APPROVAL_REQUIRED' ||
    type === 'VERIFICATION' ||
    type === 'SYNTHESIS' ||
    cat === 'ACTION' ||
    cat === 'VERIFICATION' ||
    cat === 'SYNTHESIS'
  ) {
    return 'action';
  }

  // Orchestrator: PLAN, SYSTEM, POLICY, SUFFICIENCY_CHECK and defaults
  return 'orchestrator';
}

export const AgentConsole: React.FC<AgentConsoleProps> = ({
  investigationId,
  onComplete,
  onBackToDashboard,
}) => {
  const [investigation, setInvestigation] = useState<InvestigationDetailOut | null>(null);
  const [events, setEvents] = useState<EventOut[]>([]);
  const [actions, setActions] = useState<ActionOut[]>([]);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('connecting');
  const [isFinished, setIsFinished] = useState(false);
  const [approvingActionId, setApprovingActionId] = useState<string | null>(null);
  const [approvalComment, setApprovalComment] = useState('');

  // Selected node for slide-in detail panel
  const [selectedNodeId, setSelectedNodeId] = useState<NodeId | null>(null);
  const [detailFilter, setDetailFilter] = useState<'node' | 'all'>('node');

  // State-driven animation activity tracking for each node and connecting edge
  const [nodeStates, setNodeStates] = useState<Record<NodeId, NodeActivityState>>({
    orchestrator: { isWorking: false, flash: null, flashTimestamp: 0 },
    sheets: { isWorking: false, flash: null, flashTimestamp: 0 },
    github: { isWorking: false, flash: null, flashTimestamp: 0 },
    slack: { isWorking: false, flash: null, flashTimestamp: 0 },
    hypothesis: { isWorking: false, flash: null, flashTimestamp: 0 },
    action: { isWorking: false, flash: null, flashTimestamp: 0 },
  });

  const [edgeStates, setEdgeStates] = useState<Record<NodeId, EdgeActivityState>>({
    orchestrator: { pulse: null, status: null, pulseKey: 0 },
    sheets: { pulse: null, status: null, pulseKey: 0 },
    github: { pulse: null, status: null, pulseKey: 0 },
    slack: { pulse: null, status: null, pulseKey: 0 },
    hypothesis: { pulse: null, status: null, pulseKey: 0 },
    action: { pulse: null, status: null, pulseKey: 0 },
  });

  const streamRef = useRef<InvestigationStream | null>(null);
  const drawerListRef = useRef<HTMLDivElement>(null);
  const flashTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const fetchActions = async () => {
    try {
      const res = await getInvestigationActions(investigationId);
      setActions(res);
    } catch (err) {
      console.error('Failed to load actions:', err);
    }
  };

  const loadInvestigationDetails = async () => {
    try {
      const inv = await getInvestigation(investigationId);
      setInvestigation(inv);
      if (
        inv.status === 'COMPLETED' ||
        inv.status === 'FAILED' ||
        inv.status === 'CANCELLED' ||
        inv.status === 'PARTIAL'
      ) {
        setIsFinished(true);
      }
    } catch (err) {
      console.error('Failed to load investigation details:', err);
    }
  };

  useEffect(() => {
    loadInvestigationDetails();
    fetchActions();

    // Start SSE stream
    const stream = new InvestigationStream(investigationId, {
      onEvent: (event) => {
        setEvents((prev) => {
          if (prev.some((e) => e.sequence === event.sequence)) return prev;
          return [...prev, event];
        });

        // Determine destination node
        const targetNode = getNodeForEvent(event);
        const type = (event.event_type || '').toUpperCase();
        const status = (event.status || '').toLowerCase();

        const isStart =
          type.endsWith('_STARTED') ||
          type === 'ACTION_EXECUTING' ||
          type === 'PLAN' ||
          status === 'started' ||
          status === 'running';

        const isSuccess =
          type.endsWith('_SUCCEEDED') ||
          type === 'ACTION_EXECUTED' ||
          type === 'ACTION_APPROVED' ||
          type === 'HYPOTHESES_GENERATED' ||
          type === 'VERIFICATION' ||
          status === 'succeeded' ||
          status === 'completed';

        const isFailure =
          type.endsWith('_FAILED') ||
          type === 'ACTION_FAILED' ||
          type === 'ACTION_REJECTED' ||
          type === 'ACTION_BLOCKED' ||
          status === 'failed';

        const now = Date.now();

        if (isStart) {
          // Rule 1: Working breathing glow + traveling highlight in direction of call
          setNodeStates((prev) => ({
            ...prev,
            [targetNode]: { isWorking: true, flash: null, flashTimestamp: now },
          }));
          setEdgeStates((prev) => ({
            ...prev,
            [targetNode]: { pulse: 'forward', status: 'working', pulseKey: now },
          }));
        } else if (isSuccess || isFailure) {
          // Rule 2: Stop breathing glow immediately, flash green/red, settle over 400ms, pulse back toward Orchestrator
          const flashType = isSuccess ? 'succeeded' : 'failed';
          setNodeStates((prev) => ({
            ...prev,
            [targetNode]: { isWorking: false, flash: flashType, flashTimestamp: now },
          }));
          setEdgeStates((prev) => ({
            ...prev,
            [targetNode]: { pulse: 'reverse', status: flashType, pulseKey: now },
          }));

          // Clear previous timer for this node if any
          if (flashTimersRef.current[targetNode]) {
            clearTimeout(flashTimersRef.current[targetNode]);
          }

          // Settle flash back to neutral over 400ms
          flashTimersRef.current[targetNode] = setTimeout(() => {
            setNodeStates((prev) => ({
              ...prev,
              [targetNode]: { ...prev[targetNode], flash: null },
            }));
          }, 400);
        }

        // If action-related event, reload actions
        if (
          event.event_type === 'ACTION_PROPOSED' ||
          event.event_type === 'APPROVAL_REQUIRED' ||
          event.event_type === 'ACTION_EXECUTED' ||
          event.event_type === 'VERIFICATION' ||
          event.action_id
        ) {
          fetchActions();
        }

        // Check if finished
        if (
          event.event_type === 'COMPLETED' ||
          event.event_type === 'FAILED' ||
          event.event_type === 'CANCELLED' ||
          event.status === 'completed' ||
          event.status === 'failed'
        ) {
          setIsFinished(true);
        }
      },
      onStatusChange: (status) => {
        setStreamStatus(status);
        if (status === 'ended') {
          setIsFinished(true);
        }
      },
    });

    streamRef.current = stream;

    return () => {
      stream.close();
      Object.values(flashTimersRef.current).forEach(clearTimeout);
    };
  }, [investigationId]);

  // Auto-scroll detail panel when open and new event arrives
  useEffect(() => {
    if (selectedNodeId && drawerListRef.current) {
      drawerListRef.current.scrollTop = drawerListRef.current.scrollHeight;
    }
  }, [events.length, selectedNodeId]);

  const handleApprove = async (actionId: string, approved: boolean) => {
    setApprovingActionId(actionId);
    try {
      await approveAction(investigationId, {
        action_id: actionId,
        approved,
        comment: approvalComment.trim() || undefined,
      });
      await fetchActions();
      setApprovalComment('');
    } catch (err: any) {
      console.error('Failed to approve/reject action:', err);
    } finally {
      setApprovingActionId(null);
    }
  };

  // Pending action requiring human approval
  const pendingAction = actions.find(
    (a) => a.approval_required && a.approval_status === 'PENDING'
  );

  // Group events by node
  const getEventsForNode = (nodeId: NodeId) => {
    return events.filter((e) => getNodeForEvent(e) === nodeId);
  };

  // Events to show in drawer
  const drawerEvents =
    detailFilter === 'all' || !selectedNodeId
      ? events
      : getEventsForNode(selectedNodeId);

  const selectedNodeMeta = NODES.find((n) => n.id === selectedNodeId);

  // Render node icon helper
  const renderNodeIcon = (type: NodeMeta['app'], size = 16) => {
    if (type === 'hypothesis') return <HypothesisIcon size={size} />;
    if (type === 'action') return <ActionIcon size={size} />;
    return <SourceIcon app={type} size={size} />;
  };

  // Render an individual agent node box
  const renderNode = (
    nodeId: NodeId,
    style: React.CSSProperties,
    alignClass = ''
  ) => {
    const meta = NODES.find((n) => n.id === nodeId)!;
    const nodeEvents = getEventsForNode(nodeId);
    const count = nodeEvents.length;
    const { isWorking, flash } = nodeStates[nodeId];
    const isSelected = selectedNodeId === nodeId;

    // Rule 3: Zero events so far stays fully neutral/dim
    const isZero = count === 0;

    let borderClass = 'border-[#1A1A1F]';
    let textClass = 'text-[#F5F5F5]';
    let bgClass = 'bg-[#0A0A0C]';

    if (isZero) {
      borderClass = 'border-[#16161B]';
      textClass = 'text-[#71717A]';
      bgClass = 'bg-[#070709] opacity-45';
    } else if (isWorking) {
      borderClass = 'border-indigo-500 agent-node-working';
      textClass = 'text-[#F5F5F5]';
      bgClass = 'bg-[#0B0B10]';
    } else if (flash === 'succeeded') {
      borderClass = 'border-emerald-500 text-emerald-300';
      bgClass = 'bg-emerald-950/20';
    } else if (flash === 'failed') {
      borderClass = 'border-rose-500 text-rose-300';
      bgClass = 'bg-rose-950/20';
    }

    if (isSelected) {
      borderClass = `${borderClass} ring-1 ring-indigo-500/80 border-indigo-400`;
    }

    return (
      <div
        style={style}
        onClick={() => setSelectedNodeId((curr) => (curr === nodeId ? null : nodeId))}
        className={`absolute rounded-lg border p-3 font-mono cursor-pointer transition-all duration-300 select-none ${borderClass} ${bgClass} ${textClass} ${alignClass} hover:border-[#2D2D38]`}
      >
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-2 min-w-0">
            {renderNodeIcon(meta.app, 15)}
            <span className="font-bold text-xs truncate">{meta.name}</span>
            {isWorking && (
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping shrink-0" />
            )}
          </div>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${
              isZero
                ? 'bg-[#0E0E12] border-[#18181E] text-[#52525B]'
                : isWorking
                ? 'bg-indigo-950/60 border-indigo-800/80 text-indigo-300 font-bold'
                : 'bg-[#111114] border-[#1E1E24] text-[#A1A1AA]'
            }`}
          >
            {count}
          </span>
        </div>
        <div className="text-[10px] text-[#71717A] truncate">
          {meta.role}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-mono text-xs flex flex-col antialiased">
      {/* Top Left Workspace Favicon Link */}
      <WorkspaceFaviconButton onNavigateWorkspace={onBackToDashboard} />

      {/* Floating Top Right Quick Actions */}
      <div className="fixed top-4 right-6 z-30 flex items-center gap-2.5">
        {/* Real stream status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/70 backdrop-blur-xl border border-white/10 text-[11px] text-[#A1A1AA] shadow-lg">
          <StatusDot
            status={
              isFinished
                ? 'success'
                : streamStatus === 'connected'
                ? 'info'
                : streamStatus === 'reconnecting'
                ? 'warning'
                : 'neutral'
            }
            pulse={!isFinished && streamStatus === 'connected'}
            size="sm"
          />
          <span className="uppercase text-[10px] tracking-wider font-semibold">
            {isFinished ? 'Complete' : streamStatus}
          </span>
        </div>

        {/* Toggle Detail Drawer button */}
        <button
          onClick={() => {
            if (selectedNodeId) {
              setSelectedNodeId(null);
            } else {
              setSelectedNodeId('orchestrator');
              setDetailFilter('all');
            }
          }}
          className="px-3 py-1.5 rounded-full bg-black/70 backdrop-blur-xl border border-white/10 hover:border-white/25 text-[11px] text-[#A1A1AA] hover:text-white transition-colors cursor-pointer flex items-center gap-1.5 shadow-lg"
        >
          <span>{selectedNodeId ? 'Hide Drawer' : 'View Event Log'}</span>
          <span className="text-[10px] text-[#71717A]">({events.length})</span>
        </button>

        {/* View Report Button */}
        {isFinished && (
          <Button
            size="sm"
            variant="primary"
            onClick={() => onComplete(investigationId)}
            className="font-bold text-xs flex items-center gap-1.5 rounded-full px-3.5 py-1.5 shadow-xl animate-pulse"
          >
            <span>View Final Report</span> →
          </Button>
        )}
      </div>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden relative pt-12">
        {/* Main Graph Area */}
        <div className="flex-1 flex flex-col p-6 overflow-y-auto overflow-x-hidden">
          {/* Banner if finished */}
          {isFinished && (
            <div className="mb-4 p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 text-emerald-300 text-xs">
                <StatusDot status="success" size="sm" />
                <span>
                  <strong>Investigation complete.</strong> Verified root-cause and claims ready for review.
                </span>
              </div>
              <Button
                size="sm"
                variant="primary"
                onClick={() => onComplete(investigationId)}
                className="text-xs"
              >
                Read Final Report →
              </Button>
            </div>
          )}

          {/* Human Approval Card (Non-negotiable requirement: Must not auto-approve) */}
          {pendingAction && (
            <div className="mb-5 p-4 bg-[#0E0C08] border border-amber-500/60 rounded-xl shadow-2xl shrink-0 animate-in fade-in duration-300">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-amber-500/20">
                <div className="flex items-center gap-2">
                  <StatusDot status="warning" pulse size="md" />
                  <span className="font-bold text-amber-400 text-xs uppercase tracking-wider">
                    Human Approval Required
                  </span>
                  <Badge variant="warning">RISK: {pendingAction.risk_level}</Badge>
                </div>
                <span className="text-[10px] text-[#71717A] font-mono">
                  id: {pendingAction.id}
                </span>
              </div>

              <div className="mb-3">
                <div className="text-sm font-bold text-[#F5F5F5] mb-1">
                  {pendingAction.title}
                </div>
                <div className="text-xs text-[#A1A1AA] leading-relaxed">
                  {pendingAction.rationale}
                </div>
              </div>

              {pendingAction.preview && Object.keys(pendingAction.preview).length > 0 && (
                <div className="mb-3 p-2.5 bg-[#000000] border border-[#222228] rounded font-mono text-[11px] text-[#A1A1AA] max-h-32 overflow-y-auto">
                  {pendingAction.preview.title && (
                    <div className="font-semibold text-[#F5F5F5] mb-1">
                      Title: {pendingAction.preview.title}
                    </div>
                  )}
                  {pendingAction.preview.body && (
                    <div className="text-[#888894] whitespace-pre-wrap">
                      {pendingAction.preview.body}
                    </div>
                  )}
                </div>
              )}

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                <input
                  type="text"
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  placeholder="Optional approval note or condition..."
                  className="w-full sm:w-80 px-3 py-1.5 bg-[#000000] border border-[#2A2A35] rounded text-xs text-[#F5F5F5] focus:outline-none focus:border-amber-500"
                />

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleApprove(pendingAction.id, false)}
                    loading={approvingActionId === pendingAction.id}
                  >
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    variant="success"
                    onClick={() => handleApprove(pendingAction.id, true)}
                    loading={approvingActionId === pendingAction.id}
                  >
                    Approve & Execute →
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Hub-and-Spoke Multi-Agent Graph Container */}
          <div className="flex-1 flex flex-col justify-center items-center min-h-[460px] relative py-2">
            <div className="w-full max-w-[860px] h-[440px] relative overflow-visible">
              {/* SVG Connecting Paths & Edge Highlight Pulses */}
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none"
                viewBox="0 0 860 440"
                preserveAspectRatio="none"
              >
                <defs>
                  <marker
                    id="arrow-neutral"
                    viewBox="0 0 10 10"
                    refX="7"
                    refY="5"
                    markerWidth="5"
                    markerHeight="5"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#2E2E36" />
                  </marker>
                  <marker
                    id="arrow-accent"
                    viewBox="0 0 10 10"
                    refX="7"
                    refY="5"
                    markerWidth="5"
                    markerHeight="5"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#818CF8" />
                  </marker>
                </defs>

                {/* 1. Path: User Query -> Orchestrator */}
                <path d="M 430 42 V 70" stroke="#1E1E24" strokeWidth="1.5" fill="none" />

                {/* 2. Paths: Orchestrator -> 3 Specialists (Sheets, GitHub, Slack) */}
                {/* Orchestrator -> GitHub */}
                <path d="M 430 122 V 190" stroke="#1E1E24" strokeWidth="1.5" fill="none" />
                {edgeStates.github.pulse && (
                  <path
                    key={`edge-github-${edgeStates.github.pulseKey}`}
                    d="M 430 122 V 190"
                    pathLength="100"
                    stroke={edgeStates.github.status === 'failed' ? '#EF4444' : edgeStates.github.status === 'succeeded' ? '#10B981' : '#818CF8'}
                    strokeWidth="2"
                    fill="none"
                    className={edgeStates.github.pulse === 'forward' ? 'edge-pulse-forward' : 'edge-pulse-reverse'}
                  />
                )}

                {/* Orchestrator -> Sheets */}
                <path
                  d="M 430 122 V 156 Q 430 166 420 166 H 155 Q 145 166 145 176 V 190"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                />
                {edgeStates.sheets.pulse && (
                  <path
                    key={`edge-sheets-${edgeStates.sheets.pulseKey}`}
                    d="M 430 122 V 156 Q 430 166 420 166 H 155 Q 145 166 145 176 V 190"
                    pathLength="100"
                    stroke={edgeStates.sheets.status === 'failed' ? '#EF4444' : edgeStates.sheets.status === 'succeeded' ? '#10B981' : '#818CF8'}
                    strokeWidth="2"
                    fill="none"
                    className={edgeStates.sheets.pulse === 'forward' ? 'edge-pulse-forward' : 'edge-pulse-reverse'}
                  />
                )}

                {/* Orchestrator -> Slack */}
                <path
                  d="M 430 122 V 156 Q 430 166 440 166 H 705 Q 715 166 715 176 V 190"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                />
                {edgeStates.slack.pulse && (
                  <path
                    key={`edge-slack-${edgeStates.slack.pulseKey}`}
                    d="M 430 122 V 156 Q 430 166 440 166 H 705 Q 715 166 715 176 V 190"
                    pathLength="100"
                    stroke={edgeStates.slack.status === 'failed' ? '#EF4444' : edgeStates.slack.status === 'succeeded' ? '#10B981' : '#818CF8'}
                    strokeWidth="2"
                    fill="none"
                    className={edgeStates.slack.pulse === 'forward' ? 'edge-pulse-forward' : 'edge-pulse-reverse'}
                  />
                )}

                {/* 3. Paths: 3 Specialists -> Convergence bus -> Hypothesis Engine */}
                <path
                  d="M 145 242 V 270 Q 145 280 155 280 H 300"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M 430 242 V 280 H 300"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M 715 242 V 270 Q 715 280 705 280 H 300"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M 300 280 V 320"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                />
                {edgeStates.hypothesis.pulse && (
                  <path
                    key={`edge-hypo-${edgeStates.hypothesis.pulseKey}`}
                    d="M 300 280 V 320"
                    pathLength="100"
                    stroke={edgeStates.hypothesis.status === 'failed' ? '#EF4444' : edgeStates.hypothesis.status === 'succeeded' ? '#10B981' : '#818CF8'}
                    strokeWidth="2"
                    fill="none"
                    className={edgeStates.hypothesis.pulse === 'forward' ? 'edge-pulse-forward' : 'edge-pulse-reverse'}
                  />
                )}

                {/* 4. Path: Hypothesis Engine -> Action & Verification (horizontal arrow) */}
                <path
                  d="M 410 346 H 448"
                  stroke="#1E1E24"
                  strokeWidth="1.5"
                  fill="none"
                  markerEnd={edgeStates.action.pulse ? 'url(#arrow-accent)' : 'url(#arrow-neutral)'}
                />
                {edgeStates.action.pulse && (
                  <path
                    key={`edge-action-${edgeStates.action.pulseKey}`}
                    d="M 410 346 H 448"
                    pathLength="100"
                    stroke={edgeStates.action.status === 'failed' ? '#EF4444' : edgeStates.action.status === 'succeeded' ? '#10B981' : '#818CF8'}
                    strokeWidth="2"
                    fill="none"
                    className={edgeStates.action.pulse === 'forward' ? 'edge-pulse-forward' : 'edge-pulse-reverse'}
                  />
                )}
              </svg>

              {/* Node: User query pill (Top Center) */}
              <div
                style={{ left: '50%', top: '12px', transform: 'translateX(-50%)', maxWidth: '380px' }}
                className="absolute flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0E0E12] border border-[#1E1E24] text-[11px] text-[#A1A1AA] truncate shadow-sm"
              >
                <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider">PROMPT</span>
                <span className="text-[#3F3F46]">/</span>
                <span className="truncate text-[#D4D4D8]">
                  {investigation?.request || investigation?.title || 'System Investigation Request'}
                </span>
              </div>

              {/* Tier 1 Node: Orchestrator (Top Center Hub) */}
              {renderNode(
                'orchestrator',
                { left: '50%', top: '70px', transform: 'translateX(-50%)', width: '240px' }
              )}

              {/* Tier 2 Nodes: Data Gathering Specialists (Left Branch) */}
              {/* Sheets Agent (Left) */}
              {renderNode(
                'sheets',
                { left: '45px', top: '190px', width: '200px' }
              )}

              {/* GitHub Agent (Center) */}
              {renderNode(
                'github',
                { left: '50%', top: '190px', transform: 'translateX(-50%)', width: '200px' }
              )}

              {/* Slack Agent (Right) */}
              {renderNode(
                'slack',
                { right: '45px', top: '190px', width: '200px' }
              )}

              {/* Tier 3 Nodes: Reasoning & Action Branch */}
              {/* Hypothesis Engine */}
              {renderNode(
                'hypothesis',
                { left: 'calc(50% - 240px)', top: '320px', width: '220px' }
              )}

              {/* Action & Verification */}
              {renderNode(
                'action',
                { left: 'calc(50% + 20px)', top: '320px', width: '220px' }
              )}
            </div>

            {/* Bottom Status & Hint */}
            <div className="mt-4 text-center text-[11px] text-[#52525B] flex items-center gap-3">
              <span>Click any agent node to open detailed telemetry & card events</span>
              <span className="text-[#27272A]">·</span>
              <span className="text-[#71717A]">{events.length} total events dispatched</span>
            </div>
          </div>
        </div>

        {/* Slide-in Secondary Detail Panel / Drawer */}
        {selectedNodeId && (
          <aside className="w-full sm:w-[420px] bg-[#070709] border-l border-[#1A1A1F] flex flex-col z-20 shrink-0 animate-in slide-in-from-right duration-300">
            {/* Drawer Header */}
            <div className="p-4 bg-[#0B0B0E] border-b border-[#1A1A1F] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2.5 min-w-0">
                {selectedNodeMeta && renderNodeIcon(selectedNodeMeta.app, 18)}
                <div className="min-w-0">
                  <div className="font-bold text-xs text-[#F5F5F5] truncate flex items-center gap-1.5">
                    <span>{selectedNodeMeta?.name}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#16161D] border border-[#24242E] text-[#A1A1AA]">
                      {drawerEvents.length}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#71717A] truncate">
                    {selectedNodeMeta?.role}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="w-7 h-7 rounded border border-[#22222A] bg-[#0E0E12] hover:bg-[#181820] text-[#71717A] hover:text-[#F5F5F5] flex items-center justify-center transition-colors cursor-pointer text-xs"
                  title="Close Detail View"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Filter Toggle: Current Node vs All Events */}
            <div className="px-4 py-2 bg-[#09090C] border-b border-[#18181C] flex items-center justify-between text-[11px] shrink-0">
              <div className="flex items-center gap-1 bg-[#000000] p-0.5 rounded border border-[#1E1E24]">
                <button
                  onClick={() => setDetailFilter('node')}
                  className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                    detailFilter === 'node'
                      ? 'bg-indigo-950/80 text-indigo-300 font-bold border border-indigo-800/60'
                      : 'text-[#71717A] hover:text-[#A1A1AA]'
                  }`}
                >
                  {selectedNodeMeta?.name} ({getEventsForNode(selectedNodeId).length})
                </button>
                <button
                  onClick={() => setDetailFilter('all')}
                  className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                    detailFilter === 'all'
                      ? 'bg-indigo-950/80 text-indigo-300 font-bold border border-indigo-800/60'
                      : 'text-[#71717A] hover:text-[#A1A1AA]'
                  }`}
                >
                  All Stream ({events.length})
                </button>
              </div>

              <span className="text-[10px] text-[#52525B]">
                Live SSE
              </span>
            </div>

            {/* Event Cards List */}
            <div ref={drawerListRef} className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
              {drawerEvents.length === 0 ? (
                <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-[#52525B] text-xs">
                  <div className="mb-2">No events recorded yet for this agent node.</div>
                  <div className="text-[10px] text-[#3F3F46]">
                    Listens for: {selectedNodeMeta?.categoryLabel}
                  </div>
                </div>
              ) : (
                drawerEvents.map((evt) => {
                  const isSuccess = evt.status === 'succeeded' || evt.status === 'completed';
                  const isFailure = evt.status === 'failed';

                  return (
                    <div
                      key={`${evt.sequence}-${evt.event_type}`}
                      className="p-3 bg-[#0C0C0F] border border-[#18181F] rounded-lg text-[11px] space-y-1.5 hover:border-[#282833] transition-colors"
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-[#71717A] font-mono flex items-center gap-1.5">
                          <StatusDot
                            status={isSuccess ? 'success' : isFailure ? 'danger' : 'info'}
                            size="sm"
                          />
                          #{evt.sequence} · {evt.event_type.replace(/_/g, ' ')}
                        </span>
                        {evt.duration_ms && (
                          <span className="text-[#52525B]">{evt.duration_ms}ms</span>
                        )}
                      </div>

                      {/* Step Title */}
                      <div className="font-semibold text-[#F5F5F5] leading-snug">
                        {evt.title}
                      </div>

                      {/* One-line Reasoning Summary */}
                      {evt.summary && (
                        <div className="text-[11px] text-[#A1A1AA] leading-relaxed">
                          {evt.summary}
                        </div>
                      )}

                      {/* Tool Name Badge */}
                      {evt.tool_name && (
                        <div className="pt-1 flex items-center gap-1 text-[10px] text-indigo-300">
                          <code className="bg-[#111116] px-1.5 py-0.5 rounded border border-[#1A1A22]">
                            {evt.tool_name}
                          </code>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
};
