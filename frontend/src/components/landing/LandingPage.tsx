import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { LandingNav } from './LandingNav';
import { FooterCTA } from './FooterCTA';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';
import { AnimatedJobCard } from '../ui/animated-card';
import type { ProfileOut } from '../../lib/api/auth';

interface LandingPageProps {
  onOpenApp: () => void;
  onOpenSignIn?: () => void;
  onOpenSignUp?: () => void;
  onViewInvestigation: (id?: string) => void;
  onViewReliability: () => void;
  onNavigateWorkspace?: () => void;
  userProfile?: ProfileOut | null;
}

// Icons for 3D tilt animated cards
const GoogleBadgeIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
  </svg>
);

const GitHubBadgeIcon = () => (
  <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
  </svg>
);

const SlackBadgeIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 2447.6 2452.5">
    <g clipRule="evenodd" fillRule="evenodd">
      <path d="m897.4 0c-135.3.1-244.8 109.9-244.7 245.2-.1 135.3 109.5 245.1 244.8 245.2h244.8v-245.1c.1-135.3-109.5-245.1-244.9-245.3.1 0 .1 0 0 0m0 654h-652.6c-135.3.1-244.9 109.9-244.8 245.2-.2 135.3 109.4 245.1 244.7 245.3h652.7c135.3-.1 244.9-109.9 244.8-245.2.1-135.4-109.5-245.2-244.8-245.3z" fill="#36c5f0"/>
      <path d="m2447.6 899.2c.1-135.3-109.5-245.1-244.8-245.2-135.3.1-244.9 109.9-244.8 245.2v245.3h244.8c135.3-.1 244.9-109.9 244.8-245.3zm-652.7 0v-654c.1-135.2-109.4-245-244.7-245.2-135.3.1-244.9 109.9-244.8 245.2v654c-.2 135.3 109.4 245.1 244.7 245.3 135.3-.1 244.9-109.9 244.8-245.3z" fill="#2eb67d"/>
      <path d="m1550.1 2452.5c135.3-.1 244.9-109.9 244.8-245.2.1-135.3-109.5-245.1-244.8-245.2h-244.8v245.2c-.1 135.2 109.5 245 244.8 245.2zm0-654.1h652.7c135.3-.1 244.9-109.9 244.8-245.2.2-135.3-109.4-245.1-244.7-245.3h-652.7c-135.3.1-244.9 109.9-244.8 245.2-.1 135.4 109.4 245.2 244.7 245.3z" fill="#ecb22e"/>
      <path d="m0 1553.2c-.1 135.3 109.5 245.1 244.8 245.2 135.3-.1 244.9-109.9 244.8-245.2v-245.2h-244.8c-135.3.1-244.9 109.9-244.8 245.2zm652.7 0v654c-.2 135.3 109.4 245.1 244.7 245.3 135.3-.1 244.9-109.9 244.8-245.2v-653.9c.2-135.3-109.4-245.1-244.7-245.3-135.4 0-244.9 109.8-244.8 245.1 0 0 0 .1 0 0" fill="#e01e5a"/>
    </g>
  </svg>
);

export const LandingPage: React.FC<LandingPageProps> = ({
  onOpenApp,
  onOpenSignIn,
  onOpenSignUp,
  onViewInvestigation,
  onViewReliability,
  onNavigateWorkspace,
  userProfile,
}) => {
  const [scrollY, setScrollY] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  // Parallax scroll listener
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);

    if (mediaQuery.matches) return;

    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          setScrollY(window.scrollY);
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      mediaQuery.removeEventListener('change', handler);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  const bgOrbStyle = (baseY: number, speed: number) => {
    if (reducedMotion) return {};
    const offset = (scrollY - baseY) * speed;
    return { transform: `translate3d(0, ${offset.toFixed(1)}px, 0)` };
  };

  const floatingCardStyle = (speed: number) => {
    if (reducedMotion) return {};
    const offset = scrollY * speed;
    return { transform: `translate3d(0, ${offset.toFixed(1)}px, 0)` };
  };

  const workflowSteps = [
    { num: "01", title: "Metric Anomaly Detection" },
    { num: "02", title: "Competing Hypotheses & Falsification" },
    { num: "03", title: "Evidence Linking & Correlation DAG" },
    { num: "04", title: "Independent State Verification" },
  ];

  const workflowCards = [
    {
      step: "STEP 01",
      num: "01",
      accentColor: "text-[#ff8a3d]",
      badgeBg: "bg-[#ff8a3d]/10 border-[#ff8a3d]/30 text-[#ff8a3d]",
      title: "Metric Anomaly Detection",
      description:
        "Surge probes operational data sources (e.g. Google Sheets conversion funnels) to detect statistically meaningful drop-offs against rolling baseline models.",
      bullets: [
        "Isolates exact funnel drop percentages",
        "Filters out false alarm variances",
        "Correlates time windows across sources",
      ],
      screenshot: "/screenshots/metric_anomaly.png",
      alt: "Metric Anomaly Detection Screenshot",
      tag: "METRICS AGENT",
    },
    {
      step: "STEP 02",
      num: "02",
      accentColor: "text-indigo-400",
      badgeBg: "bg-indigo-500/10 border-indigo-500/30 text-indigo-400",
      title: "Competing Hypotheses & Falsification",
      description:
        "Instead of assuming a single cause, Surge produces rival candidate hypotheses and tests them simultaneously. Theories without corroboration are ruled out.",
      bullets: [
        "Multi-source corroboration scoring",
        "Exhaustive counter-evidence elimination",
        "Prior and posterior probability ranking",
      ],
      screenshot: "/screenshots/competing_hypotheses.png",
      alt: "Competing Hypotheses Screenshot",
      tag: "HYPOTHESIS AGENT",
    },
    {
      step: "STEP 03",
      num: "03",
      accentColor: "text-purple-400",
      badgeBg: "bg-purple-500/10 border-purple-500/30 text-purple-400",
      title: "Evidence Linking & Correlation DAG",
      description:
        "Discovered facts from Slack incident chatter, Sheets metrics, and GitHub commits are assembled into a connected, verifiable directed acyclic graph.",
      bullets: [
        "Epistemic FACT vs INFERENCE separation",
        "Timestamp precision alignment",
        "Deterministic correlation tracing",
      ],
      screenshot: "/screenshots/correlation_dag.png",
      alt: "Correlation DAG Screenshot",
      tag: "CORRELATION AGENT",
    },
    {
      step: "STEP 04",
      num: "04",
      accentColor: "text-emerald-400",
      badgeBg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
      title: "Independent State Verification",
      description:
        "Before and after proposing mitigations, Surge independently audits the external tool state. An action is only verified once read-back checks pass 100%.",
      bullets: [
        "Human-in-the-loop approval gate",
        "Zero hallucinated remediations",
        "Idempotent API execution safeguards",
      ],
      screenshot: "/screenshots/state_verification.png",
      alt: "Independent State Verification Screenshot",
      tag: "VERIFICATION AGENT",
    },
  ];

  const faqs = [
    {
      q: "How does Surge ensure it doesn't hallucinate causes?",
      a: "Surge requires every single claim to cite direct evidence: exact column and row coordinates from Google Sheets, git commit hashes and diffs from GitHub, or timestamped messages from Slack. It constructs competing hypotheses simultaneously and runs counter-evidence checks to actively falsify unsubstantiated theories.",
    },
    {
      q: "Can Surge execute write actions without my permission?",
      a: "Never. Surge strictly operates read-only during data collection and diagnostic synthesis. Any proposed write action (e.g. reverting a GitHub commit, updating an operational sheet, or paging an incident channel) is gated by a mandatory operator review step with diff previews.",
    },
    {
      q: "How does the independent verification phase work?",
      a: "After an approved remediation runs, Surge polls external provider APIs directly. It queries the target system to prove the intended change occurred, records the post-action provider state, and computes a cryptographically verifiable run hash.",
    },
    {
      q: "What data does Surge store?",
      a: "Surge stores only connector credentials (encrypted at rest using AES-256 Fernet), investigation metadata, hypotheses, and linked evidence records in an isolated SQLite database. Your source code and spreadsheet row data remain on your host providers.",
    },
    {
      q: "Can I test Surge without connecting production tools?",
      a: "Yes. Surge features an offline Seeded Demo Mode loaded with 16 end-to-end incident scenarios, allowing full exploration of the hypothesis generator, evidence graph, and operator approval gate.",
    },
  ];

  return (
    <div className="landing-page min-h-screen bg-[#050506] text-[#F5F5F5] selection:bg-indigo-500/30 selection:text-white relative overflow-hidden font-[Nohemi]">
      {/* Navigation */}
      <LandingNav
        onOpenApp={onOpenApp}
        onOpenSignIn={onOpenSignIn}
        onOpenSignUp={onOpenSignUp}
        onOpenWorkspace={onNavigateWorkspace}
        userProfile={userProfile}
      />

      {/* Ambient Depth Orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden z-0">
        <div
          style={bgOrbStyle(300, 0.12)}
          className="absolute -top-40 -left-40 w-[900px] h-[600px] rounded-full opacity-45 blur-[160px] transition-transform duration-75"
        >
          <div className="w-full h-full bg-gradient-to-br from-[#ff8a3d]/25 via-[#3d7aff]/25 to-transparent" />
        </div>
        <div
          style={bgOrbStyle(900, -0.08)}
          className="absolute top-[45%] -right-40 w-[800px] h-[600px] rounded-full opacity-35 blur-[160px] transition-transform duration-75"
        >
          <div className="w-full h-full bg-gradient-to-bl from-indigo-600/30 via-purple-600/20 to-transparent" />
        </div>
        <div
          style={bgOrbStyle(2800, 0.18)}
          className="absolute -right-48 w-[800px] h-[550px] rounded-full opacity-40 blur-[150px] transition-transform duration-75"
        >
          <div className="w-full h-full bg-gradient-to-br from-[#ff8a3d]/20 via-[#3d7aff]/20 to-transparent" />
        </div>
      </div>

      {/* Foreground Content */}
      <div className="relative z-10">
        {/* ===================== 1. HERO SECTION ===================== */}
        <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 px-6 max-w-7xl mx-auto flex flex-col items-center text-center">
          {/* Main Headline in Big Bold Editorial Nohemi */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="text-5xl sm:text-7xl md:text-8xl lg:text-9xl font-black tracking-tighter leading-[0.96] max-w-6xl mb-8 text-white select-none"
          >
            Find the signal.
            <br />
            <span className="bg-gradient-to-r from-white via-[#CBD5E1] to-[#94A3B8] bg-clip-text text-transparent">
              Prove the cause.
            </span>
            <br />
            <span className="bg-gradient-to-r from-[#818CF8] via-[#6366F1] to-[#A78BFA] bg-clip-text text-transparent">
              Verify the action.
            </span>
          </motion.h1>

          {/* One-line positioning */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="text-base sm:text-xl text-[#A1A1AA] max-w-3xl leading-relaxed mb-10 font-normal"
          >
            Surge reads your metrics, forms competing theories, tests them against each
            other, and proves its answer before it acts.
          </motion.p>

          {/* Action CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap items-center justify-center gap-4 mb-12"
          >
            {userProfile ? (
              <Button
                size="lg"
                variant="primary"
                onClick={onNavigateWorkspace || onOpenApp}
                className="text-sm px-8 py-3.5 font-bold shadow-xl shadow-indigo-950/60 transition-transform hover:scale-[1.02]"
              >
                Go to Workspace →
              </Button>
            ) : (
              <Button
                size="lg"
                variant="primary"
                onClick={onOpenSignIn || onOpenApp}
                className="text-sm px-8 py-3.5 font-bold shadow-xl shadow-indigo-950/60 transition-transform hover:scale-[1.02]"
              >
                Sign In to Surge →
              </Button>
            )}
            <Button
              size="lg"
              variant="secondary"
              onClick={() => onViewInvestigation()}
              className="text-sm px-7 py-3.5 border-white/[0.1] bg-white/[0.03] text-white hover:bg-white/[0.08] backdrop-blur-md"
            >
              See an investigation
            </Button>
          </motion.div>

          {/* Integration Strip */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.9, delay: 0.35 }}
            className="flex flex-wrap items-center justify-center gap-4 text-xs text-[#71717A] mb-16 pt-4 border-t border-white/[0.06]"
          >
            <span className="flex items-center gap-1.5 text-[#A1A1AA]">
              <SourceIcon app="sheets" size={15} /> Google Sheets
            </span>
            <span className="text-[#3F3F46]">·</span>
            <span className="flex items-center gap-1.5 text-[#A1A1AA]">
              <SourceIcon app="github" size={15} /> GitHub Deployments
            </span>
            <span className="text-[#3F3F46]">·</span>
            <span className="flex items-center gap-1.5 text-[#A1A1AA]">
              <SourceIcon app="slack" size={15} /> Slack Alert Logs
            </span>
            <span className="text-[#3F3F46]">·</span>
            <span className="text-emerald-400 font-semibold">100% Verified Actions</span>
          </motion.div>

          {/* Hero Visual: Real Product UI in Glass Panel */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            style={floatingCardStyle(-0.04)}
            className="w-full max-w-5xl rounded-2xl p-2 md:p-3 bg-[#0A0B10]/80 border border-white/[0.12] backdrop-blur-2xl shadow-2xl shadow-black/80 relative group"
          >
            {/* Top Window Bar */}
            <div className="px-4 py-2.5 bg-[#0E0F14]/90 border-b border-white/[0.08] rounded-t-xl flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
                <span className="text-[#52525B] ml-2 text-[11px]">surge-live-orchestrator.internal</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span className="text-emerald-400 text-[10px] font-bold tracking-wider uppercase">
                  ACTIVE INVESTIGATION
                </span>
              </div>
            </div>

            {/* Real Screenshot Preview */}
            <div className="overflow-hidden rounded-b-xl border border-white/[0.04] bg-[#000000]">
              <img
                src="/screenshots/agent_console_hero.png"
                alt="Surge Agent Console Live Hub-and-Spoke Graph"
                className="w-full h-auto object-cover opacity-95 group-hover:opacity-100 transition-opacity duration-500"
              />
            </div>
          </motion.div>
        </section>

        {/* ===================== 2. WHAT SETS SURGE APART (01) ===================== */}
        <section id="why-surge" className="py-28 px-6 max-w-7xl mx-auto border-t border-white/[0.06]">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.2 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="mb-14"
          >
            <div className="text-xs text-[#ff8a3d] tracking-widest uppercase mb-3 font-semibold">
              01 : THE PRINCIPLES
            </div>
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white mb-4">
              What sets Surge apart.
            </h2>
            <p className="text-base sm:text-lg text-[#A1A1AA] max-w-2xl leading-relaxed">
              Engineered specifically for engineering and operations teams who cannot tolerate
              speculative agent hallucinations.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Card 1: Evidence-first */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.65, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
              className="p-6 rounded-2xl bg-[#0A0B10]/60 border border-white/[0.08] backdrop-blur-xl hover:border-white/[0.18] transition-all duration-300 flex flex-col justify-between group shadow-lg"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-indigo-400 mb-5 group-hover:scale-110 transition-transform">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">Evidence-first</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  Nothing is asserted without a linked source. Every single claim explicitly references
                  exact metrics, git commit diffs, or timestamped channel alerts.
                </p>
              </div>
              <div className="pt-6 mt-4 border-t border-white/[0.04] text-[11px] text-[#71717A]">
                100% cited grounding
              </div>
            </motion.div>

            {/* Card 2: Self-challenging */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.65, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
              className="p-6 rounded-2xl bg-[#0A0B10]/60 border border-white/[0.08] backdrop-blur-xl hover:border-white/[0.18] transition-all duration-300 flex flex-col justify-between group shadow-lg"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-[#ff8a3d] mb-5 group-hover:scale-110 transition-transform">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M16 3h5v5" />
                    <path d="M8 21H3v-5" />
                    <path d="M21 3l-7.5 7.5" />
                    <path d="M3 21l7.5-7.5" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">Self-challenging</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  Actively seeks counter-evidence before concluding. The hypothesis engine constructs
                  competing explanations and tries to falsify each theory.
                </p>
              </div>
              <div className="pt-6 mt-4 border-t border-white/[0.04] text-[11px] text-[#71717A]">
                Falsification-driven
              </div>
            </motion.div>

            {/* Card 3: Controlled action */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.65, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="p-6 rounded-2xl bg-[#0A0B10]/60 border border-white/[0.08] backdrop-blur-xl hover:border-white/[0.18] transition-all duration-300 flex flex-col justify-between group shadow-lg"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-emerald-400 mb-5 group-hover:scale-110 transition-transform">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">Controlled action</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  Nothing executes without approval. Write actions remain held in an explicit gate
                  requiring human review with preview diffs and risk ratings.
                </p>
              </div>
              <div className="pt-6 mt-4 border-t border-white/[0.04] text-[11px] text-[#71717A]">
                Operator gate enforced
              </div>
            </motion.div>

            {/* Card 4: Measured */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.65, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="p-6 rounded-2xl bg-[#0A0B10]/60 border border-white/[0.08] backdrop-blur-xl hover:border-white/[0.18] transition-all duration-300 flex flex-col justify-between group shadow-lg"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-[#3d7aff] mb-5 group-hover:scale-110 transition-transform">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">Measured</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  Reliability is a verified benchmark number, not marketing copy. Benchmarked on 16
                  complex reliability scenarios with 100% precision.
                </p>
              </div>
              <div className="pt-6 mt-4 border-t border-white/[0.04] text-[11px] text-[#71717A]">
                16/16 testbed suites
              </div>
            </motion.div>
          </div>
        </section>

        {/* ===================== 3. HOW SURGE INVESTIGATES (02) ===================== */}
        <section id="how-it-works" className="py-28 px-6 max-w-7xl mx-auto border-t border-white/[0.06] overflow-hidden">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.2 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="mb-14"
          >
            <div className="text-xs text-indigo-400 tracking-widest uppercase mb-3 font-semibold">
              02 : THE WORKFLOW
            </div>
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white mb-4">
              How Surge investigates.
            </h2>
            <p className="text-base sm:text-lg text-[#A1A1AA] max-w-2xl leading-relaxed">
              Every step is deterministic, auditable, and grounded in real operational data.
            </p>
          </motion.div>

          {/* Editorial Rotating Text Ticker */}
          <div className="w-screen -ml-[50vw] left-1/2 relative overflow-hidden py-4 my-6 border-y border-white/[0.08] bg-black/50 backdrop-blur-md select-none">
            <motion.div
              className="flex whitespace-nowrap gap-12 text-xl sm:text-2xl md:text-3xl font-black uppercase tracking-tight text-white/80"
              animate={{ x: [0, -1800] }}
              transition={{ repeat: Infinity, ease: "linear", duration: 28 }}
            >
              {[...workflowSteps, ...workflowSteps, ...workflowSteps].map((step, idx) => (
                <div key={idx} className="flex items-center gap-6 cursor-default">
                  <span className="text-indigo-400/50 font-bold">{step.num}</span>
                  <span className="hover:text-indigo-300 transition-colors">{step.title}</span>
                  <span className="text-[#ff8a3d] text-xl">✦</span>
                </div>
              ))}
            </motion.div>
          </div>

          {/* CONTINUOUS HORIZONTAL REEL OF ALL 4 FULL STEP CARDS (Making rounds from one end of screen to another) */}
          <div className="w-screen -ml-[50vw] left-1/2 relative overflow-hidden py-8 select-none">
            {/* Left and Right Edge Vignette Fades */}
            <div className="pointer-events-none absolute left-0 top-0 bottom-0 w-16 sm:w-36 bg-gradient-to-r from-[#050506] via-[#050506]/80 to-transparent z-20" />
            <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-16 sm:w-36 bg-gradient-to-l from-[#050506] via-[#050506]/80 to-transparent z-20" />

            {/* Moving Reel Track */}
            <div className="animate-cards-marquee flex gap-8 px-8">
              {[...workflowCards, ...workflowCards].map((card, idx) => (
                <div
                  key={idx}
                  className="w-[88vw] sm:w-[740px] md:w-[840px] lg:w-[960px] xl:w-[1040px] shrink-0 rounded-3xl p-6 sm:p-8 lg:p-10 bg-[#0A0B10]/90 border border-white/[0.1] hover:border-white/[0.25] backdrop-blur-2xl shadow-2xl shadow-black/80 transition-all duration-300 overflow-hidden group cursor-pointer"
                >
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">
                    {/* Left Column: Step Info & Copy */}
                    <div className="lg:col-span-5 space-y-4">
                      <div className="flex items-center gap-3">
                        <span className={`px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-wider border ${card.badgeBg}`}>
                          {card.step}
                        </span>
                        <span className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
                          {card.tag}
                        </span>
                      </div>
                      <h3 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white tracking-tight leading-tight">
                        {card.title}
                      </h3>
                      <p className="text-xs sm:text-sm text-[#A1A1AA] leading-relaxed">
                        {card.description}
                      </p>
                      <div className="pt-2">
                        <ul className="space-y-2 text-xs sm:text-sm text-[#A1A1AA]">
                          {card.bullets.map((bullet, bIdx) => (
                            <li key={bIdx} className="flex items-center gap-2.5">
                              <span className={`${card.accentColor} font-bold text-sm`}>✓</span>
                              <span>{bullet}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Right Column: Screenshot Window Mockup */}
                    <div className="lg:col-span-7">
                      <div className="rounded-2xl p-2 bg-[#0E0F14]/90 border border-white/[0.1] backdrop-blur-xl shadow-2xl overflow-hidden group-hover:border-white/[0.18] transition-all duration-300">
                        {/* Window Header */}
                        <div className="px-3 py-2 bg-[#0A0B10] border-b border-white/[0.06] rounded-t-xl flex items-center justify-between text-[11px] text-[#71717A] mb-2">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
                            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
                            <span className="ml-2 text-[10px] text-[#52525B]">surge // {card.tag.toLowerCase()}</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                            <span className="text-emerald-400 text-[9px] font-bold tracking-wider uppercase">VERIFIED</span>
                          </div>
                        </div>
                        <div className="overflow-hidden rounded-xl border border-white/[0.04] bg-[#000000]">
                          <img
                            src={card.screenshot}
                            alt={card.alt}
                            className="w-full h-auto object-cover opacity-90 group-hover:opacity-100 group-hover:scale-[1.01] transition-all duration-500"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Hint below the reel */}
            <div className="flex items-center justify-center gap-2 text-[11px] text-[#71717A] mt-6">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              <span>Hover over any card to pause rotation · Continuous loop</span>
            </div>
          </div>
        </section>

        {/* ===================== 4. PROVEN, NOT PROMISED (03) ===================== */}
        <section id="proven" className="py-28 px-6 max-w-7xl mx-auto border-t border-white/[0.06]">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.2 }}
            transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1] }}
            className="rounded-3xl p-8 md:p-14 bg-[#0A0B10]/80 border border-white/[0.1] backdrop-blur-2xl relative overflow-hidden"
          >
            {/* Subtle glow behind card */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none" />

            <div className="max-w-3xl mb-12 relative z-10">
              <div className="text-xs text-[#3d7aff] tracking-widest uppercase mb-3 font-semibold">
                03 : EMPIRICAL BENCHMARKS
              </div>
              <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white mb-4">
                Proven, not promised.
              </h2>
              <p className="text-sm sm:text-base text-[#A1A1AA] leading-relaxed">
                We do not use customer testimonials or marketing claims. Surge’s reliability is
                measured directly against real, deterministic incident scenarios and published live.
              </p>
            </div>

            {/* Stat Strip */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-10 relative z-10">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: false, amount: 0.2 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06]"
              >
                <div className="text-4xl sm:text-5xl font-black text-white mb-2">
                  16 / 16
                </div>
                <div className="text-xs text-[#A1A1AA]">
                  Reliability scenarios passing
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  100% full-suite clearance
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: false, amount: 0.2 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06]"
              >
                <div className="text-4xl sm:text-5xl font-black text-emerald-400 mb-2">
                  100%
                </div>
                <div className="text-xs text-[#A1A1AA]">
                  Diagnosis accuracy
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Zero hallucinated incidents
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: false, amount: 0.2 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06]"
              >
                <div className="text-4xl sm:text-5xl font-black text-indigo-400 mb-2">
                  0%
                </div>
                <div className="text-xs text-[#A1A1AA]">
                  Duplicate action rate
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Strict idempotency guarantees
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: false, amount: 0.2 }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06]"
              >
                <div className="text-4xl sm:text-5xl font-black text-[#ff8a3d] mb-2">
                  100%
                </div>
                <div className="text-xs text-[#A1A1AA]">
                  Verification success
                </div>
                <div className="text-[10px] text-[#71717A] mt-1">
                  Proved against real telemetry
                </div>
              </motion.div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-white/[0.08] relative z-10">
              <span className="text-xs text-[#71717A]">
                Real evaluation run telemetry · Backend suite 100% automated
              </span>
              <Button
                size="sm"
                variant="secondary"
                onClick={onViewReliability}
                className="text-xs border-white/[0.1] bg-white/[0.04] text-white hover:bg-white/[0.08]"
              >
                Inspect Reliability Benchmark Suite →
              </Button>
            </div>
          </motion.div>
        </section>

        {/* ===================== 5. 3 STEPS TO GET STARTED / 3D TILT CARDS (04) ===================== */}
        <section id="start" className="py-28 px-6 max-w-7xl mx-auto border-t border-white/[0.06]">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.2 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="mb-14"
          >
            <div className="text-xs text-[#ff8a3d] tracking-widest uppercase mb-3 font-semibold">
              04 : ONBOARDING
            </div>
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white mb-4">
              3 steps to get started.
            </h2>
            <p className="text-base sm:text-lg text-[#A1A1AA] max-w-2xl leading-relaxed">
              Fast, zero-config onboarding. Connect your real accounts with granular read scopes. Hover to inspect.
            </p>
          </motion.div>

          {/* 3 Interactive 3D Tilt Animated Cards with spring physics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch justify-items-center">
            {/* Card 1: Google Sheets */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="w-full flex justify-center"
            >
              <AnimatedJobCard
                companyLogo={<GoogleBadgeIcon />}
                companyName="Step 01 · Google Authentication"
                jobTitle="Sign In with Google"
                salary="One-Click Firebase Session"
                tags={["OAuth 2.0", "Granular Scopes", "Read-Only"]}
                postedDate="Ready in 10s · Instant"
                variant="yellow"
                className="w-full"
              />
            </motion.div>

            {/* Card 2: GitHub Provider */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="w-full flex justify-center"
            >
              <AnimatedJobCard
                companyLogo={<GitHubBadgeIcon />}
                companyName="Step 02 · Connect Tools"
                jobTitle="Pick Persona & Link Repos"
                salary="GitHub + Sheets + Slack"
                tags={["Commit Diffs", "Channel History", "Deployments"]}
                postedDate="Zero Config · 20s"
                variant="purple"
                className="w-full"
              />
            </motion.div>

            {/* Card 3: Slack / Describe what changed */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.2 }}
              transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="w-full flex justify-center"
            >
              <AnimatedJobCard
                companyLogo={<SlackBadgeIcon />}
                companyName="Step 03 · Launch Investigation"
                jobTitle="Describe What Changed"
                salary="Human-in-the-Loop Gate"
                tags={["Causal Graph", "Telemetry Diff", "Verified Action"]}
                postedDate="Safe Execution · Real-Time"
                variant="pink"
                className="w-full"
              />
            </motion.div>
          </div>
        </section>

        {/* ===================== 6. MULTI-LAYER SECURITY (05) ===================== */}
        <section id="security" className="py-28 px-6 max-w-7xl mx-auto border-t border-white/[0.06]">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.2 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="mb-14"
          >
            <div className="text-xs text-emerald-400 tracking-widest uppercase mb-3 font-semibold">
              05 : ENTERPRISE ASSURANCE
            </div>
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white mb-4">
              Multi-layer security.
            </h2>
            <p className="text-base sm:text-lg text-[#A1A1AA] max-w-2xl leading-relaxed">
              Built on defensive principles. Real architectural practices, not generic checkmarks.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                num: "01",
                title: "Encrypted Credential Storage",
                desc: "Tokens encrypted at rest via AES-256 Fernet using a persistent server key. Access tokens are isolated per user and never sent to clients.",
              },
              {
                num: "02",
                title: "Scoped OAuth Permissions",
                desc: "Requests strictly read-only scopes by default (spreadsheets.readonly, channels:history).",
              },
              {
                num: "03",
                title: "Explicit Approval Gate",
                desc: "Write actions require mandatory operator confirmation with target previews and risk levels before any state mutation can proceed.",
              },
              {
                num: "04",
                title: "Allowlisted Tool Calls",
                desc: "Surge executes only predefined, schema-validated tool definitions. Every invocation is bounded by strict timeout limits and error handling.",
              },
              {
                num: "05",
                title: "No Arbitrary Code or HTTP",
                desc: "Agents have zero shell access, no unrestricted HTTP client capability, and cannot reach unauthorized external network endpoints.",
              },
              {
                num: "06",
                title: "Isolated SQLite Audit Trail",
                desc: "Every event, hypothesis revision, and verified claim is committed with millisecond timestamps in an immutable investigation event log.",
              },
            ].map((item, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, amount: 0.15 }}
                transition={{ duration: 0.6, delay: idx * 0.08, ease: [0.16, 1, 0.3, 1] }}
                className="p-6 rounded-2xl bg-[#0A0B10]/60 border border-white/[0.08] backdrop-blur-xl hover:border-white/[0.18] transition-colors"
              >
                <div className="text-xs font-bold text-white mb-2 flex items-center gap-2">
                  <span className="text-emerald-400">{item.num}</span> {item.title}
                </div>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  {item.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ===================== 7. FAQ ACCORDION (06) ===================== */}
        <section id="faq" className="py-28 px-6 max-w-4xl mx-auto border-t border-white/[0.06] scroll-mt-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.2 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="text-center mb-16"
          >
            <div className="text-xs text-indigo-400 tracking-widest uppercase mb-3 font-semibold">
              06 : QUESTIONS & ANSWERS
            </div>
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white mb-4">
              Frequently asked questions.
            </h2>
            <p className="text-base text-[#A1A1AA]">
              Real operational mechanics and technical design decisions explained.
            </p>
          </motion.div>

          <div className="space-y-4">
            {faqs.map((faq, index) => {
              const isOpen = openFaqIndex === index;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: false, amount: 0.2 }}
                  transition={{ duration: 0.5, delay: index * 0.06 }}
                  className="rounded-2xl bg-[#0A0B10]/60 border border-white/[0.08] backdrop-blur-xl overflow-hidden transition-all duration-200"
                >
                  <button
                    onClick={() => setOpenFaqIndex(isOpen ? null : index)}
                    className="w-full p-6 text-left flex items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
                  >
                    <span className="text-sm sm:text-base font-semibold text-white">
                      {faq.q}
                    </span>
                    <span className="text-xl text-[#71717A] shrink-0">
                      {isOpen ? '−' : '+'}
                    </span>
                  </button>
                  {isOpen && (
                    <div className="px-6 pb-6 pt-1 text-xs sm:text-sm text-[#A1A1AA] leading-relaxed border-t border-white/[0.04]">
                      {faq.a}
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* ===================== 8. FOOTER WITH LARGE WORDMARK ===================== */}
        <FooterCTA onOpenApp={onOpenApp} onNavigateWorkspace={onNavigateWorkspace} />
      </div>
    </div>
  );
};

export default LandingPage;
