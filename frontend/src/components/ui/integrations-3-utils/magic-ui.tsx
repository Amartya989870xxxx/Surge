
export const MagicUI = () => (
  <svg viewBox="0 0 24 24" fill="none" className="size-8">
    <circle cx="12" cy="12" r="10" fill="url(#magic-grad)" opacity="0.15" />
    <path
      d="M7 17V7L12 12L17 7V17"
      stroke="url(#magic-grad)"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <defs>
      <linearGradient id="magic-grad" x1="7" y1="7" x2="17" y2="17" gradientUnits="userSpaceOnUse">
        <stop stopColor="#EC4899" />
        <stop offset="1" stopColor="#F59E0B" />
      </linearGradient>
    </defs>
  </svg>
);
