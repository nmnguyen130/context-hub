"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail, Building2, ArrowRight, CheckCircle2, RefreshCw } from "lucide-react";
import { forgotPasswordSchema, ForgotPasswordFormValues } from "./schemas";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function ForgotPasswordForm() {
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [countdown, setCountdown] = useState(60);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
      tenant_slug: "",
    },
  });

  // Pre-fill tenant from URL if present
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tenant = params.get("tenant");
      if (tenant) setValue("tenant_slug", tenant);
    }
  }, [setValue]);

  // Cooldown timer for resend
  useEffect(() => {
    let timer: any;
    if (submitted && countdown > 0) {
      timer = setInterval(() => setCountdown((prev) => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [submitted, countdown]);

  const onSubmit = async (data: ForgotPasswordFormValues) => {
    setLoading(true);
    try {
      // Simulate API call to dispatch reset token
      await new Promise((resolve) => setTimeout(resolve, 800));
      setSubmittedEmail(data.email);
      setSubmitted(true);
      setCountdown(60);
      toast.success("Reset instructions dispatched.");
    } catch {
      toast.error("Failed to dispatch reset instructions.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = () => {
    if (countdown > 0) return;
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setCountdown(60);
      toast.success("New reset instructions sent.");
    }, 600);
  };

  if (submitted) {
    return (
      <div className="text-center space-y-4">
        <div className="w-10 h-10 rounded-full bg-success/10 border border-success/30 text-success flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-5 h-5" />
        </div>

        <div className="space-y-1">
          <h2 className="text-sm font-bold text-primary font-heading">Check your inbox</h2>
          <p className="text-xs text-muted leading-relaxed">
            If an account matching <span className="text-primary font-mono">{submittedEmail}</span> exists, single-use password reset instructions have been dispatched (valid for 15 minutes).
          </p>
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={handleResend}
            disabled={countdown > 0 || loading}
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline disabled:text-muted disabled:no-underline cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>
              {countdown > 0 ? `Resend instructions in ${countdown}s` : "Resend instructions now"}
            </span>
          </button>
        </div>

        <div className="pt-3 border-t border-stroke">
          <Link
            href="/login"
            className="text-xs text-muted hover:text-primary font-medium"
          >
            ← Return to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="Work Email"
        type="email"
        placeholder="alex@company.com"
        leftIcon={<Mail className="w-4 h-4 text-muted" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <Input
        label="Organization Slug (Optional)"
        placeholder="acme-corp"
        leftIcon={<Building2 className="w-4 h-4 text-muted" />}
        error={errors.tenant_slug?.message}
        {...register("tenant_slug")}
      />
      <p className="text-[10px] text-muted text-left">
        Specify if your email is registered with multiple tenant workspaces.
      </p>

      <Button
        type="submit"
        isLoading={loading}
        className="w-full mt-2 bg-accent hover:bg-accent-hover text-white"
        rightIcon={<ArrowRight className="w-4 h-4" />}
      >
        Send Reset Instructions
      </Button>

      <div className="text-center pt-2">
        <Link
          href="/login"
          className="text-xs text-muted hover:text-primary font-medium"
        >
          ← Return to Sign In
        </Link>
      </div>
    </form>
  );
}
