import Link from "next/link";
import { RegisterForm } from "@/features/auth/register-form";

export default function RegisterPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold text-primary font-heading">
          Create Tenant Organization
        </h1>
        <p className="text-xs text-muted">
          Set up a multi-tenant AI Knowledge workspace & master admin account.
        </p>
      </div>

      <RegisterForm />

      <p className="text-center text-xs text-muted pt-2 border-t border-stroke">
        Already have an organization workspace?{" "}
        <Link
          href="/login"
          className="text-accent font-semibold hover:underline"
        >
          Sign In
        </Link>
      </p>
    </div>
  );
}
