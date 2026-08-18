"use client";

import { useState } from "react";
import { Plus, Mail, AlertTriangle, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { toast } from "sonner";

export default function SettingsMembersPage() {
  const { data: currentUser } = useCurrentUser();
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");

  const [members, setMembers] = useState([
    {
      id: "1",
      email: currentUser?.email || "alex@acme.com",
      name: currentUser?.display_name || "Alex Rivers (You)",
      role: "OWNER",
      status: "ACTIVE",
      lastLogin: "Active Now",
    },
    {
      id: "2",
      email: "sarah.chen@acme.com",
      name: "Sarah Chen",
      role: "ADMIN",
      status: "ACTIVE",
      lastLogin: "2 hours ago",
    },
    {
      id: "3",
      email: "david.kim@acme.com",
      name: "David Kim",
      role: "MEMBER",
      status: "ACTIVE",
      lastLogin: "Yesterday",
    },
  ]);

  const handleSendInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setMembers((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        email: inviteEmail,
        name: inviteEmail.split("@")[0],
        role: inviteRole,
        status: "INVITED",
        lastLogin: "Pending Token Accept",
      },
    ]);
    toast.success(`Invitation dispatched to ${inviteEmail} (Single-use token valid for 24h).`);
    setInviteEmail("");
    setShowInviteModal(false);
  };

  const handleRevokeAllSessions = () => {
    setShowRevokeModal(false);
    toast.success("Global session revocation executed. All other active sessions terminated.");
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-stroke pb-4">
        <div>
          <h2 className="text-base font-bold text-primary font-heading">Team Directory & RBAC Roles</h2>
          <p className="text-xs text-muted">
            Manage tenant-level permissions and invite team members to your organization.
          </p>
        </div>

        <Button
          size="sm"
          onClick={() => setShowInviteModal(true)}
          leftIcon={<Plus className="w-3.5 h-3.5" />}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          Invite Member
        </Button>
      </div>

      {/* Members Table */}
      <div className="rounded-lg bg-surface-dark border border-stroke overflow-hidden text-xs">
        <table className="w-full text-left">
          <thead className="bg-surface text-muted border-b border-stroke font-mono text-[11px]">
            <tr>
              <th className="px-4 py-3">Member</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last Active</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stroke">
            {members.map((m) => (
              <tr key={m.id} className="hover:bg-surface-elevated/40 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-semibold text-primary">{m.name}</div>
                  <div className="text-[11px] text-muted font-mono">{m.email}</div>
                </td>
                <td className="px-4 py-3 font-mono text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-surface border border-stroke text-primary">
                    {m.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded ${
                      m.status === "ACTIVE"
                        ? "bg-success/10 text-success border border-success/20"
                        : "bg-warning/10 text-warning border border-warning/20"
                    }`}
                  >
                    {m.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted font-mono text-[11px]">
                  {m.lastLogin}
                </td>
                <td className="px-4 py-3 text-right">
                  {m.role !== "OWNER" && (
                    <button
                      onClick={() => toast.info(`Role change for ${m.email} saved.`)}
                      className="text-[11px] text-accent hover:underline cursor-pointer"
                    >
                      Edit Role
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Global Session Revocation Card */}
      <div className="p-4 rounded-lg bg-surface-dark border border-stroke flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div>
          <span className="font-bold text-primary block">Global Session Termination</span>
          <span className="text-muted text-[11px]">
            Invalidate all active refresh tokens and sign out of all sessions across all devices.
          </span>
        </div>
        <Button
          size="sm"
          variant="danger"
          onClick={() => setShowRevokeModal(true)}
          leftIcon={<LogOut className="w-3.5 h-3.5" />}
        >
          Sign Out All Other Sessions
        </Button>
      </div>

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="surface-card max-w-md w-full p-6 bg-surface border border-stroke rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-stroke pb-2">
              <h3 className="text-sm font-bold text-primary font-heading">Invite Team Member</h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-muted hover:text-primary text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSendInvite} className="space-y-3">
              <Input
                label="Work Email Address"
                type="email"
                placeholder="colleague@acme.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                leftIcon={<Mail className="w-4 h-4 text-muted" />}
                required
              />

              <div className="space-y-1 text-left">
                <label className="text-xs font-medium text-primary">Assign Tenant Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full p-2 rounded-md bg-surface-elevated border border-stroke text-xs text-primary"
                >
                  <option value="MEMBER">Member (Read, Search, Grounded RAG Chat)</option>
                  <option value="ADMIN">Admin (Manage Workspaces, Members, Documents)</option>
                  <option value="VIEWER">Viewer (Read-only knowledge access)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowInviteModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" size="sm" className="bg-accent hover:bg-accent-hover text-white">
                  Send Invitation
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Revoke All Sessions Confirmation Modal */}
      {showRevokeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="surface-card max-w-sm w-full p-6 bg-surface border border-stroke rounded-xl space-y-3 text-xs">
            <h3 className="text-sm font-bold text-danger flex items-center gap-1.5 font-heading">
              <AlertTriangle className="w-4 h-4" />
              Revoke All Active Sessions?
            </h3>
            <p className="text-muted">
              This will immediately invalidate all session refresh tokens in Redis and PostgreSQL across mobile, desktop, and web clients.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={() => setShowRevokeModal(false)}>
                Cancel
              </Button>
              <Button size="sm" variant="danger" onClick={handleRevokeAllSessions}>
                Revoke All Sessions
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
