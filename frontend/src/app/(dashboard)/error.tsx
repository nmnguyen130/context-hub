"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard Route Error:", error);
  }, [error]);

  return (
    <div className="p-12 rounded-lg bg-surface border border-stroke text-center max-w-lg mx-auto my-12 space-y-4 shadow-xl">
      <div className="w-10 h-10 rounded-lg bg-danger/10 border border-danger/30 flex items-center justify-center text-danger mx-auto">
        <AlertCircle className="w-5 h-5" />
      </div>

      <div className="space-y-1">
        <h2 className="text-base font-bold text-primary font-heading">Failed to Load Workspace View</h2>
        <p className="text-xs text-muted leading-relaxed">
          {error.message || "An error occurred while communicating with the backend knowledge service."}
        </p>
      </div>

      <div className="pt-2">
        <Button
          size="sm"
          onClick={() => reset()}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          Retry Loading
        </Button>
      </div>
    </div>
  );
}
