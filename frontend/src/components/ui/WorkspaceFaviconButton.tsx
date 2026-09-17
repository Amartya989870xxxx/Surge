import React from 'react';
import { motion } from 'framer-motion';

interface WorkspaceFaviconButtonProps {
  onNavigateWorkspace?: () => void;
  className?: string;
}

export const WorkspaceFaviconButton: React.FC<WorkspaceFaviconButtonProps> = ({
  onNavigateWorkspace,
  className = '',
}) => {
  const handleClick = (e: React.MouseEvent) => {
    if (onNavigateWorkspace) {
      e.preventDefault();
      onNavigateWorkspace();
    } else {
      window.location.hash = '#/dashboard';
    }
  };

  return (
    <motion.a
      href="#/dashboard"
      onClick={handleClick}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.94 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className={`fixed top-4 left-5 z-40 flex items-center justify-center w-10 h-10 rounded-full bg-black/70 backdrop-blur-xl border border-white/10 hover:border-white/30 hover:bg-white/[0.08] shadow-2xl transition-colors cursor-pointer group ${className}`}
      title="Return to Workspace"
      aria-label="Return to Workspace"
    >
      <img
        src="/favicon.png"
        alt="Surge"
        className="w-6 h-6 rounded-full object-contain pointer-events-none drop-shadow-sm group-hover:brightness-110 transition-all"
      />
    </motion.a>
  );
};

export default WorkspaceFaviconButton;
