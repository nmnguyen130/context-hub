"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Next.js Error Boundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#090d16] flex items-center justify-center p-6 text-center">
      <div className="glass-panel p-8 rounded-2xl max-w-md border border-slate-800 bg-slate-950/80 shadow-2xl">
        <div className="w-12 h-12 rounded-xl bg-rose-950/80 text-rose-400 border border-rose-500/30 flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-white font-outfit">Something went wrong</h2>
        <p className="text-xs text-slate-400 mt-2 mb-6">
          {error.message || "An unexpected error occurred while rendering the application."}
        </p>

        <Button onClick={reset} leftIcon={<RefreshCw className="w-4 h-4" />}>
          Try Again
        </Button>
      </div>
    </div>
  );
}
