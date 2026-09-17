import React, { useState } from 'react';
import type { AppType } from '../../types/api';
import {
  getLocalSession,
  updateLocalSession,
  startLocalSession,
} from '../../lib/auth/sessionState';
import { Step01Welcome } from './Step01Welcome';
import { Step02SelectApps } from './Step02SelectApps';
import { Step03Permissions } from './Step03Permissions';
import { Step04Connect } from './Step04Connect';
import { Step05Complete } from './Step05Complete';

interface OnboardingWizardProps {
  onFinish: () => void;
  onLaunchDemoInvestigation: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  onFinish,
  onLaunchDemoInvestigation,
}) => {
  const session = getLocalSession() || startLocalSession();
  const [step, setStep] = useState<number>(1);
  const [selectedApps, setSelectedApps] = useState<AppType[]>(session.selectedApps || ['sheets', 'github', 'slack']);

  const handleToggleApp = (app: AppType) => {
    setSelectedApps((prev) => {
      const next = prev.includes(app) ? prev.filter((a) => a !== app) : [...prev, app];
      updateLocalSession({ selectedApps: next });
      return next;
    });
  };

  const handleComplete = () => {
    updateLocalSession({
      onboardingCompleted: true,
      selectedApps,
    });
    onFinish();
  };

  const handleSkip = () => {
    updateLocalSession({
      onboardingCompleted: true,
    });
    onFinish();
  };

  return (
    <div className="min-h-screen bg-[#050505] text-[#F5F5F5] flex flex-col justify-center px-6 py-12">
      <div className="w-full max-w-3xl mx-auto">
        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-8 font-mono text-xs text-[#71717A]">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold border transition-colors ${
                  step === i
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : step > i
                    ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                    : 'bg-[#111114] text-[#71717A] border-[#1A1A1F]'
                }`}
              >
                {step > i ? '✓' : i}
              </span>
              {i < 5 && <div className="w-6 h-px bg-[#1A1A1F]" />}
            </div>
          ))}
        </div>

        {/* Step Views */}
        <div className="bg-[#0B0B0D] border border-[#1A1A1F] rounded-xl p-6 sm:p-8 shadow-2xl">
          {step === 1 && (
            <Step01Welcome onNext={() => setStep(2)} onSkip={handleSkip} />
          )}

          {step === 2 && (
            <Step02SelectApps
              selectedApps={selectedApps}
              onToggleApp={handleToggleApp}
              onNext={() => setStep(3)}
              onBack={() => setStep(1)}
            />
          )}

          {step === 3 && (
            <Step03Permissions
              selectedApps={selectedApps}
              onNext={() => setStep(4)}
              onBack={() => setStep(2)}
            />
          )}

          {step === 4 && (
            <Step04Connect
              selectedApps={selectedApps}
              onNext={() => setStep(5)}
              onBack={() => setStep(3)}
            />
          )}

          {step === 5 && (
            <Step05Complete
              selectedApps={selectedApps}
              onLaunchInvestigation={() => {
                updateLocalSession({ onboardingCompleted: true });
                onLaunchDemoInvestigation();
              }}
              onGoToWorkspace={handleComplete}
            />
          )}
        </div>
      </div>
    </div>
  );
};
