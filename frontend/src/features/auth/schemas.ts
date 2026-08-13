import { z } from "zod";

export const loginSchema = z.object({
  tenant_slug: z.string().min(2, "Organization slug is required"),
  email: z.string().email("Valid email address is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  tenant_name: z.string().min(3, "Organization name must be at least 3 characters"),
  email: z.string().email("Valid email address is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;
