import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Please enter a valid work email address"),
  password: z.string().min(1, "Password is required"),
  tenant_slug: z
    .string()
    .min(2, "Organization slug must be at least 2 characters")
    .optional()
    .or(z.literal("")),
  remember_email: z.boolean().optional(),
  mfa_code: z
    .string()
    .length(6, "MFA code must be exactly 6 digits")
    .regex(/^\d+$/, "MFA code must contain only numbers")
    .optional()
    .or(z.literal("")),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    tenant_name: z
      .string()
      .min(3, "Organization name must be at least 3 characters")
      .max(100, "Organization name cannot exceed 100 characters"),
    tenant_slug: z
      .string()
      .min(3, "Slug must be at least 3 characters")
      .max(50, "Slug cannot exceed 50 characters")
      .regex(
        /^[a-z0-9-]+$/,
        "Slug can only contain lowercase letters, numbers, and hyphens"
      ),
    display_name: z
      .string()
      .min(2, "Full name must be at least 2 characters")
      .max(100, "Full name cannot exceed 100 characters"),
    email: z.string().email("Please enter a valid work email address"),
    password: z
      .string()
      .min(12, "Enterprise password must be at least 12 characters")
      .max(72, "Password cannot exceed 72 characters")
      .refine(
        (val) => /[A-Z]/.test(val) && /[a-z]/.test(val) && /[0-9]/.test(val),
        {
          message:
            "Password must contain uppercase, lowercase, and a number",
        }
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
    terms_accepted: z
      .boolean()
      .refine((val) => val === true, "You must accept the terms of service to continue"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: z.string().email("Please enter a valid work email address"),
  tenant_slug: z.string().optional().or(z.literal("")),
});

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    token: z.string().min(1, "Reset token is required"),
    new_password: z
      .string()
      .min(12, "Enterprise password must be at least 12 characters")
      .max(72, "Password cannot exceed 72 characters")
      .refine(
        (val) => /[A-Z]/.test(val) && /[a-z]/.test(val) && /[0-9]/.test(val),
        {
          message:
            "Password must contain uppercase, lowercase, and a number",
        }
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export const acceptInviteSchema = z
  .object({
    token: z.string().min(1, "Invitation token is required"),
    email: z.string().email("Valid email address is required"),
    display_name: z
      .string()
      .min(2, "Full name must be at least 2 characters")
      .max(100, "Full name cannot exceed 100 characters"),
    password: z
      .string()
      .min(12, "Enterprise password must be at least 12 characters")
      .max(72, "Password cannot exceed 72 characters")
      .refine(
        (val) => /[A-Z]/.test(val) && /[a-z]/.test(val) && /[0-9]/.test(val),
        {
          message:
            "Password must contain uppercase, lowercase, and a number",
        }
      ),
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export type AcceptInviteFormValues = z.infer<typeof acceptInviteSchema>;
