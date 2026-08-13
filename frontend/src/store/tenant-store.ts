import { create } from "zustand";
import { persist } from "zustand/middleware";

interface TenantState {
  tenantSlug: string | null;
  setTenantSlug: (slug: string | null) => void;
  clearTenantSlug: () => void;
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      tenantSlug: null,
      setTenantSlug: (slug) => set({ tenantSlug: slug }),
      clearTenantSlug: () => set({ tenantSlug: null }),
    }),
    {
      name: "contexthub_tenant_slug",
    }
  )
);
