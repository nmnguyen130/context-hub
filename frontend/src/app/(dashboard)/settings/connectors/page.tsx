"use client";

import { useState } from "react";
import { Building2, RefreshCw, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface Connector {
  id: string;
  name: string;
  type: string;
  status: "HEALTHY" | "SYNCING" | "AUTH_REQUIRED" | "ERROR";
  lastSync: string;
  nextSync: string;
  docCount: number;
  description: string;
}

export default function SettingsConnectorsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([
    {
      id: "1",
      name: "Google Drive (Enterprise)",
      type: "gdrive",
      status: "HEALTHY",
      lastSync: "12m ago",
      nextSync: "In 48m",
      docCount: 142,
      description: "Auto-syncs shared team drives with preserved Google Workspace ACL permissions.",
    },
    {
      id: "2",
      name: "Microsoft SharePoint & OneDrive",
      type: "sharepoint",
      status: "HEALTHY",
      lastSync: "1h ago",
      nextSync: "In 3h",
      docCount: 88,
      description: "Syncs Microsoft 365 document libraries and respects Entra ID user group ACLs.",
    },
    {
      id: "3",
      name: "Atlassian Confluence Cloud",
      type: "confluence",
      status: "SYNCING",
      lastSync: "Syncing now...",
      nextSync: "Continuous",
      docCount: 310,
      description: "Parses Confluence spaces and page hierarchies with live webhook updates.",
    },
    {
      id: "4",
      name: "Slack Enterprise Grid",
      type: "slack",
      status: "AUTH_REQUIRED",
      lastSync: "2 days ago",
      nextSync: "Paused",
      docCount: 0,
      description: "Indexes public & private channels with granular member permission filtering.",
    },
  ]);

  const handleTriggerSync = (id: string, name: string) => {
    setConnectors((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: "SYNCING", lastSync: "Syncing now..." } : c))
    );
    toast.success(`Incremental sync triggered for ${name}.`);
    setTimeout(() => {
      setConnectors((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "HEALTHY", lastSync: "Just now" } : c))
      );
    }, 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-stroke pb-4">
        <div>
          <h2 className="text-base font-bold text-primary font-heading">Enterprise Connectors & Sync Health</h2>
          <p className="text-xs text-muted">
            Connect external SaaS repositories to index institutional documents with source ACL inheritance.
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-success font-mono bg-success/10 px-2.5 py-1 rounded border border-success/20">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>ACL INHERITANCE ENABLED</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {connectors.map((connector) => (
          <div
            key={connector.id}
            className="p-5 rounded-lg bg-surface-dark border border-stroke flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded bg-surface-elevated border border-stroke flex items-center justify-center text-accent">
                    <Building2 className="w-3.5 h-3.5" />
                  </div>
                  <h3 className="text-xs font-bold text-primary font-heading">{connector.name}</h3>
                </div>

                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                    connector.status === "HEALTHY"
                      ? "bg-success/10 text-success border border-success/20"
                      : connector.status === "SYNCING"
                      ? "bg-accent/10 text-accent border border-accent/20 animate-pulse"
                      : "bg-warning/10 text-warning border border-warning/20"
                  }`}
                >
                  {connector.status}
                </span>
              </div>

              <p className="text-[11px] text-muted leading-relaxed">
                {connector.description}
              </p>
            </div>

            <div className="space-y-3 pt-3 border-t border-stroke text-xs">
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-muted">
                <div>
                  <span className="text-secondary block">Last Sync</span>
                  <span>{connector.lastSync}</span>
                </div>
                <div>
                  <span className="text-secondary block">Next Sync</span>
                  <span>{connector.nextSync}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] font-mono text-primary">
                  {connector.docCount} docs synced
                </span>

                <div className="flex items-center gap-2">
                  {connector.status === "AUTH_REQUIRED" ? (
                    <Button size="sm" className="bg-accent hover:bg-accent-hover text-white">
                      Authenticate
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleTriggerSync(connector.id, connector.name)}
                      disabled={connector.status === "SYNCING"}
                      leftIcon={<RefreshCw className={`w-3 h-3 ${connector.status === "SYNCING" ? "animate-spin" : ""}`} />}
                    >
                      Sync Now
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
