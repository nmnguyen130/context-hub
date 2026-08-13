import { useQuery } from "@tanstack/react-query";
import { authApi } from "@/lib/api/auth";

export function useCurrentUser() {
  return useQuery({
    queryKey: ["current-user"],
    queryFn: () => authApi.getCurrentUser(),
    retry: false, // Don't retry if 401 unauthenticated
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}
