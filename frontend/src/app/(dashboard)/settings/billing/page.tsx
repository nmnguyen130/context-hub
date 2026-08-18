"use client";

import { CreditCard, CheckCircle2, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function SettingsBillingPage() {
  const handleUpgradeInquiry = () => {
    toast.info("Sales engineering team notified for Enterprise SLA customization.");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-base font-bold text-primary font-heading">Plan & Knowledge Capacity</h2>
        <p className="text-xs text-muted">
          Current organizational subscription tier and semantic storage quotas.
        </p>
      </div>

      {/* Current Plan Card */}
      <div className="p-5 rounded-lg bg-surface-dark border border-stroke space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-accent/20 text-accent flex items-center justify-center font-bold">
              <CreditCard className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-primary font-heading">ContextHub Enterprise Tier</h3>
              <p className="text-xs text-muted">Multi-tenant isolated pgvector + RRF Hybrid Ingestion</p>
            </div>
          </div>
          <span className="text-[10px] font-mono text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">
            ACTIVE CONTRACT
          </span>
        </div>

        {/* Quota Progress */}
        <div className="space-y-2 pt-2 border-t border-stroke text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted">Ingested Document Storage</span>
            <span className="font-mono text-primary">14.2 MB / Unlimited</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-surface-elevated overflow-hidden">
            <div className="w-[5%] h-full bg-accent"></div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2 text-[11px] text-muted">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-success" />
            <span>Dedicated Tenant Database Isolation</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-success" />
            <span>SAML 2.0 / OIDC SSO Included</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-success" />
            <span>Pre-Ingest DLP Regex Scanners</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-success" />
            <span>Immutable Audit Logging</span>
          </div>
        </div>
      </div>

      {/* Upgrade / Contact Card */}
      <div className="p-4 rounded-lg bg-surface-dark border border-stroke flex items-center justify-between text-xs">
        <div>
          <span className="font-bold text-primary block">Need custom BYOK encryption or on-prem deployment?</span>
          <span className="text-muted text-[11px]">
            Speak with our enterprise solutions architecture team.
          </span>
        </div>
        <Button
          size="sm"
          onClick={handleUpgradeInquiry}
          rightIcon={<ArrowUpRight className="w-3 h-3" />}
          className="bg-accent hover:bg-accent-hover text-white shrink-0"
        >
          Contact Solutions
        </Button>
      </div>
    </div>
  );
}
