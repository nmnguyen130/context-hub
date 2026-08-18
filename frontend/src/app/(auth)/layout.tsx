import Link from "next/link";
import { Terminal, Shield } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-canvas text-primary tech-grid flex flex-col justify-between py-8 px-4 sm:px-6 lg:px-8">
      {/* Top Bar / Header */}
      <div className="max-w-md w-full mx-auto flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-md bg-surface border border-stroke flex items-center justify-center text-accent group-hover:border-accent/50 transition-colors">
            <Terminal className="w-3.5 h-3.5" />
          </div>
          <span className="font-bold text-sm tracking-tight text-primary font-heading">
            Context<span className="text-accent">Hub</span>
          </span>
        </Link>

        <Link
          href="/"
          className="text-xs text-muted hover:text-primary font-medium transition-colors"
        >
          ← Back to home
        </Link>
      </div>

      {/* Main Form Center Panel */}
      <div className="max-w-md w-full mx-auto my-6">
        <div className="surface-card p-6 sm:p-8 shadow-2xl bg-surface border border-stroke rounded-xl relative">
          {children}
        </div>
      </div>

      {/* Bottom Factual Security Footer */}
      <div className="max-w-md w-full mx-auto text-center space-y-1">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface border border-stroke text-[10px] font-mono text-muted">
          <Shield className="w-3 h-3 text-success" />
          <span>TENANT ISOLATED · SESSION ENCRYPTED</span>
        </div>
        <p className="text-[11px] text-muted">
          Authentication context strictly bounded to verified organization tenant.
        </p>
      </div>
    </div>
  );
}
