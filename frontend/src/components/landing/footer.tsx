import Link from "next/link";
import { Terminal } from "lucide-react";

export function LandingFooter() {
  return (
    <footer className="bg-canvas border-t border-stroke py-12 text-xs text-muted">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-8 border-b border-stroke">
          {/* Logo & Platform Tag */}
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-surface border border-stroke flex items-center justify-center text-accent">
              <Terminal className="w-3 h-3" />
            </div>
            <span className="font-bold text-sm text-primary tracking-tight font-heading">
              Context<span className="text-accent">Hub</span>
            </span>
            <span className="text-[10px] font-mono text-muted bg-surface px-2 py-0.5 rounded border border-stroke ml-2">
              Enterprise AI Knowledge Platform
            </span>
          </div>

          {/* Nav Links */}
          <div className="flex flex-wrap items-center gap-6 text-xs">
            <a href="#pipeline" className="hover:text-primary transition-colors">
              Pipeline
            </a>
            <a href="#tour" className="hover:text-primary transition-colors">
              Demo
            </a>
            <a href="#capabilities" className="hover:text-primary transition-colors">
              Capabilities
            </a>
            <a href="#security" className="hover:text-primary transition-colors">
              Security
            </a>
            <a href="#pricing" className="hover:text-primary transition-colors">
              Pricing
            </a>
            <Link href="/login" className="hover:text-primary transition-colors">
              Sign In
            </Link>
          </div>
        </div>

        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px]">
          <p>© {new Date().getFullYear()} ContextHub Platform. All rights reserved.</p>
          <p className="font-mono text-secondary">
            Architecture: FastAPI · SQLAlchemy UoW · PostgreSQL pgvector · Next.js 16
          </p>
        </div>
      </div>
    </footer>
  );
}
