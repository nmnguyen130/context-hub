"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function SettingsSecurityPage() {
  const [ssnPolicy, setSsnPolicy] = useState("MASK");
  const [ccPolicy, setCcPolicy] = useState("MASK");
  const [secretsPolicy, setSecretsPolicy] = useState("REJECT");

  const handleSaveDlp = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Security & DLP pre-ingestion rules saved.");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-base font-bold text-primary font-heading">Data Loss Prevention (DLP) & Security</h2>
        <p className="text-xs text-muted">
          Pre-ingestion regex scanning filters to sanitize sensitive PII and secrets before vector embedding.
        </p>
      </div>

      <form onSubmit={handleSaveDlp} className="space-y-5">
        {/* SSN Policy */}
        <div className="p-4 rounded-lg bg-surface-dark border border-stroke space-y-2 text-xs text-left">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-primary">Social Security Numbers (SSN)</span>
            <select
              value={ssnPolicy}
              onChange={(e) => setSsnPolicy(e.target.value)}
              className="p-1.5 rounded bg-surface-elevated border border-stroke text-xs text-primary"
            >
              <option value="MASK">Mask (***-**-****)</option>
              <option value="REJECT">Reject Ingestion</option>
              <option value="ALLOW">Allow (Unmasked)</option>
            </select>
          </div>
          <p className="text-[11px] text-muted">
            Automatically scans for US SSN patterns and redacts matching numeric chunks prior to pgvector storage.
          </p>
        </div>

        {/* Credit Card Policy */}
        <div className="p-4 rounded-lg bg-surface-dark border border-stroke space-y-2 text-xs text-left">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-primary">Payment Card Numbers (PCI-DSS)</span>
            <select
              value={ccPolicy}
              onChange={(e) => setCcPolicy(e.target.value)}
              className="p-1.5 rounded bg-surface-elevated border border-stroke text-xs text-primary"
            >
              <option value="MASK">Mask (****-****-****-1234)</option>
              <option value="REJECT">Reject Ingestion</option>
              <option value="ALLOW">Allow (Unmasked)</option>
            </select>
          </div>
          <p className="text-[11px] text-muted">
            Luhn algorithm validation for Visa, Mastercard, AMEX, and Discover account numbers.
          </p>
        </div>

        {/* API Keys & Secrets Policy */}
        <div className="p-4 rounded-lg bg-surface-dark border border-stroke space-y-2 text-xs text-left">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-primary">API Keys & Cloud Credentials</span>
            <select
              value={secretsPolicy}
              onChange={(e) => setSecretsPolicy(e.target.value)}
              className="p-1.5 rounded bg-surface-elevated border border-stroke text-xs text-primary"
            >
              <option value="REJECT">Reject Chunk & Alert Admin</option>
              <option value="MASK">Redact Secret</option>
              <option value="ALLOW">Allow</option>
            </select>
          </div>
          <p className="text-[11px] text-muted">
            Entropy-based scanner for OpenAI, AWS, GitHub tokens, and private keys.
          </p>
        </div>

        <div className="pt-2 flex justify-end">
          <Button type="submit" className="bg-accent hover:bg-accent-hover text-white">
            Save Security Policy
          </Button>
        </div>
      </form>
    </div>
  );
}
