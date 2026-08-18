"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail, Lock, User, ArrowRight, Eye, EyeOff, Building2, Check, X } from "lucide-react";
import { acceptInviteSchema, AcceptInviteFormValues } from "./schemas";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function AcceptInviteForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [tenantName, setTenantName] = useState<string>("your organization");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AcceptInviteFormValues>({
    resolver: zodResolver(acceptInviteSchema),
    defaultValues: {
      token: "",
      email: "",
      display_name: "",
      password: "",
      confirm_password: "",
    },
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tokenParam = params.get("token") || "";
      const emailParam = params.get("email") || "";
      const orgParam = params.get("org");
      setValue("token", tokenParam);
      setValue("email", emailParam);
      if (orgParam) setTenantName(orgParam);
    }
  }, [setValue]);

  const passwordValue = watch("password") || "";
  const isMinLength = passwordValue.length >= 12;
  const hasMixedCase = /[A-Z]/.test(passwordValue) && /[a-z]/.test(passwordValue);
  const hasNumber = /[0-9]/.test(passwordValue);

  const onSubmit = async (data: AcceptInviteFormValues) => {
    if (!data.token) {
      toast.error("Invitation token is missing or invalid.");
      return;
    }
    setLoading(true);
    try {
      // Simulate invitation acceptance
      await new Promise((resolve) => setTimeout(resolve, 800));
      toast.success("Invitation accepted! Please sign in with your credentials.");
      router.push("/login");
    } catch {
      toast.error("Failed to accept invitation. The invitation may be expired or already used.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <input type="hidden" {...register("token")} />

      {/* Organization Info Banner */}
      <div className="p-3 rounded-lg bg-surface-dark border border-stroke flex items-center gap-2.5 text-xs text-muted">
        <Building2 className="w-4 h-4 text-accent shrink-0" />
        <span>
          Invited to join <strong className="text-primary">{tenantName}</strong>
        </span>
      </div>

      {/* Invited Email (Read-only) */}
      <Input
        label="Invited Work Email"
        type="email"
        leftIcon={<Mail className="w-4 h-4 text-muted" />}
        disabled
        error={errors.email?.message}
        {...register("email")}
      />

      {/* Full Name */}
      <Input
        label="Your Full Name"
        placeholder="Jane Doe"
        leftIcon={<User className="w-4 h-4 text-muted" />}
        error={errors.display_name?.message}
        {...register("display_name")}
      />

      {/* Password */}
      <div className="space-y-1.5 text-left">
        <label className="text-xs font-medium text-primary">
          Create Master Password (min 12 characters)
        </label>
        <div className="relative">
          <Input
            type={showPassword ? "text" : "password"}
            placeholder="••••••••••••"
            leftIcon={<Lock className="w-4 h-4 text-muted" />}
            error={errors.password?.message}
            {...register("password")}
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

      {/* Confirm Password */}
      <Input
        label="Confirm Password"
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
        Accept Invitation & Join Workspace
      </Button>

      <div className="text-center pt-2">
        <Link
          href="/login"
          className="text-xs text-muted hover:text-primary font-medium"
        >
          Already have an account? Sign In
        </Link>
      </div>
    </form>
  );
}
