import React, { useState, useEffect } from 'react';
import type { SystemInfo } from '../../types/api';
import { getSystem, getHealth } from '../../lib/api/system';
import { getLocalSession, clearLocalSession } from '../../lib/auth/sessionState';
import { Button } from '../ui/Button';

export const SettingsPage: React.FC = () => {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [health, setHealth] = useState<{ status: string; version: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const session = getLocalSession();

  useEffect(() => {
    Promise.all([getSystem().catch(() => null), getHealth().catch(() => null)]).then(
      ([sys, hlth]) => {
        setSystem(sys);
        setHealth(hlth);
        setLoading(false);
      }
    );
  }, []);

  const handleResetSession = () => {
    if (confirm('Reset local session state and return to onboarding?')) {
      clearLocalSession();
      window.location.hash = '#/onboarding';
      window.location.reload();
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto font-mono text-xs text-[#F5F5F5]">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-[#F5F5F5]">System Policy & Configuration</h1>
        <p className="text-xs text-[#71717A] mt-0.5">
          Surge backend decision thresholds, reasoning routing, and local session preferences.
        </p>
      </div>

      {loading ? (
        <div className="p-8 text-center text-[#71717A]">Loading system parameters...</div>
      ) : (
        <div className="max-w-4xl space-y-6">
          {/* Diagnostic Policy Thresholds */}
          <div className="p-5 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
            <div className="text-sm font-bold text-[#F5F5F5] mb-3 pb-2 border-b border-[#1A1A1F] flex items-center justify-between">
              <span>Diagnostic Stopping Policy</span>
              <span className="text-[10px] text-emerald-400 font-bold uppercase">
                Enforced by Orchestrator
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-[#71717A] mb-1">Supported Threshold</div>
                <div className="text-lg font-bold text-[#F5F5F5]">
                  {system?.policy.diagnosis.supported_threshold != null
                    ? `${system.policy.diagnosis.supported_threshold * 100}%`
                    : '70%'}
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Minimum confidence required for a hypothesis to be considered viable.
                </div>
              </div>

              <div className="p-3 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-[#71717A] mb-1">Early Stop Threshold</div>
                <div className="text-lg font-bold text-emerald-400">
                  {system?.policy.diagnosis.stop_threshold != null
                    ? `${system.policy.diagnosis.stop_threshold * 100}%`
                    : '85%'}
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Investigation terminates early once confidence reaches this threshold.
                </div>
              </div>

              <div className="p-3 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-[#71717A] mb-1">Min Independent Sources</div>
                <div className="text-lg font-bold text-[#F5F5F5]">
                  {system?.policy.diagnosis.min_independent_sources || 2}
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Evidence from at least two distinct tools required to confirm a diagnosis.
                </div>
              </div>

              <div className="p-3 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-[#71717A] mb-1">Min Margin Over Runner-up</div>
                <div className="text-lg font-bold text-[#F5F5F5]">
                  {system?.policy.diagnosis.min_margin_over_runner_up != null
                    ? `${system.policy.diagnosis.min_margin_over_runner_up * 100}%`
                    : '20%'}
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Lead margin over the second-place competing hypothesis.
                </div>
              </div>
            </div>
          </div>

          {/* Reasoning & LLM Configuration */}
          <div className="p-5 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
            <div className="text-sm font-bold text-[#F5F5F5] mb-3 pb-2 border-b border-[#1A1A1F]">
              Reasoning Engine
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#1A1A1F]">
                <span className="text-[#71717A]">Default Mode:</span>
                <span className="text-[#F5F5F5] font-bold">
                  {system?.reasoning.default_mode || 'auto'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1A1A1F]">
                <span className="text-[#71717A]">LLM Available:</span>
                <span className={system?.reasoning.llm_available ? 'text-emerald-400' : 'text-zinc-400'}>
                  {system?.reasoning.llm_available ? 'YES (Hybrid Provider)' : 'Deterministic Fallback'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1A1A1F]">
                <span className="text-[#71717A]">Active Model:</span>
                <span className="text-[#818CF8]">
                  {system?.reasoning.active_model || 'Heuristic Rules Engine'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#71717A]">Max Tool Invocations:</span>
                <span className="text-[#F5F5F5]">{system?.policy.max_tool_calls || 14}</span>
              </div>
              <div className="flex justify-between py-1 border-t border-[#1A1A1F]">
                <span className="text-[#71717A]">Backend Health:</span>
                <span className={health?.status === 'ok' ? 'text-emerald-400' : 'text-zinc-400'}>
                  {health?.status === 'ok' ? `ONLINE (${health.version})` : 'UNREACHABLE'}
                </span>
              </div>
            </div>
          </div>

          {/* Honest Local Session Settings */}
          <div className="p-5 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
            <div className="text-sm font-bold text-[#F5F5F5] mb-2 pb-2 border-b border-[#1A1A1F]">
              Local Demo Session
            </div>
            <p className="text-[11px] text-[#71717A] mb-4 leading-relaxed">
              This browser holds your local operator preferences and completed onboarding state. It
              does not represent a cloud account or authentication token.
            </p>

            <div className="space-y-2 text-xs mb-4">
              <div className="flex justify-between py-1 border-b border-[#1A1A1F]">
                <span className="text-[#71717A]">Session Identifier:</span>
                <span className="text-[#F5F5F5]">{session?.sessionId}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1A1A1F]">
                <span className="text-[#71717A]">Operator Handle:</span>
                <span className="text-[#F5F5F5]">{session?.sessionName}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#71717A]">Connected Signals:</span>
                <span className="text-emerald-400">
                  {session?.selectedApps?.join(', ') || 'none'}
                </span>
              </div>
            </div>

            <Button size="sm" variant="danger" onClick={handleResetSession} className="text-xs">
              Clear Local Session & Re-run Onboarding
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
