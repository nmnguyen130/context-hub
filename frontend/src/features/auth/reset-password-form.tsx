"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, ArrowRight, Eye, EyeOff, Check, X } from "lucide-react";
import { resetPasswordSchema, ResetPasswordFormValues } from "./schemas";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function ResetPasswordForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      token: "",
      new_password: "",
      confirm_password: "",
    },
  });

  // Extract token from query params
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tokenParam = params.get("token") || "";
      setValue("token", tokenParam);
    }
  }, [setValue]);

  const passwordValue = watch("new_password") || "";
  const isMinLength = passwordValue.length >= 12;
  const hasMixedCase = /[A-Z]/.test(passwordValue) && /[a-z]/.test(passwordValue);
  const hasNumber = /[0-9]/.test(passwordValue);

  const onSubmit = async (data: ResetPasswordFormValues) => {
    if (!data.token) {
      toast.error("Reset token is missing or invalid.");
      return;
    }
    setLoading(true);
    try {
      // Simulate password reset execution
      await new Promise((resolve) => setTimeout(resolve, 800));
      toast.success("Password updated successfully. Please sign in with your new password.");
      router.push("/login");
    } catch {
      toast.error("Failed to reset password. The reset link may be expired.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <input type="hidden" {...register("token")} />

      <div className="space-y-1.5 text-left">
        <label className="text-xs font-medium text-primary">
          New Master Password (min 12 characters)
        </label>
        <div className="relative">
          <Input
            type={showPassword ? "text" : "password"}
            placeholder="••••••••••••"
            leftIcon={<Lock className="w-4 h-4 text-muted" />}
            error={errors.new_password?.message}
            {...register("new_password")}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-2.5 text-muted hover:text-primary cursor-pointer"
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>

        {/* Password Strength Requirements */}
        <div className="p-2.5 rounded bg-surface-dark border border-stroke grid grid-cols-3 gap-1 text-[10px] font-mono">
          <div className={`flex items-center gap-1 ${isMinLength ? "text-success" : "text-muted"}`}>
            {isMinLength ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            <span>12+ chars</span>
          </div>
          <div className={`flex items-center gap-1 ${hasMixedCase ? "text-success" : "text-muted"}`}>
            {hasMixedCase ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            <span>Aa mixed</span>
          </div>
          <div className={`flex items-center gap-1 ${hasNumber ? "text-success" : "text-muted"}`}>
            {hasNumber ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            <span>0-9 number</span>
          </div>
        </div>
      </div>

      <Input
        label="Confirm New Password"
        type="password"
        placeholder="••••••••••••"
        leftIcon={<Lock className="w-4 h-4 text-muted" />}
        error={errors.confirm_password?.message}
        {...register("confirm_password")}
      />

      <Button
        type="submit"
        isLoading={loading}
        className="w-full mt-2 bg-accent hover:bg-accent-hover text-white"
        rightIcon={<ArrowRight className="w-4 h-4" />}
      >
        Set New Password & Sign In
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
