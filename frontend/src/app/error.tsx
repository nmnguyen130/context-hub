"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log client error to audit service
    console.error("Global Application Error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-canvas text-primary flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full p-6 sm:p-8 rounded-xl bg-surface border border-stroke text-center space-y-4 shadow-2xl">
        <div className="w-10 h-10 rounded-lg bg-danger/10 border border-danger/30 flex items-center justify-center text-danger mx-auto">
          <AlertCircle className="w-5 h-5" />
        </div>

        <div className="space-y-1">
          <h2 className="text-base font-bold text-primary font-heading">Application Runtime Exception</h2>
          <p className="text-xs text-muted leading-relaxed">
            An unexpected error occurred during request processing.
          </p>
          {error.digest && (
            <p className="text-[10px] font-mono text-muted bg-surface-dark p-1.5 rounded border border-stroke mt-2">
              Digest: {error.digest}
            </p>
          )}
        </div>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            size="sm"
            onClick={() => reset()}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Retry Action
          </Button>
          <Link href="/">
            <Button size="sm" variant="secondary" leftIcon={<Home className="w-3.5 h-3.5" />}>
              Return Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
