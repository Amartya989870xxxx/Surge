import React from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";

// --- PROPS INTERFACE ---
export interface JobCardProps {
  companyLogo: React.ReactNode;
  companyName: string;
  jobTitle: string;
  salary: string;
  tags: string[];
  postedDate: string;
  variant?: "pink" | "yellow" | "blue" | "purple";
  className?: string;
  onClick?: () => void;
}

// --- BORDER VARIANT STYLES ---
const variantClasses = {
  pink: "border-t-pink-500",
  yellow: "border-t-yellow-500",
  blue: "border-t-blue-500",
  purple: "border-t-purple-500",
};

/**
 * A responsive, theme-adaptive card with a 3D tilt effect on hover.
 */
export const AnimatedJobCard = ({
  companyLogo,
  companyName,
  jobTitle,
  salary,
  tags,
  postedDate,
  variant = "purple",
  className,
  onClick,
}: JobCardProps) => {
  // --- FULL ANIMATION LOGIC ---
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const cardRef = React.useRef<HTMLDivElement>(null);

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const { left, top, width, height } = cardRef.current.getBoundingClientRect();
    mouseX.set(e.clientX - left - width / 2);
    mouseY.set(e.clientY - top - height / 2);
  };

  const onMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  // Transform mouse position into a 3D rotation
  const rotateX = useTransform(mouseY, [-150, 150], [10, -10]);
  const rotateY = useTransform(mouseX, [-150, 150], [-10, 10]);

  // Apply spring physics for a smooth return effect
  const springConfig = { stiffness: 300, damping: 20, mass: 0.5 };
  const springRotateX = useSpring(rotateX, springConfig);
  const springRotateY = useSpring(rotateY, springConfig);

  return (
    <motion.div
      layout
      onClick={onClick}
      whileHover={{ scale: 1.025 }}
      whileTap={{ scale: 0.96 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      ref={cardRef}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{
        rotateX: springRotateX,
        rotateY: springRotateY,
        transformStyle: "preserve-3d",
      }}
      className={cn(
        "relative w-full max-w-sm shrink-0 transform-gpu cursor-pointer overflow-hidden rounded-2xl bg-[#0E1017]/90 border border-white/10 p-6 shadow-xl transition-all duration-300 hover:shadow-2xl hover:border-white/20 backdrop-blur-md",
        "border-t-4",
        variantClasses[variant],
        className
      )}
      aria-label={`${jobTitle} at ${companyName}`}
      tabIndex={0}
    >
      <div style={{ transform: "translateZ(20px)" }} className="space-y-4">
        {/* Header */}
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.06] border border-white/10 p-2">
            {companyLogo}
          </div>
          <span className="font-semibold text-white/80 text-sm tracking-wide">{companyName}</span>
        </div>

        {/* Details */}
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">{jobTitle}</h3>
          <p className="text-xs text-indigo-400 font-medium mt-0.5">{salary}</p>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2">
          {tags.map((tag, index) => (
            <span
              key={index}
              className="rounded-full bg-white/[0.06] border border-white/[0.08] px-2.5 py-0.5 text-xs font-medium text-white/70"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Footer */}
        <div className="pt-2 text-right text-[11px] text-white/40">
          {postedDate}
        </div>
      </div>
    </motion.div>
  );
};

export default AnimatedJobCard;
