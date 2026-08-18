import React from "react";
import { clsx } from "clsx";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "info" | "success" | "warning" | "error" | "neutral" | "accent";
  size?: "sm" | "md";
}

export function Badge({
  children,
  className,
  variant = "info",
  size = "sm",
  ...props
}: BadgeProps) {
  const baseStyles = "inline-flex items-center font-mono rounded border";

  const variants = {
    info: "bg-accent/10 text-accent border-accent/30",
    accent: "bg-accent/10 text-accent border-accent/30",
    success: "bg-success/10 text-success border-success/20",
    warning: "bg-warning/10 text-warning border-warning/20",
    error: "bg-danger/10 text-danger border-danger/20",
    neutral: "bg-surface-elevated text-secondary border-stroke",
  };

  const sizes = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
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
