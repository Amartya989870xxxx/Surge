import React, { useState } from 'react';
import { updateProfile, type ProfileOut } from '../../lib/api/auth';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';
import { WorkspaceFaviconButton } from '../ui/WorkspaceFaviconButton';

interface PersonaAndGoalOnboardingProps {
  initialProfile?: ProfileOut | null;
  onComplete: () => void;
}

export const PersonaAndGoalOnboarding: React.FC<PersonaAndGoalOnboardingProps> = ({
  initialProfile,
  onComplete,
}) => {
  const [step, setStep] = useState<'persona' | 'goal'>('persona');
  const [selectedPersona, setSelectedPersona] = useState<string>(
    initialProfile?.persona || 'engineer'
  );
  const [otherPersonaLabel, setOtherPersonaLabel] = useState<string>(
    initialProfile?.persona_label || ''
  );

  const [selectedGoalTemplate, setSelectedGoalTemplate] = useState<string>(
    initialProfile?.goal_template || 'investigate_incident'
  );
  const [goalText, setGoalText] = useState<string>(
    initialProfile?.goal || 'Investigate a specific incident that just happened'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personas = [
    { id: 'founder', title: 'Founder', desc: 'Framed in business impact, revenue, and customer trust.' },
    { id: 'student', title: 'Student', desc: 'Plain-language definitions of statistical terms and confidence.' },
    { id: 'engineer', title: 'Engineer', desc: 'Thorough investigation depth, commit diffs, and validation traces.' },
    { id: 'designer', title: 'Designer', desc: 'UI/UX regressions, user journey impacts, and conversion shifts.' },
    { id: 'marketer', title: 'Marketer', desc: 'Campaign traffic, funnel conversions, and acquisition anomalies.' },
    { id: 'other', title: 'Other', desc: 'Custom role with specific terminology adaptation.' },
  ];

  const goalSuggestions = [
    {
      template: 'investigate_incident',
      label: 'Investigate a specific incident that just happened',
    },
    {
      template: 'ongoing_monitoring',
      label: "Set up ongoing monitoring for my product's key metrics",
    },
    {
      template: 'engineering_context',
      label: 'Understand what my engineering team shipped recently',
    },
    {
      template: 'learn',
      label: 'Learn how AI-driven root-cause investigation works',
    },
    {
      template: 'other',
      label: 'Other (custom operational goal)',
    },
  ];

  const handlePersonaNext = async () => {
    if (selectedPersona === 'other' && !otherPersonaLabel.trim()) {
      setError('Please specify your role description.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await updateProfile({
        persona: selectedPersona,
        persona_label: selectedPersona === 'other' ? otherPersonaLabel.trim() : null,
      });
      setStep('goal');
    } catch (err: any) {
      setError(err.message || 'Failed to save persona');
    } finally {
      setLoading(false);
    }
  };

  const handleGoalSubmit = async () => {
    if (!goalText.trim()) {
      setError('Please provide your primary goal.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await updateProfile({
        goal: goalText.trim(),
        goal_template: selectedGoalTemplate === 'other' ? null : selectedGoalTemplate,
        onboarding_completed: true,
      });
      onComplete();
    } catch (err: any) {
      setError(err.message || 'Failed to complete onboarding');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F5] flex flex-col justify-center px-6 py-12 font-mono text-xs relative">
      <WorkspaceFaviconButton onNavigateWorkspace={() => { window.location.hash = '#/dashboard'; }} />
      <div className="w-full max-w-xl mx-auto bg-[#0C0C0E] border border-[#18181C] rounded-xl p-8 shadow-2xl">
        {/* Logo & Step indicator */}
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-[#18181C]">
          <div className="flex items-center gap-2">
            <SourceIcon app="surge" size={18} />
            <span className="font-bold text-sm text-[#F5F5F5] tracking-wider uppercase">SURGE</span>
          </div>
          <span className="text-[11px] text-[#71717A]">
            Step {step === 'persona' ? '1 of 2: Persona' : '2 of 2: Objective'}
          </span>
        </div>

        {error && (
          <div className="p-3 bg-red-950/40 border border-red-800/60 rounded text-red-300 text-[11px] mb-6">
            {error}
          </div>
        )}

        {step === 'persona' ? (
          <div>
            <h1 className="text-xl font-bold text-[#F5F5F5] mb-1">What best describes you?</h1>
            <p className="text-[11px] text-[#A1A1AA] leading-relaxed mb-6">
              Surge customizes both its investigation depth and final report wording based on your
              background. (Engineers trigger exhaustive probe runs; students receive plain-language definitions).
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              {personas.map((p) => {
                const isSelected = selectedPersona === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setSelectedPersona(p.id)}
                    className={`p-3 rounded border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500 shadow-sm ring-1 ring-indigo-500/30'
                        : 'bg-[#050505] border-[#18181C] hover:border-[#2A2A35]'
                    }`}
                  >
                    <div className="font-bold text-[#F5F5F5] mb-0.5">{p.title}</div>
                    <div className="text-[10px] text-[#71717A] leading-relaxed">{p.desc}</div>
                  </button>
                );
              })}
            </div>

            {selectedPersona === 'other' && (
              <div className="mb-6">
                <label className="block text-[11px] text-[#A1A1AA] mb-1 font-semibold">
                  Describe your role:
                </label>
                <input
                  type="text"
                  value={otherPersonaLabel}
                  onChange={(e) => setOtherPersonaLabel(e.target.value)}
                  placeholder="e.g. SRE Director, Security Auditor, Operations Lead..."
                  className="w-full px-3 py-2 bg-[#050505] border border-[#222228] rounded text-[#F5F5F5] focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div className="flex justify-end pt-4 border-t border-[#18181C]">
              <Button size="md" variant="primary" onClick={handlePersonaNext} loading={loading}>
                Continue →
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <h1 className="text-xl font-bold text-[#F5F5F5] mb-1">What do you want to use Surge for?</h1>
            <p className="text-[11px] text-[#A1A1AA] leading-relaxed mb-6">
              Pick a primary focus or enter a custom operational goal. This shapes your initial prompt
              context and suggested actions.
            </p>

            <div className="space-y-2 mb-6">
              {goalSuggestions.map((g) => {
                const isSelected = selectedGoalTemplate === g.template;
                return (
                  <button
                    key={g.template}
                    type="button"
                    onClick={() => {
                      setSelectedGoalTemplate(g.template);
                      if (g.template !== 'other') {
                        setGoalText(g.label);
                      } else {
                        setGoalText('');
                      }
                    }}
                    className={`w-full p-3 rounded border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500 shadow-sm ring-1 ring-indigo-500/30 text-[#F5F5F5]'
                        : 'bg-[#050505] border-[#18181C] hover:border-[#2A2A35] text-[#A1A1AA]'
                    }`}
                  >
                    {g.label}
                  </button>
                );
              })}
            </div>

            {selectedGoalTemplate === 'other' && (
              <div className="mb-6">
                <label className="block text-[11px] text-[#A1A1AA] mb-1 font-semibold">
                  Custom operational goal:
                </label>
                <textarea
                  rows={3}
                  value={goalText}
                  onChange={(e) => setGoalText(e.target.value)}
                  placeholder="Describe what you want to investigate or monitor..."
                  className="w-full p-3 bg-[#050505] border border-[#222228] rounded text-[#F5F5F5] focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div className="flex items-center justify-between pt-4 border-t border-[#18181C]">
              <Button size="md" variant="ghost" onClick={() => setStep('persona')} disabled={loading}>
                ← Back
              </Button>

              <Button size="md" variant="primary" onClick={handleGoalSubmit} loading={loading}>
                Complete Onboarding & Connect Apps →
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
