"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail, Lock, Building2, User, Globe, ArrowRight, Eye, EyeOff, Check, X } from "lucide-react";
import { registerSchema, RegisterFormValues } from "./schemas";
import { authApi } from "@/lib/api/auth";
import { useTenantStore } from "@/store/tenant-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function deriveSlug(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function RegisterForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [manualSlugEdit, setManualSlugEdit] = useState(false);
  const { setTenantSlug } = useTenantStore();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      tenant_name: "",
      tenant_slug: "",
      display_name: "",
      email: "",
      password: "",
      confirm_password: "",
      terms_accepted: true,
    },
  });

  const passwordValue = watch("password") || "";

  // Password strength checks
  const isMinLength = passwordValue.length >= 12;
  const hasMixedCase = /[A-Z]/.test(passwordValue) && /[a-z]/.test(passwordValue);
  const hasNumber = /[0-9]/.test(passwordValue);

  // Handle Organization Name change to auto-update slug unless manually edited
  const handleOrgNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setValue("tenant_name", val, { shouldValidate: true });
    if (!manualSlugEdit) {
      setValue("tenant_slug", deriveSlug(val), { shouldValidate: true });
    }
  };

  const onSubmit = async (data: RegisterFormValues) => {
    setLoading(true);
    try {
      setTenantSlug(data.tenant_slug);

      await authApi.register({
        tenant_name: data.tenant_name,
        email: data.email,
        password: data.password,
      });

      toast.success("Organization created successfully! Please sign in.");
      router.push(`/login?tenant=${data.tenant_slug}`);
    } catch (err: any) {
      toast.error(err.message || "Failed to register organization.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Organization Name */}
      <Input
        label="Organization Name"
        placeholder="Acme Corporation"
        leftIcon={<Building2 className="w-4 h-4 text-muted" />}
        error={errors.tenant_name?.message}
        onChange={handleOrgNameChange}
      />

      {/* Organization Slug */}
      <div className="space-y-1.5 text-left">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-primary">
            Workspace Slug Identifier
          </label>
          <span className="text-[10px] font-mono text-muted">
            .contexthub.internal
          </span>
        </div>
        <Input
          placeholder="acme-corporation"
          leftIcon={<Globe className="w-4 h-4 text-muted" />}
          error={errors.tenant_slug?.message}
          {...register("tenant_slug", {
            onChange: () => setManualSlugEdit(true),
          })}
        />
        <p className="text-[10px] text-muted">
          Used for tenant isolation context. Derived from organization name and can be customized.
        </p>
      </div>

      {/* Full Name */}
      <Input
        label="Admin Full Name"
        placeholder="Alex Rivers"
        leftIcon={<User className="w-4 h-4 text-muted" />}
        error={errors.display_name?.message}
        {...register("display_name")}
      />

      {/* Work Email */}
      <Input
        label="Admin Work Email"
        type="email"
        placeholder="alex@acme.com"
        leftIcon={<Mail className="w-4 h-4 text-muted" />}
        error={errors.email?.message}
        {...register("email")}
      />

      {/* Password */}
      <div className="space-y-1.5 text-left">
        <label className="text-xs font-medium text-primary">
          Master Password (min 12 characters)
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

        {/* Live Password Strength Requirements */}
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

      {/* Terms & Policy */}
      <div className="space-y-1 pt-1 text-left">
        <div className="flex items-start gap-2">
          <input
            type="checkbox"
            id="terms_accepted"
            className="w-3.5 h-3.5 mt-0.5 rounded border-stroke bg-surface-elevated text-accent focus:ring-0 cursor-pointer"
            {...register("terms_accepted")}
          />
          <label htmlFor="terms_accepted" className="text-[11px] text-muted leading-tight cursor-pointer">
            I agree to the ContextHub Terms of Service, Multi-Tenant Data Isolation Policy, and Security Architecture.
          </label>
        </div>
        {errors.terms_accepted && (
          <p className="text-[11px] text-danger">{errors.terms_accepted.message}</p>
        )}
      </div>

      {/* Submit Button */}
      <Button
        type="submit"
        isLoading={loading}
        className="w-full mt-2 bg-accent hover:bg-accent-hover text-white"
        rightIcon={<ArrowRight className="w-4 h-4" />}
      >
        Create Tenant Organization
      </Button>
    </form>
  );
}
