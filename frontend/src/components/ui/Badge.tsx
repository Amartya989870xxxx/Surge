import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground border-white/20",
        verified: "bg-emerald-950/50 text-emerald-300 border-emerald-800/60 font-mono uppercase",
        warning: "bg-amber-950/50 text-amber-300 border-amber-800/60 font-mono uppercase",
        danger: "bg-red-950/50 text-red-300 border-red-800/60 font-mono uppercase",
        investigation: "bg-indigo-950/50 text-indigo-300 border-indigo-800/60 font-mono uppercase",
        neutral: "bg-[#17171C] text-[#A1A1AA] border-[#2A2A33] font-mono uppercase",
        demo: "bg-zinc-800/80 text-zinc-300 border-zinc-700 font-mono uppercase",
        real: "bg-emerald-950/80 text-emerald-200 border-emerald-700 font-mono uppercase",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
export type BadgeVariant =
  | "verified"
  | "warning"
  | "danger"
  | "investigation"
  | "neutral"
  | "demo"
  | "real"
  | "default"
  | "secondary"
  | "destructive"
  | "outline";
