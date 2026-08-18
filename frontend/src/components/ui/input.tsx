import React, { InputHTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    { label, error, hint, leftIcon, rightIcon, className, id, ...props },
    ref
  ) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-medium text-primary tracking-tight"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 text-muted pointer-events-none flex items-center justify-center">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              "w-full bg-surface-elevated border text-primary placeholder:text-muted text-xs sm:text-sm rounded-lg px-3 py-2 transition-all focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/40 disabled:opacity-50 disabled:cursor-not-allowed",
              leftIcon && "pl-9",
              rightIcon && "pr-9",
              error
                ? "border-danger focus:border-danger focus:ring-danger/30"
                : "border-stroke hover:border-stroke-strong",
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 text-muted">{rightIcon}</div>
          )}
        </div>
        {error && <p className="text-[11px] text-danger mt-1">{error}</p>}
        {hint && !error && <p className="text-[11px] text-muted mt-1">{hint}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
