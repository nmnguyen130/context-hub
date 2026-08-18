"use client";

import { useState } from "react";
import { KeyRound, Globe } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function SettingsSsoPage() {
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [domain, setDomain] = useState("acme.com");
  const [entityId, setEntityId] = useState("https://idp.okta.com/org123");
  const [ssoUrl, setSsoUrl] = useState("https://idp.okta.com/app/sso");

  const handleSaveSso = (e: React.FormEvent) => {
    e.preventDefault();
    setSsoEnabled(true);
    toast.success("Enterprise SAML 2.0 / OIDC Identity Provider configuration saved.");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-base font-bold text-primary font-heading">Single Sign-On (SAML 2.0 / OIDC)</h2>
        <p className="text-xs text-muted">
          Connect your organization&apos;s identity provider (Okta, Azure Active Directory, Google Workspace).
        </p>
      </div>

      <div className="p-3.5 rounded-lg bg-surface-dark border border-stroke flex items-center justify-between text-xs">
        <div className="flex items-center gap-2.5">
          <div className={`w-6 h-6 rounded flex items-center justify-center ${ssoEnabled ? "bg-success/10 text-success" : "bg-surface-elevated text-muted"}`}>
            <KeyRound className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-semibold text-primary">SSO Domain Routing</span>
            <span className="text-muted block text-[11px]">
              Users with verified email domain <code className="text-accent font-mono">@{domain}</code> will be routed to your IdP.
            </span>
          </div>
        </div>

        <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${ssoEnabled ? "bg-success/10 text-success border border-success/20" : "bg-surface-elevated text-muted"}`}>
          {ssoEnabled ? "ACTIVE" : "UNCONFIGURED"}
        </span>
      </div>

      <form onSubmit={handleSaveSso} className="space-y-4">
        <Input
          label="Corporate Email Domain"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          leftIcon={<Globe className="w-4 h-4 text-muted" />}
        />

        <Input
          label="IdP Entity ID / Issuer URL"
          value={entityId}
          onChange={(e) => setEntityId(e.target.value)}
          leftIcon={<KeyRound className="w-4 h-4 text-muted" />}
        />

        <Input
          label="Single Sign-On Service URL (ACS)"
          value={ssoUrl}
          onChange={(e) => setSsoUrl(e.target.value)}
          leftIcon={<KeyRound className="w-4 h-4 text-muted" />}
        />

        <div className="space-y-1.5 text-left">
          <label className="text-xs font-medium text-primary">X.509 Public Certificate</label>
          <textarea
            rows={4}
            placeholder="-----BEGIN CERTIFICATE----- ... -----END CERTIFICATE-----"
            className="w-full p-2.5 rounded-md bg-surface-elevated border border-stroke text-xs font-mono text-primary placeholder:text-muted focus:outline-none focus:border-accent"
          />
        </div>

        <div className="pt-2 flex justify-end">
          <Button type="submit" className="bg-accent hover:bg-accent-hover text-white">
            Save & Test SAML Configuration
          </Button>
        </div>
      </form>
    </div>
  );
}
