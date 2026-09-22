import React, { useState } from 'react';
import { Eye, EyeOff, X, ArrowLeft } from 'lucide-react';

// --- HELPER COMPONENTS (ICONS) ---

export const GoogleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 48 48">
    <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s12-5.373 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-2.641-.21-5.236-.611-7.743z" />
    <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" />
    <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" />
    <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.022 35.026 44 30.038 44 24c0-2.641-.21-5.236-.611-7.743z" />
  </svg>
);

// Streamline waves animation inspired by the 3rd reference image
export const StreamlineWaves: React.FC<{ className?: string }> = ({ className = "" }) => {
  const lineData = [
    { d: "M -60 480 C 100 460, 240 340, 520 260", opacity: 0.12, width: 1.2, dash: "6 10" },
    { d: "M -50 495 C 110 472, 255 350, 530 268", opacity: 0.18, width: 1.4, dash: "12 8" },
    { d: "M -40 510 C 120 485, 270 360, 540 275", opacity: 0.25, width: 1.5, dash: "none" },
    { d: "M -30 525 C 130 498, 285 370, 550 282", opacity: 0.32, width: 1.6, dash: "16 10" },
    { d: "M -20 540 C 140 510, 300 380, 560 290", opacity: 0.40, width: 1.8, dash: "none" },
    { d: "M -10 555 C 150 522, 315 392, 570 298", opacity: 0.35, width: 1.5, dash: "20 12" },
    { d: "M 0 570 C 160 535, 330 405, 580 306", opacity: 0.28, width: 1.4, dash: "none" },
    { d: "M 10 585 C 170 548, 345 418, 590 315", opacity: 0.22, width: 1.3, dash: "8 14" },
    { d: "M 20 600 C 180 560, 360 430, 600 325", opacity: 0.18, width: 1.2, dash: "none" },
    { d: "M 30 615 C 190 572, 375 442, 610 335", opacity: 0.14, width: 1.1, dash: "10 16" },
    { d: "M 40 630 C 200 585, 390 455, 620 345", opacity: 0.10, width: 1.0, dash: "none" },
    { d: "M 50 645 C 210 598, 405 468, 630 356", opacity: 0.08, width: 0.9, dash: "14 18" },
    { d: "M 60 660 C 220 610, 420 482, 640 368", opacity: 0.06, width: 0.8, dash: "none" },
  ];

  return (
    <div className={`relative w-full h-full overflow-hidden select-none pointer-events-none ${className}`}>
      <svg
        viewBox="0 0 600 700"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="absolute inset-0 w-full h-full object-cover scale-110"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <linearGradient id="waveGradient" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#818CF8" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.6" />
          </linearGradient>
          <radialGradient id="ambientGlow" cx="25%" cy="75%" r="60%">
            <stop offset="0%" stopColor="#4F46E5" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Ambient Glow */}
        <rect width="600" height="700" fill="url(#ambientGlow)" />

        {/* Animated Streamline Ribbons */}
        <g className="animate-wave-flow">
          {lineData.map((line, i) => (
            <path
              key={i}
              d={line.d}
              stroke="url(#waveGradient)"
              strokeWidth={line.width}
              strokeOpacity={line.opacity}
              strokeDasharray={line.dash !== "none" ? line.dash : undefined}
              strokeLinecap="round"
            />
          ))}
        </g>
      </svg>
    </div>
  );
};

// --- TYPE DEFINITIONS ---

export interface Testimonial {
  avatarSrc?: string;
  name: string;
  handle: string;
  text: string;
}

export interface SignInPageProps {
  initialMode?: 'signin' | 'signup';
  isSignUpMode?: boolean;
  onToggleMode?: (isSignUp: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  heroImageSrc?: string;
  testimonials?: Testimonial[];
  onSignIn?: (event: React.FormEvent<HTMLFormElement>, isSignUp: boolean, rememberMe: boolean) => void;
  onGoogleSignIn?: () => void;
  onResetPassword?: () => void;
  onCreateAccount?: () => void;
  onDemoMode?: () => void;
  onClose?: () => void;
  loading?: boolean;
  error?: string | null;
  quote?: {
    text: string;
    author: string;
  };
  brandName?: string;
  isModal?: boolean;
}

// --- SUB-COMPONENTS ---

export const GlassInputWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm transition-all focus-within:border-indigo-500/60 focus-within:bg-indigo-500/[0.07] focus-within:ring-1 focus-within:ring-indigo-500/30">
    {children}
  </div>
);

export const TestimonialCard = ({
  testimonial,
  delay,
}: {
  testimonial: Testimonial;
  delay: string;
}) => (
  <div
    className={`animate-testimonial ${delay} flex items-start gap-3 rounded-2xl bg-black/60 backdrop-blur-xl border border-white/10 p-4 w-72 shadow-xl`}
  >
    {testimonial.avatarSrc ? (
      <img
        src={testimonial.avatarSrc}
        className="h-9 w-9 object-cover rounded-xl shrink-0"
        alt={testimonial.name}
      />
    ) : (
      <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center font-bold text-xs text-white shrink-0">
        {testimonial.name[0]}
      </div>
    )}
    <div className="text-xs leading-snug">
      <p className="flex items-center gap-1 font-semibold text-white/95">{testimonial.name}</p>
      <p className="text-white/50 text-[11px]">{testimonial.handle}</p>
      <p className="mt-1.5 text-white/80 line-clamp-3">{testimonial.text}</p>
    </div>
  </div>
);

// --- MAIN COMPONENT ---

export const SignInPage: React.FC<SignInPageProps> = ({
  initialMode = 'signin',
  title = <span className="font-light text-white tracking-tight">Welcome Back</span>,
  description = "Access your account and continue your investigation with us",
  heroImageSrc,
  testimonials = [],
  onSignIn,
  onGoogleSignIn,
  onResetPassword,
  onCreateAccount,
  onDemoMode,
  onClose,
  loading = false,
  error = null,
  quote = {
    text: "Surge proved root cause across Google Sheets and GitHub in 8 seconds, and verified provider state without human delay.",
    author: "Ali Hassan",
  },
  brandName = "Surge",
  isModal = false,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [isSignUpMode, setIsSignUpMode] = useState(initialMode === 'signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  // Sync mode with initialMode prop changes
  React.useEffect(() => {
    setIsSignUpMode(initialMode === 'signup');
  }, [initialMode]);

  // Load the remembered email (only) from the browser cache. The password is never persisted
  // client-side - Firebase's own browserLocalPersistence already keeps the user signed in
  // securely without ever needing the raw password stored in localStorage, where it would be
  // plaintext and readable by any script that can run on the page (e.g. via XSS).
  React.useEffect(() => {
    try {
      const savedEmail = localStorage.getItem('surge_remembered_email');
      if (savedEmail) {
        setEmail(savedEmail);
        setRememberMe(true);
      }
    } catch (e) {
      console.warn('Could not retrieve cached email', e);
    }
  }, []);

  const handleFormSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      if (rememberMe) {
        localStorage.setItem('surge_remembered_email', email.trim());
      } else {
        localStorage.removeItem('surge_remembered_email');
      }
    } catch {}

    if (onSignIn) {
      onSignIn(e, isSignUpMode, rememberMe);
    }
  };

  const containerClasses = isModal
    ? "relative flex flex-col md:flex-row w-full max-w-4xl bg-[#09090C] border border-[#22222A] rounded-3xl overflow-hidden shadow-2xl text-white font-sans my-auto max-h-[92vh]"
    : "min-h-[100dvh] flex flex-col md:flex-row font-sans w-[100dvw] bg-[#050507] text-white";

  return (
    <div className={containerClasses}>
      {/* Optional Close Button for modal mode */}
      {onClose && (
        <button
          onClick={onClose}
          type="button"
          aria-label="Close"
          className="absolute top-5 right-5 z-20 w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-white/70 hover:text-white transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      )}

      {/* Left column / Hero Column with Wave animation (Image 3 inspired) */}
      <section className="hidden md:flex flex-1 relative flex-col justify-between p-8 bg-[#060608] border-r border-[#1B1B22] overflow-hidden min-h-[520px]">
        {/* Background Waves Animation or Image */}
        {heroImageSrc ? (
          <div
            className="animate-slide-right animate-delay-300 absolute inset-0 rounded-2xl bg-cover bg-center"
            style={{ backgroundImage: `url(${heroImageSrc})` }}
          />
        ) : (
          <StreamlineWaves className="absolute inset-0" />
        )}

        {/* Top brand header */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-500 to-blue-400 p-[1px] flex items-center justify-center">
              <div className="w-full h-full bg-[#07070A] rounded-[7px] flex items-center justify-center">
                <svg className="w-3.5 h-3.5 text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 2L2 19.5H22L12 2Z" />
                </svg>
              </div>
            </div>
            <span className="font-bold text-sm tracking-wide text-white">{brandName}</span>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              type="button"
              className="flex items-center gap-1.5 text-xs text-white/60 hover:text-white transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Home</span>
            </button>
          )}
        </div>

        {/* Bottom Testimonial / Quote */}
        <div className="relative z-10 mt-auto pt-16">
          {testimonials.length > 0 ? (
            <div className="flex flex-col gap-3">
              <TestimonialCard testimonial={testimonials[0]} delay="animate-delay-500" />
              {testimonials[1] && (
                <div className="hidden xl:block">
                  <TestimonialCard testimonial={testimonials[1]} delay="animate-delay-700" />
                </div>
              )}
            </div>
          ) : (
            <div className="animate-element animate-delay-500 max-w-sm rounded-2xl bg-black/40 backdrop-blur-md border border-white/10 p-5">
              <p className="text-xs md:text-sm text-white/90 leading-relaxed font-normal">
                “{quote.text}”
              </p>
              <p className="mt-3 text-xs text-indigo-300 font-medium tracking-wide">
                ~ {quote.author}
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Right column: Sign-In / Sign-Up Form (identical UI for both) */}
      <section className="flex-1 flex items-center justify-center p-6 md:p-10 overflow-y-auto">
        <div className="w-full max-w-md">
          <div className="flex flex-col gap-5">
            <div>
              <h1 className="animate-element animate-delay-100 text-3xl md:text-4xl font-semibold leading-tight tracking-tight text-white">
                {isSignUpMode ? "Create your account" : title}
              </h1>
              <p className="animate-element animate-delay-200 mt-2 text-xs md:text-sm text-[#A1A1AA] leading-relaxed">
                {isSignUpMode
                  ? "Join Surge to diagnose incidents and coordinate verified actions."
                  : description}
              </p>
            </div>

            {error && (
              <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-xs leading-relaxed">
                {error}
              </div>
            )}

            <form
              className="space-y-4"
              onSubmit={handleFormSubmit}
            >
              <div className="animate-element animate-delay-300">
                <label className="text-xs font-medium text-[#A1A1AA] mb-1.5 block">
                  Email Address
                </label>
                <GlassInputWrapper>
                  <input
                    name="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full bg-transparent text-sm text-white p-3.5 rounded-2xl focus:outline-none placeholder-[#52525B]"
                  />
                </GlassInputWrapper>
              </div>

              <div className="animate-element animate-delay-400">
                <label className="text-xs font-medium text-[#A1A1AA] mb-1.5 block">
                  Password
                </label>
                <GlassInputWrapper>
                  <div className="relative">
                    <input
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full bg-transparent text-sm text-white p-3.5 pr-11 rounded-2xl focus:outline-none placeholder-[#52525B]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-3 flex items-center text-[#71717A] hover:text-white transition-colors cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </GlassInputWrapper>
              </div>

              {/* Remember me option in both Sign In and Sign Up */}
              <div className="animate-element animate-delay-500 flex items-center justify-between text-xs pt-0.5">
                <label className="flex items-center gap-2.5 cursor-pointer select-none text-[#D4D4D8]">
                  <input
                    type="checkbox"
                    name="rememberMe"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-white/20 bg-white/5 text-indigo-600 focus:ring-indigo-500 cursor-pointer accent-indigo-500"
                  />
                  <span>Remember me on this device</span>
                </label>
                {!isSignUpMode && (
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      onResetPassword?.();
                    }}
                    className="hover:underline text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    Reset password
                  </a>
                )}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="animate-element animate-delay-600 w-full rounded-2xl bg-white text-black py-3.5 font-semibold text-sm hover:bg-neutral-200 transition-all cursor-pointer shadow-lg disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading && (
                  <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                )}
                <span>{isSignUpMode ? "Create your account" : "Log In"}</span>
              </button>

              {/* Prominent clickable message directly below the button as requested */}
              <div className="pt-2 text-center animate-element animate-delay-650">
                {isSignUpMode ? (
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignUpMode(false);
                      onCreateAccount?.();
                    }}
                    className="text-xs text-neutral-300 hover:text-white transition-colors cursor-pointer group"
                  >
                    <span>Already have an account? </span>
                    <span className="text-indigo-400 group-hover:text-indigo-300 font-semibold underline underline-offset-4 ml-0.5">
                      Log In
                    </span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignUpMode(true);
                      onCreateAccount?.();
                    }}
                    className="text-xs text-neutral-300 hover:text-white transition-colors cursor-pointer group"
                  >
                    <span>New User? </span>
                    <span className="text-indigo-400 group-hover:text-indigo-300 font-semibold underline underline-offset-4 ml-0.5">
                      Create your account
                    </span>
                  </button>
                )}
              </div>
            </form>

            <div className="animate-element animate-delay-700 relative flex items-center justify-center my-1">
              <span className="w-full border-t border-white/10"></span>
              <span className="px-3 text-xs text-[#71717A] bg-[#09090C] absolute uppercase tracking-wider">
                Or continue with
              </span>
            </div>

            <button
              type="button"
              onClick={onGoogleSignIn}
              disabled={loading}
              className="animate-element animate-delay-800 w-full flex items-center justify-center gap-3 border border-white/15 bg-white/[0.03] hover:bg-white/[0.08] text-white rounded-2xl py-3.5 text-sm font-medium transition-all cursor-pointer disabled:opacity-50"
            >
              <GoogleIcon />
              <span>Continue with Google</span>
            </button>

            {onDemoMode && (
              <div className="text-center pt-1">
                <button
                  type="button"
                  onClick={onDemoMode}
                  className="text-xs text-[#71717A] hover:text-[#A1A1AA] cursor-pointer underline transition-colors"
                >
                  Continue without signing in (Seeded Demo Mode)
                </button>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

export default SignInPage;
