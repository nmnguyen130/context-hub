import { Suspense } from "react";
import { ResetPasswordForm } from "@/features/auth/reset-password-form";

export default function ResetPasswordPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold text-primary font-heading">
          Set New Master Password
        </h1>
        <p className="text-xs text-muted">
          Create a secure 12+ character password for your account.
        </p>
      </div>

      <Suspense fallback={<div className="text-xs text-muted text-center">Loading reset session...</div>}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
