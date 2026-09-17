import React from "react";
import { Gemini } from "@/components/ui/integrations-3-utils/gemini";
import { Replit } from "@/components/ui/integrations-3-utils/replit";
import { MagicUI } from "@/components/ui/integrations-3-utils/magic-ui";
import { VSCodium } from "@/components/ui/integrations-3-utils/vs-codium";
import { MediaWiki } from "@/components/ui/integrations-3-utils/media-wiki";
import { GooglePaLM } from "@/components/ui/integrations-3-utils/google-palm";
import { LogoIcon } from "@/components/ui/integrations-3-utils/logo";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

interface IntegrationsSectionProps {
  onGetStarted?: () => void;
  className?: string;
}

export default function IntegrationsSection({
  onGetStarted,
  className,
}: IntegrationsSectionProps) {
  return (
    <section className={cn("min-h-screen bg-[#000000] text-[#F5F5F5] flex items-center justify-center relative overflow-hidden py-16 px-4 select-none", className)}>
      {/* Ambient background glow */}
      <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[450px] bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[500px] h-[400px] bg-indigo-500/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="w-full max-w-5xl mx-auto z-10">
        <div className="grid items-center sm:grid-cols-2 gap-12 sm:gap-16">
          {/* Tool icon cluster (matching 3rd reference image) */}
          <div className="relative mx-auto w-fit">
            <div
              aria-hidden
              className="absolute inset-0 z-10 from-transparent via-[#000000]/10 to-[#000000]/80 pointer-events-none"
            />
            {/* Row 1 */}
            <div className="mx-auto mb-3 flex w-fit justify-center gap-3">
              <IntegrationCard>
                <Gemini />
              </IntegrationCard>
              <IntegrationCard>
                <Replit />
              </IntegrationCard>
            </div>

            {/* Row 2 */}
            <div className="mx-auto my-3 flex w-fit justify-center gap-3">
              <IntegrationCard>
                <MagicUI />
              </IntegrationCard>
              <IntegrationCard
                borderClassName="shadow-[0_0_35px_rgba(6,182,212,0.4)] border-cyan-400/50"
                className="bg-[#0C1524] scale-105 ring-1 ring-cyan-500/20"
              >
                <LogoIcon />
              </IntegrationCard>
              <IntegrationCard>
                <VSCodium />
              </IntegrationCard>
            </div>

            {/* Row 3 */}
            <div className="mx-auto flex w-fit justify-center gap-3">
              <IntegrationCard>
                <MediaWiki />
              </IntegrationCard>
              <IntegrationCard>
                <GooglePaLM />
              </IntegrationCard>
            </div>
          </div>

          {/* Copy and CTA */}
          <div className="mx-auto mt-6 max-w-lg space-y-6 text-center sm:mt-0 sm:text-left">
            <h2 className="text-balance text-3xl font-black md:text-5xl tracking-tight text-white leading-tight">
              Integrate with your favorite tools
            </h2>
            <p className="text-[#A1A1AA] text-base leading-relaxed">
              Connect seamlessly with popular platforms and services to enhance your workflow.
            </p>

            <div>
              <Button
                variant="outline"
                size="default"
                onClick={onGetStarted}
                className="border-white/20 bg-white/10 hover:bg-white/20 text-white rounded-xl px-7 py-2.5 font-bold text-sm transition-all shadow-lg hover:scale-105 cursor-pointer"
              >
                Get Started →
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const IntegrationCard = ({
  children,
  className,
  borderClassName,
}: {
  children: React.ReactNode;
  className?: string;
  borderClassName?: string;
}) => {
  return (
    <div
      className={cn(
        "relative flex size-20 sm:size-24 rounded-2xl bg-[#0E1017]/90 border border-white/10 shadow-xl backdrop-blur-md transition-all duration-300 hover:scale-105 hover:border-white/30",
        className
      )}
    >
      <div
        role="presentation"
        className={cn(
          "absolute inset-0 rounded-2xl border border-white/10",
          borderClassName
        )}
      />
      <div className="relative z-20 m-auto size-fit *:size-8 sm:*:size-9 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
};

export { IntegrationsSection };
