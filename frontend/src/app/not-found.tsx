import Link from "next/link";
import { Terminal, ArrowLeft, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-canvas text-primary tech-grid flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full p-6 sm:p-8 rounded-xl bg-surface border border-stroke text-center space-y-4 shadow-2xl">
        <div className="w-10 h-10 rounded-lg bg-surface-dark border border-stroke flex items-center justify-center text-accent mx-auto">
          <Terminal className="w-5 h-5" />
        </div>

        <div className="space-y-1">
          <span className="text-[10px] font-mono text-danger uppercase tracking-wider bg-danger/10 px-2 py-0.5 rounded border border-danger/20">
            HTTP 404 · NOT FOUND
          </span>
          <h1 className="text-lg font-bold text-primary pt-2 font-heading">Resource Not Found</h1>
          <p className="text-xs text-muted leading-relaxed">
            The requested workspace, route, or document does not exist or you do not have permission to view it.
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 pt-3 border-t border-stroke">
          <Link href="/dashboard">
            <Button
              size="sm"
              leftIcon={<LayoutDashboard className="w-3.5 h-3.5" />}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              Dashboard
            </Button>
          </Link>
          <Link href="/">
            <Button size="sm" variant="secondary" leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}>
              Landing Page
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
