import { useQuery } from "@tanstack/react-query";
import { authApi } from "@/lib/api/auth";
import { useTenantStore } from "@/store/tenant-store";

export function useCurrentTenant() {
  const { tenantSlug, setTenantSlug, clearTenantSlug } = useTenantStore();

  const query = useQuery({
    queryKey: ["current-tenant", tenantSlug],
    queryFn: () => (tenantSlug ? authApi.getCurrentTenant(tenantSlug) : null),
    enabled: Boolean(tenantSlug),
    staleTime: 10 * 60 * 1000,
  });

  return {
    tenant: query.data,
    tenantSlug,
    setTenantSlug,
    clearTenantSlug,
    isLoading: query.isLoading,
    tenantDisplayName: query.data?.name || tenantSlug || null,
  };
}
