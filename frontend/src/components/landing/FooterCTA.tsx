import React from 'react';

interface FooterCTAProps {
  onOpenApp?: () => void;
  onNavigateWorkspace?: () => void;
}

export const FooterCTA: React.FC<FooterCTAProps> = () => {
  return (
    <footer className="relative bg-[#050507] text-white pt-24 pb-0 overflow-hidden select-none border-t border-white/[0.06]">
      {/* Background Subtle Gradient Glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-purple-900/10 blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10 flex flex-col items-center">
        {/* Top "Lets Connect" Heading (Clean, unclickable, without eye symbol) */}
        <div className="flex flex-col items-center justify-center mb-16 sm:mb-20">
          <div className="inline-flex items-baseline gap-2.5 sm:gap-3.5">
            <span className="text-4xl sm:text-5xl md:text-6xl font-light text-[#8E8E93] tracking-tight">
              Lets
            </span>
            <span className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight">
              Connect
            </span>
          </div>
        </div>

        {/* 4 Social / Connector Icon Links Row */}
        <div className="w-full max-w-4xl grid grid-cols-4 gap-6 sm:gap-12 mb-20 sm:mb-24 justify-items-center">
          {/* 1. X (Twitter) */}
          <a
            href="https://x.com/AmartyaTheDev"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="X (Twitter)"
            className="group relative flex items-center justify-center p-3 sm:p-4 transition-all duration-300 hover:scale-110"
          >
            <div className="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/10 rounded-2xl blur-xl transition-all duration-300" />
            <svg
              className="w-9 h-9 sm:w-11 sm:h-11 md:w-12 md:h-12 text-[#8E8E93] group-hover:text-white transition-colors duration-300 drop-shadow-sm group-hover:drop-shadow-[0_0_16px_rgba(168,85,247,0.7)]"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </a>

          {/* 2. LinkedIn */}
          <a
            href="https://www.linkedin.com/in/amartyamajumder"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn"
            className="group relative flex items-center justify-center p-3 sm:p-4 transition-all duration-300 hover:scale-110"
          >
            <div className="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/10 rounded-2xl blur-xl transition-all duration-300" />
            <svg
              className="w-9 h-9 sm:w-11 sm:h-11 md:w-12 md:h-12 text-[#8E8E93] group-hover:text-white transition-colors duration-300 drop-shadow-sm group-hover:drop-shadow-[0_0_16px_rgba(168,85,247,0.7)]"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.45a1.6 1.6 0 0 0-1.6 1.6 1.6 1.6 0 0 0 1.6 1.6 1.6 1.6 0 0 0 1.6-1.6c0-.88-.72-1.6-1.6-1.6Z" />
            </svg>
          </a>

          {/* 3. Official GitHub */}
          <a
            href="https://github.com/Amartya989870xxxx"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            className="group relative flex items-center justify-center p-3 sm:p-4 transition-all duration-300 hover:scale-110"
          >
            <div className="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/10 rounded-2xl blur-xl transition-all duration-300" />
            <svg
              className="w-9 h-9 sm:w-11 sm:h-11 md:w-12 md:h-12 text-[#8E8E93] group-hover:text-white transition-colors duration-300 drop-shadow-sm group-hover:drop-shadow-[0_0_16px_rgba(168,85,247,0.7)]"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
              />
            </svg>
          </a>

          {/* 4. Mail */}
          <a
            href="mailto:amartya.dev2006@gmail.com"
            aria-label="Email"
            className="group relative flex items-center justify-center p-3 sm:p-4 transition-all duration-300 hover:scale-110"
          >
            <div className="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/10 rounded-2xl blur-xl transition-all duration-300" />
            <svg
              className="w-9 h-9 sm:w-11 sm:h-11 md:w-12 md:h-12 text-[#8E8E93] group-hover:text-white transition-colors duration-300 drop-shadow-sm group-hover:drop-shadow-[0_0_16px_rgba(168,85,247,0.7)]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect width="20" height="16" x="2" y="4" rx="2" strokeDasharray="3 2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" strokeDasharray="3 2" />
            </svg>
          </a>
        </div>

        {/* Divider Line & Copyright / Legal row */}
        <div className="w-full pt-8 pb-10 border-t border-white/[0.08] flex flex-row items-center justify-between text-[10px] sm:text-[11px] tracking-widest text-[#71717A]">
          {/* Left: Copyright */}
          <div className="flex flex-col text-left leading-relaxed">
            <span className="font-semibold text-[#8E8E93]">2026 SURGE.</span>
            <span>ALL RIGHTS RESERVED</span>
          </div>

          {/* Right: Terms & Privacy */}
          <div className="flex items-center gap-6 sm:gap-8">
            <a
              href="#terms"
              className="hover:text-white transition-colors uppercase cursor-pointer"
            >
              TERMS
            </a>
            <a
              href="#privacy"
              className="hover:text-white transition-colors uppercase cursor-pointer"
            >
              PRIVACY POLICY
            </a>
          </div>
        </div>
      </div>

      {/* Giant Colossal SURGE Wordmark with Vivid Purple Ambient Glow */}
      <div className="relative w-full overflow-hidden flex justify-center -mb-4 sm:-mb-8 md:-mb-12 pointer-events-none">
        {/* Volumetric Purple Ambient Glow behind the wordmark */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-48 sm:h-64 md:h-80 bg-gradient-to-t from-[#8B5CF6]/50 via-[#7C3AED]/25 to-transparent blur-[90px] pointer-events-none" />

        {/* Colossal SURGE wordmark in Nohemi Black */}
        <div className="text-[25vw] font-black tracking-tighter leading-[0.74] text-center select-none text-[#8B5CF6] drop-shadow-[0_0_60px_rgba(139,92,246,0.5)] w-full flex justify-center">
          <span className="bg-gradient-to-b from-[#A78BFA] via-[#8B5CF6] to-[#6D28D9] bg-clip-text text-transparent">
            SURGE
          </span>
        </div>

        {/* Subtle bottom edge shadow overlay matching reference image */}
        <div className="absolute inset-x-0 bottom-0 h-10 sm:h-16 bg-gradient-to-t from-[#050507] via-[#050507]/40 to-transparent pointer-events-none" />
      </div>
    </footer>
  );
};

export default FooterCTA;
