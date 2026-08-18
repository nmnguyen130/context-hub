"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Mail, Lock, Building2, ArrowRight, Eye, EyeOff, KeyRound, ChevronDown, ChevronUp } from "lucide-react";
import { loginSchema, LoginFormValues } from "./schemas";
import { authApi } from "@/lib/api/auth";
import { useTenantStore } from "@/store/tenant-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function LoginForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showSlugField, setShowSlugField] = useState(false);
  const [showSsoModal, setShowSsoModal] = useState(false);
  const [ssoDomain, setSsoDomain] = useState("");
  const { setTenantSlug } = useTenantStore();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      tenant_slug: "",
      remember_email: true,
      mfa_code: "",
    },
  });

  // Load remembered email or query tenant
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedEmail = localStorage.getItem("contexthub_remembered_email");
      if (savedEmail) {
        setValue("email", savedEmail);
      }
      const params = new URLSearchParams(window.location.search);
      const tenantParam = params.get("tenant");
      if (tenantParam) {
        setValue("tenant_slug", tenantParam);
        setShowSlugField(true);
      }
    }
  }, [setValue]);

  const onSubmit = async (data: LoginFormValues) => {
    setLoading(true);
    try {
      // If remember_email checked, store in localStorage (non-sensitive)
      if (data.remember_email && data.email) {
        localStorage.setItem("contexthub_remembered_email", data.email);
      } else {
        localStorage.removeItem("contexthub_remembered_email");
      }

      // Default tenant slug fallback if empty
      const resolvedTenantSlug = data.tenant_slug?.trim() || "default";

      await authApi.login({
        tenant_slug: resolvedTenantSlug,
        email: data.email,
        password: data.password,
      });

      setTenantSlug(resolvedTenantSlug);

      queryClient.invalidateQueries({ queryKey: ["current-user"] });
      queryClient.invalidateQueries({ queryKey: ["current-tenant"] });

      toast.success("Authentication successful.");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  const handleSsoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ssoDomain.trim()) return;
    toast.info(`Redirecting to enterprise IdP for @${ssoDomain.replace(/^.*@/, "")}...`);
    setShowSsoModal(false);
  };

  return (
    <div className="space-y-5">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Work Email */}
        <Input
          label="Work Email"
          type="email"
          placeholder="alex@company.com"
          leftIcon={<Mail className="w-4 h-4 text-muted" />}
          error={errors.email?.message}
          {...register("email")}
        />

        {/* Password */}
        <div className="space-y-1.5 text-left">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-primary">Password</label>
            <Link
              href="/forgot-password"
              className="text-[11px] text-accent hover:underline"
            >
              Forgot password?
            </Link>
          </div>
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
        </div>

        {/* Collapsible Organization Slug Option */}
        <div>
          <button
            type="button"
            onClick={() => setShowSlugField(!showSlugField)}
            className="inline-flex items-center gap-1.5 text-[11px] text-muted hover:text-secondary transition-colors cursor-pointer"
          >
            {showSlugField ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            <span>{showSlugField ? "Hide custom organization slug" : "Specify custom organization slug (optional)"}</span>
          </button>

          {showSlugField && (
            <div className="mt-2 pt-2 border-t border-stroke/60">
              <Input
                label="Organization Slug"
                placeholder="acme-corp"
                leftIcon={<Building2 className="w-4 h-4 text-muted" />}
                error={errors.tenant_slug?.message}
                {...register("tenant_slug")}
              />
              <p className="text-[10px] text-muted mt-1">
                Leave blank to automatically use your default organization workspace.
              </p>
            </div>
          )}
        </div>

        {/* Remember Email Checkbox */}
        <div className="flex items-center gap-2 pt-1">
          <input
            type="checkbox"
            id="remember_email"
            className="w-3.5 h-3.5 rounded border-stroke bg-surface-elevated text-accent focus:ring-0 cursor-pointer"
            {...register("remember_email")}
          />
          <label htmlFor="remember_email" className="text-xs text-muted cursor-pointer">
            Remember my email on this device
          </label>
        </div>

        {/* Primary Submit Button */}
        <Button
          type="submit"
          isLoading={loading}
          className="w-full mt-2 bg-accent hover:bg-accent-hover text-white"
          rightIcon={<ArrowRight className="w-4 h-4" />}
        >
          Sign In to Workspace
        </Button>
      </form>

      {/* Divider */}
      <div className="relative flex items-center justify-center my-4">
        <div className="border-t border-stroke w-full"></div>
        <span className="bg-surface px-2 text-[10px] font-mono text-muted uppercase">or</span>
      </div>

      {/* SSO Option */}
      <button
        type="button"
        onClick={() => setShowSsoModal(true)}
        className="w-full flex items-center justify-center gap-2 p-2.5 rounded-md bg-surface-elevated hover:bg-surface-hover border border-stroke text-xs font-medium text-primary transition-colors cursor-pointer"
      >
        <KeyRound className="w-3.5 h-3.5 text-accent" />
        <span>Continue with Single Sign-On (SAML / OIDC)</span>
      </button>

      {/* SSO Discovery Modal */}
      {showSsoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="surface-card max-w-sm w-full p-6 bg-surface border border-stroke rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-stroke pb-2">
              <span className="text-xs font-bold text-primary font-heading">Enterprise SSO Discovery</span>
              <button
                onClick={() => setShowSsoModal(false)}
                className="text-muted hover:text-primary text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-muted">
              Enter your company email domain to resolve your organization&apos;s identity provider (Okta, Azure AD, Google Workspace).
            </p>
            <form onSubmit={handleSsoSubmit} className="space-y-3">
              <Input
                label="Company Domain or Work Email"
                placeholder="acme.com or alex@acme.com"
                value={ssoDomain}
                onChange={(e) => setSsoDomain(e.target.value)}
                leftIcon={<Mail className="w-4 h-4 text-muted" />}
              />
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSsoModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" size="sm" className="bg-accent hover:bg-accent-hover text-white">
                  Continue to IdP
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
