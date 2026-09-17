import React, { useState } from 'react';
import type { ActionOut } from '../../types/api';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { SourceIcon } from '../ui/SourceIcon';

interface ActionApprovalCardProps {
  action: ActionOut;
  onDecide: (actionId: string, approved: boolean, comment?: string) => Promise<void>;
}

export const ActionApprovalCard: React.FC<ActionApprovalCardProps> = ({ action, onDecide }) => {
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isPendingApproval =
    action.approval_required && action.approval_status === 'PENDING';
  const isExecuting = action.execution_status === 'EXECUTING';
  const isVerifying = action.verification_status === 'VERIFYING';
  const isVerified = action.verification_status === 'VERIFIED';

  const handleDecision = async (approved: boolean) => {
    setSubmitting(true);
    try {
      await onDecide(action.id, approved, comment.trim() || undefined);
    } finally {
      setSubmitting(false);
    }
  };

  const riskVariant = {
    LOW: 'verified' as const,
    MEDIUM: 'warning' as const,
    HIGH: 'danger' as const,
  }[action.risk_level] || 'neutral';

  return (
    <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg shadow-lg">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-3 border-b border-[#1A1A1F]">
        <div className="flex items-center gap-2">
          <SourceIcon app={action.external_app} size={16} />
          <span className="font-mono text-xs font-bold text-[#F5F5F5] uppercase">
            Action: {action.action_type.replace(/_/g, ' ')}
          </span>
          <Badge variant={riskVariant}>RISK: {action.risk_level}</Badge>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px] text-[#71717A]">
          <span>id: {action.id}</span>
          <span>·</span>
          <span>key: {action.idempotency_key}</span>
        </div>
      </div>

      {/* Target & Title */}
      <div className="mb-3">
        <div className="text-xs font-mono text-[#71717A] mb-1">Target: {action.target}</div>
        <div className="font-mono text-sm font-semibold text-[#F5F5F5]">{action.title}</div>
      </div>

      {/* Rationale */}
      <div className="text-xs text-[#A1A1AA] leading-relaxed mb-4 font-mono">
        <span className="text-[#71717A]">Reason: </span>
        {action.rationale}
      </div>

      {/* Payload Preview */}
      {action.preview && Object.keys(action.preview).length > 0 && (
        <div className="mb-4">
          <div className="text-[11px] font-mono text-[#71717A] uppercase mb-1">
            Action Payload Preview
          </div>
          <pre className="p-2.5 bg-[#050505] rounded border border-[#1A1A1F] text-[11px] text-[#A1A1AA] font-mono overflow-x-auto max-h-36">
            {JSON.stringify(action.preview, null, 2)}
          </pre>
        </div>
      )}

      {/* Four-Stage Lifecycle Visualizer */}
      <div className="grid grid-cols-4 gap-2 py-3 px-2 bg-[#111114] border border-[#1A1A1F] rounded mb-4 font-mono text-[11px]">
        {/* Stage 1: Approval */}
        <div className="text-center">
          <div className="text-[#71717A] text-[10px] uppercase">1. APPROVAL</div>
          <div
            className={`font-bold mt-0.5 ${
              action.approval_status === 'APPROVED'
                ? 'text-emerald-400'
                : action.approval_status === 'REJECTED'
                ? 'text-red-400'
                : 'text-amber-400'
            }`}
          >
            {action.approval_status}
          </div>
        </div>

        {/* Stage 2: Execution */}
        <div className="text-center">
          <div className="text-[#71717A] text-[10px] uppercase">2. EXECUTION</div>
          <div
            className={`font-bold mt-0.5 ${
              action.execution_status === 'SUCCEEDED'
                ? 'text-emerald-400'
                : action.execution_status === 'EXECUTING'
                ? 'text-indigo-400'
                : action.execution_status === 'FAILED'
                ? 'text-red-400'
                : 'text-[#71717A]'
            }`}
          >
            {action.execution_status}
          </div>
        </div>

        {/* Stage 3: Read-back */}
        <div className="text-center">
          <div className="text-[#71717A] text-[10px] uppercase">3. READ BACK</div>
          <div
            className={`font-bold mt-0.5 ${
              action.verification ? 'text-emerald-400' : 'text-[#71717A]'
            }`}
          >
            {action.verification ? 'COMPLETED' : isExecuting ? 'WAITING' : 'PENDING'}
          </div>
        </div>

        {/* Stage 4: Verification */}
        <div className="text-center">
          <div className="text-[#71717A] text-[10px] uppercase">4. VERIFICATION</div>
          <div
            className={`font-bold mt-0.5 ${
              isVerified
                ? 'text-emerald-400'
                : action.verification_status === 'FAILED'
                ? 'text-red-400'
                : isVerifying
                ? 'text-indigo-400'
                : 'text-[#71717A]'
            }`}
          >
            {action.verification_status}
          </div>
        </div>
      </div>

      {/* External URL if created */}
      {action.external_url && (
        <div className="mb-4 text-xs font-mono">
          <span className="text-[#71717A]">Created resource: </span>
          <a
            href={action.external_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-400 hover:text-indigo-300 underline"
          >
            {action.external_url}
          </a>
        </div>
      )}

      {/* Interactive Approval Gate */}
      {isPendingApproval && (
        <div className="pt-3 border-t border-[#1A1A1F] flex flex-col sm:flex-row items-center justify-between gap-3">
          <input
            type="text"
            placeholder="Optional decision comment..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={submitting}
            className="w-full sm:w-80 px-3 py-1.5 text-xs font-mono bg-[#050505] border border-[#24242B] rounded text-[#F5F5F5] placeholder-[#71717A] focus:outline-none focus:border-indigo-500"
          />

          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="danger"
              onClick={() => handleDecision(false)}
              loading={submitting}
              className="font-mono text-xs"
            >
              Reject Action
            </Button>
            <Button
              size="sm"
              variant="success"
              onClick={() => handleDecision(true)}
              loading={submitting}
              className="font-mono text-xs"
            >
              Approve & Execute →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
