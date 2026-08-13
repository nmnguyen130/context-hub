"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail, Lock, Building, ArrowRight } from "lucide-react";
import { registerSchema, RegisterFormValues } from "./schemas";
import { authApi } from "@/lib/api/auth";
import { useTenantStore } from "@/store/tenant-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function RegisterForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const { setTenantSlug } = useTenantStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormValues) => {
    setLoading(true);
    try {
      // Automatically derive tenant slug for local state store
      const derivedSlug = data.tenant_name
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
      
      setTenantSlug(derivedSlug);

      await authApi.register({
        tenant_name: data.tenant_name,
        email: data.email,
        password: data.password,
      });

      toast.success("Organization created successfully! Please sign in.");
      router.push("/login");
    } catch (err: any) {
      toast.error(err.message || "Failed to register organization.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="Organization Name"
        placeholder="Acme Corporation"
        leftIcon={<Building className="w-4 h-4" />}
        error={errors.tenant_name?.message}
        {...register("tenant_name")}
      />

      <Input
        label="Admin Email"
        type="email"
        placeholder="admin@acme.com"
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
        Create Tenant Organization
      </Button>
    </form>
  );
}
