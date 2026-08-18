"use client";

import { useCurrentTenant } from "@/features/tenant/hooks/use-tenant";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Building2, User, Mail, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

export default function SettingsGeneralPage() {
  const { tenantDisplayName, tenantSlug } = useCurrentTenant();
  const { data: user } = useCurrentUser();

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Organization profile updated successfully.");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-base font-bold text-primary font-heading">Organization Profile</h2>
        <p className="text-xs text-muted">
          Tenant identifier and organizational metadata for this ContextHub installation.
        </p>
      </div>

      <form onSubmit={handleSaveProfile} className="space-y-4">
        <Input
          label="Organization Display Name"
          defaultValue={tenantDisplayName || "Acme Corporation"}
          leftIcon={<Building2 className="w-4 h-4 text-muted" />}
        />

        <div className="space-y-1.5 text-left">
          <label className="text-xs font-medium text-primary">Tenant Identifier Slug</label>
          <Input
            value={tenantSlug || "default"}
            disabled
            leftIcon={<ShieldCheck className="w-4 h-4 text-success" />}
          />
          <p className="text-[10px] text-muted">
            Tenant slugs are immutable after registration to guarantee logical database isolation.
          </p>
        </div>

        <div className="pt-4 border-t border-stroke text-left">
          <h3 className="text-xs font-bold text-primary mb-3 font-heading">Master Administrator Account</h3>
          <div className="space-y-3">
            <Input
              label="Full Name"
              defaultValue={user?.display_name || "Admin"}
              leftIcon={<User className="w-4 h-4 text-muted" />}
            />
            <Input
              label="Work Email"
              defaultValue={user?.email || "admin@company.com"}
              disabled
              leftIcon={<Mail className="w-4 h-4 text-muted" />}
            />
          </div>
        </div>

        <div className="pt-4 flex justify-end">
          <Button type="submit" className="bg-accent hover:bg-accent-hover text-white">
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
