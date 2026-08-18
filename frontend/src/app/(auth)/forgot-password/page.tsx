import { ForgotPasswordForm } from "@/features/auth/forgot-password-form";

export default function ForgotPasswordPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold text-primary font-heading">
          Reset Master Password
        </h1>
        <p className="text-xs text-muted">
          Enter your work email to receive single-use password reset instructions.
        </p>
      </div>

      <ForgotPasswordForm />
    </div>
  );
}
