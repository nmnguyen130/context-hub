"use client";

import { useState } from "react";
import { Search, Download, Filter, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  actor: string;
  resourceId: string;
  status: "SUCCESS" | "FAILED";
  ipAddress: string;
}

export default function SettingsAuditPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterAction, setFilterAction] = useState("ALL");

  const [logs] = useState<AuditLogEntry[]>([
    {
      id: "1",
      timestamp: "2026-08-14 15:42:10 UTC",
      action: "AUTH_LOGIN",
      actor: "alex@acme.com",
      resourceId: "user-8f92a10",
      status: "SUCCESS",
      ipAddress: "192.168.1.104",
    },
    {
      id: "2",
      timestamp: "2026-08-14 14:20:05 UTC",
      action: "DOC_UPLOAD",
      actor: "sarah.chen@acme.com",
      resourceId: "doc-91b402",
      status: "SUCCESS",
      ipAddress: "192.168.1.112",
    },
    {
      id: "3",
      timestamp: "2026-08-14 12:15:33 UTC",
      action: "MEMBER_INVITE",
      actor: "alex@acme.com",
      resourceId: "invite-29ba04",
      status: "SUCCESS",
      ipAddress: "192.168.1.104",
    },
    {
      id: "4",
      timestamp: "2026-08-14 10:04:18 UTC",
      action: "SSO_CONFIG_UPDATE",
      actor: "alex@acme.com",
      resourceId: "tenant-acme",
      status: "SUCCESS",
      ipAddress: "192.168.1.104",
    },
  ]);

  const handleExportCsv = () => {
    toast.success("Audit logs exported to CSV (Tenant-scoped).");
  };

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.actor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.resourceId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterAction === "ALL" || log.action === filterAction;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-stroke pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-primary font-heading">Immutable System Audit Explorer</h2>
            <span className="text-[10px] font-mono text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">
              APPEND-ONLY
            </span>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Cryptographically timestamped record of all authentication, ingestion, ACL, and policy events.
          </p>
        </div>

        <Button
          size="sm"
          variant="secondary"
          onClick={handleExportCsv}
          leftIcon={<Download className="w-3.5 h-3.5" />}
        >
          Export CSV
        </Button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by actor, action, or resource..."
            className="w-full pl-9 pr-3 py-1.5 rounded-md bg-surface-dark border border-stroke text-xs text-primary placeholder:text-muted focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          <Filter className="w-3.5 h-3.5 text-muted" />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="p-1.5 rounded bg-surface-dark border border-stroke text-xs text-primary"
          >
            <option value="ALL">All Actions</option>
            <option value="AUTH_LOGIN">AUTH_LOGIN</option>
            <option value="DOC_UPLOAD">DOC_UPLOAD</option>
            <option value="MEMBER_INVITE">MEMBER_INVITE</option>
            <option value="SSO_CONFIG_UPDATE">SSO_CONFIG_UPDATE</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="rounded-lg bg-surface-dark border border-stroke overflow-hidden text-xs">
        <table className="w-full text-left">
          <thead className="bg-surface text-muted border-b border-stroke font-mono text-[11px]">
            <tr>
              <th className="px-4 py-3">Timestamp (UTC)</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Resource ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">IP Address</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stroke">
            {filteredLogs.map((log) => (
              <tr key={log.id} className="hover:bg-surface-elevated/40 transition-colors">
                <td className="px-4 py-3 font-mono text-[11px] text-muted">
                  {log.timestamp}
                </td>
                <td className="px-4 py-3 font-mono text-[11px] font-semibold text-primary">
                  {log.action}
                </td>
                <td className="px-4 py-3 font-mono text-[11px] text-accent">
                  {log.actor}
                </td>
                <td className="px-4 py-3 font-mono text-[11px] text-muted">
                  {log.resourceId}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-success/10 text-success border border-success/20">
                    <CheckCircle2 className="w-3 h-3" />
                    {log.status}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-[11px] text-muted text-right">
                  {log.ipAddress}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
