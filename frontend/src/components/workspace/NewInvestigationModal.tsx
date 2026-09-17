import React, { useState, useEffect } from 'react';
import { createInvestigation } from '../../lib/api/investigations';
import { listConnectors } from '../../lib/api/connectors';
import { getLocalSession } from '../../lib/auth/sessionState';
import { Button } from '../ui/Button';

interface NewInvestigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (investigationId: string) => void;
}

export const NewInvestigationModal: React.FC<NewInvestigationModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const [requestText, setRequestText] = useState(
    'Investigate the checkout conversion rate drop from Sep 12 14:00 UTC'
  );
  const [scenarioId, setScenarioId] = useState('checkout_regression_01');
  const [faultPresets, setFaultPresets] = useState<Record<string, string>>({});
  const [selectedFaults, setSelectedFaults] = useState<string[]>([]);
  const [reasoning, setReasoning] = useState<'heuristic' | 'llm'>('heuristic');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      listConnectors().then((data) => {
        if (data.fault_presets) {
          setFaultPresets(data.fault_presets);
        }
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (requestText.trim().length < 5) {
      setError('Request must be at least 5 characters');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const session = getLocalSession();
      const res = await createInvestigation({
        request: requestText.trim(),
        scenario_id: scenarioId || undefined,
        inject_failures: selectedFaults,
        reasoning: reasoning,
        session_id: session?.sessionId || 'demo-operator',
      });
      onCreated(res.id);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create investigation');
    } finally {
      setLoading(false);
    }
  };

  const toggleFault = (fault: string) => {
    setSelectedFaults((prev) =>
      prev.includes(fault) ? prev.filter((f) => f !== fault) : [...prev, fault]
    );
  };

  const scenarios = [
    { id: 'checkout_regression_01', name: 'Checkout Regression (Default Hackathon Demo)' },
    { id: 'tracking_failure_01', name: 'Analytics Tracking Failure' },
    { id: 'payment_provider_01', name: 'Payment Gateway Outage' },
    { id: 'marketing_traffic_01', name: 'Low-Intent Traffic Surge' },
    { id: 'slack_unavailable_01', name: 'Slack Unavailable (Graceful Degradation)' },
    { id: 'insufficient_evidence_01', name: 'Insufficient Evidence (Safety Stop)' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#050505]/80 backdrop-blur-sm font-mono text-xs">
      <div className="bg-[#0B0B0D] border border-[#24242B] rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 bg-[#111114] border-b border-[#1A1A1F] flex items-center justify-between">
          <span className="font-bold text-sm text-[#F5F5F5] uppercase">
            Launch New Investigation
          </span>
          <button
            onClick={onClose}
            className="text-[#71717A] hover:text-[#F5F5F5] text-base cursor-pointer"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-2.5 bg-red-950/40 border border-red-800/60 rounded text-red-300">
              {error}
            </div>
          )}

          {/* Problem description */}
          <div>
            <label className="block text-[11px] font-bold text-[#A1A1AA] uppercase mb-1">
              Operational Request
            </label>
            <textarea
              rows={3}
              value={requestText}
              onChange={(e) => setRequestText(e.target.value)}
              className="w-full p-2.5 bg-[#050505] border border-[#24242B] rounded text-[#F5F5F5] placeholder-[#71717A] focus:outline-none focus:border-indigo-500"
              placeholder="Describe the operational anomaly..."
              required
            />
          </div>

          {/* Seeded World / Scenario Selector */}
          <div>
            <label className="block text-[11px] font-bold text-[#A1A1AA] uppercase mb-1">
              Demo World Scenario
            </label>
            <select
              value={scenarioId}
              onChange={(e) => setScenarioId(e.target.value)}
              className="w-full p-2 bg-[#050505] border border-[#24242B] rounded text-[#F5F5F5] focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.id})
                </option>
              ))}
            </select>
          </div>

          {/* Fault Presets Selector */}
          {Object.keys(faultPresets).length > 0 && (
            <div>
              <label className="block text-[11px] font-bold text-[#A1A1AA] uppercase mb-1.5">
                Fault Injections (Optional Resilience Testing)
              </label>
              <div className="space-y-1.5 max-h-32 overflow-y-auto p-2 bg-[#050505] border border-[#1A1A1F] rounded">
                {Object.entries(faultPresets).map(([key, desc]) => (
                  <label
                    key={key}
                    className="flex items-start gap-2 text-[11px] text-[#A1A1AA] hover:text-[#F5F5F5] cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedFaults.includes(key)}
                      onChange={() => toggleFault(key)}
                      className="mt-0.5 accent-indigo-500 rounded"
                    />
                    <span>
                      <strong className="text-amber-300">{key}:</strong> {desc}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning mode */}
          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-[#71717A]">Reasoning Mode:</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setReasoning('heuristic')}
                className={`px-2 py-0.5 rounded border text-[11px] cursor-pointer ${
                  reasoning === 'heuristic'
                    ? 'bg-indigo-950 text-indigo-300 border-indigo-800'
                    : 'text-[#71717A] border-[#24242B]'
                }`}
              >
                Deterministic Heuristic
              </button>
              <button
                type="button"
                onClick={() => setReasoning('llm')}
                className={`px-2 py-0.5 rounded border text-[11px] cursor-pointer ${
                  reasoning === 'llm'
                    ? 'bg-indigo-950 text-indigo-300 border-indigo-800'
                    : 'text-[#71717A] border-[#24242B]'
                }`}
              >
                Hybrid LLM
              </button>
            </div>
          </div>

          {/* Footer buttons */}
          <div className="pt-4 border-t border-[#1A1A1F] flex items-center justify-end gap-2">
            <Button size="sm" variant="ghost" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" variant="primary" type="submit" loading={loading}>
              Spawn Investigation →
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
