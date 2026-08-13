import React from "react";
import { clsx } from "clsx";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "info" | "success" | "warning" | "error" | "neutral" | "purple";
  size?: "sm" | "md";
}

export function Badge({
  children,
  className,
  variant = "info",
  size = "sm",
  ...props
}: BadgeProps) {
  const baseStyles = "inline-flex items-center font-medium rounded-full border";

  const variants = {
    info: "bg-indigo-950/60 text-indigo-300 border-indigo-500/30",
    success: "bg-emerald-950/60 text-emerald-300 border-emerald-500/30",
    warning: "bg-amber-950/60 text-amber-300 border-amber-500/30",
    error: "bg-rose-950/60 text-rose-300 border-rose-500/30",
    neutral: "bg-slate-800 text-slate-300 border-slate-700",
    purple: "bg-purple-950/60 text-purple-300 border-purple-500/30",
  };

  const sizes = {
    sm: "text-[11px] px-2.5 py-0.5 gap-1",
    md: "text-xs px-3 py-1 gap-1.5",
  };

  return (
    <span
      className={clsx(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </span>
  );
}
