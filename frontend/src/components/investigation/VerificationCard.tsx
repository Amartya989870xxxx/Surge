import React, { useState } from 'react';
import type { VerificationOut } from '../../types/api';
import { Badge } from '../ui/Badge';

interface VerificationCardProps {
  verification: VerificationOut;
}

export const VerificationCard: React.FC<VerificationCardProps> = ({ verification }) => {
  const [showRaw, setShowRaw] = useState(false);
  const isPassed = verification.result === 'passed';

  return (
    <div
      className={`p-4 rounded-lg border ${
        isPassed
          ? 'bg-emerald-950/15 border-emerald-800/60'
          : 'bg-red-950/20 border-red-800/60'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-3 pb-2 border-b border-[#1A1A1F]">
        <div className="flex items-center gap-2">
          <span
            className={`font-mono text-xs font-bold uppercase ${
              isPassed ? 'text-emerald-400' : 'text-red-400'
            }`}
          >
            Independent Provider Verification
          </span>
          <Badge variant={isPassed ? 'verified' : 'danger'}>
            {verification.result.toUpperCase()}
          </Badge>
        </div>

        <span className="text-[11px] font-mono text-[#71717A]">
          confidence: {Math.round(verification.confidence * 100)}%
        </span>
      </div>

      <p className="text-xs font-mono text-[#A1A1AA] mb-4">
        {isPassed
          ? 'Surge read back the provider state and independently verified that the intended modification exists without duplication.'
          : 'Provider state validation failed. Observed state does not match expectations.'}
      </p>

      {/* Verification Checks Grid */}
      {verification.checks?.length > 0 && (
        <div className="space-y-1.5 mb-4 font-mono text-xs">
          {verification.checks.map((c, i) => (
            <div
              key={i}
              className="flex items-center justify-between p-2 bg-[#050505] rounded border border-[#1A1A1F]"
            >
              <div className="flex items-center gap-2">
                <span className={c.passed ? 'text-emerald-400' : 'text-red-400'}>
                  {c.passed ? '✓' : '✗'}
                </span>
                <span className="text-[#F5F5F5]">{c.field}</span>
              </div>
              <span className={`text-[11px] ${c.passed ? 'text-emerald-400' : 'text-red-400'}`}>
                {c.message || (c.passed ? 'MATCH' : 'MISMATCH')}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* State Toggle */}
      <div className="pt-2 flex items-center justify-between text-[11px] font-mono text-[#71717A]">
        <span>method: {verification.method}</span>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
        >
          {showRaw ? 'Hide Raw Diff' : 'View Expected vs Observed State'}
        </button>
      </div>

      {showRaw && (
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-[#1A1A1F] font-mono text-[11px]">
          <div>
            <div className="text-[#71717A] mb-1 uppercase">Expected State</div>
            <pre className="p-2 bg-[#050505] rounded border border-[#1A1A1F] text-[#A1A1AA] overflow-x-auto max-h-36">
              {JSON.stringify(verification.expected_state, null, 2)}
            </pre>
          </div>
          <div>
            <div className="text-[#71717A] mb-1 uppercase">Observed State (Read-Back)</div>
            <pre className="p-2 bg-[#050505] rounded border border-[#1A1A1F] text-[#A1A1AA] overflow-x-auto max-h-36">
              {JSON.stringify(verification.observed_state, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
