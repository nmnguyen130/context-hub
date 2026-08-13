"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Mail, Lock, Building, ArrowRight } from "lucide-react";
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
  const { setTenantSlug } = useTenantStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      tenant_slug: "default",
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setLoading(true);
    try {
      await authApi.login({
        tenant_slug: data.tenant_slug,
        email: data.email,
        password: data.password,
      });

      setTenantSlug(data.tenant_slug);

      queryClient.invalidateQueries({ queryKey: ["current-user"] });
      queryClient.invalidateQueries({ queryKey: ["current-tenant"] });

      toast.success("Welcome back! Authentication successful.");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="Organization Slug"
        placeholder="acme-corp"
        leftIcon={<Building className="w-4 h-4" />}
        error={errors.tenant_slug?.message}
        {...register("tenant_slug")}
      />

      <Input
        label="Work Email"
        type="email"
        placeholder="alex@company.com"
        leftIcon={<Mail className="w-4 h-4" />}
        error={errors.email?.message}
        {...register("email")}
      />

      <Input
        label="Password"
        type="password"
        placeholder="••••••••"
        leftIcon={<Lock className="w-4 h-4" />}
        error={errors.password?.message}
        {...register("password")}
      />

      <Button
        type="submit"
        isLoading={loading}
        className="w-full mt-2"
        rightIcon={<ArrowRight className="w-4 h-4" />}
      >
        Sign In to Workspace
      </Button>
    </form>
  );
}
