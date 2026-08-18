import { Terminal } from "lucide-react";

export default function GlobalLoading() {
  return (
    <div className="min-h-screen bg-canvas text-primary flex flex-col items-center justify-center p-4">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-surface border border-stroke flex items-center justify-center text-accent animate-pulse">
          <Terminal className="w-5 h-5" />
        </div>
        <div className="space-y-1 text-center">
          <span className="text-xs font-bold text-primary tracking-tight font-heading">ContextHub</span>
          <p className="text-[11px] text-muted font-mono">Initializing secure tenant environment...</p>
        </div>
      </div>
    </div>
  );
}
