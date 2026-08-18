import Link from "next/link";
import { LoginForm } from "@/features/auth/login-form";

export default function LoginPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold text-primary font-heading">
          Sign in to your workspace
        </h1>
        <p className="text-xs text-muted">
          Enter your work email to access your tenant organization.
        </p>
      </div>

      <LoginForm />

      <p className="text-center text-xs text-muted pt-2 border-t border-stroke">
        Need to register a new tenant?{" "}
        <Link
          href="/register"
          className="text-accent font-semibold hover:underline"
        >
          Create Organization
        </Link>
      </p>
    </div>
  );
}
