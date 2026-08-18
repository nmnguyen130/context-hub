import { Suspense } from "react";
import { AcceptInviteForm } from "@/features/auth/accept-invite-form";

export default function AcceptInvitePage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold text-primary font-heading">
          Accept Team Invitation
        </h1>
        <p className="text-xs text-muted">
          Set up your user credentials to join the organization workspace.
        </p>
      </div>

      <Suspense fallback={<div className="text-xs text-muted text-center">Loading invitation details...</div>}>
        <AcceptInviteForm />
      </Suspense>
    </div>
  );
}
