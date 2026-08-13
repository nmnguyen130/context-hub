import Link from "next/link";
import { Sparkles } from "lucide-react";

export function LandingFooter() {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-600 to-cyan-400 p-0.5">
            <div className="w-full h-full bg-slate-950 rounded-[6px] flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            </div>
          </div>
          <span className="font-bold text-base text-white font-outfit">
            Context<span className="text-gradient">Hub</span>
          </span>
          <span className="text-xs text-slate-500 ml-3">
            © {new Date().getFullYear()} ContextHub Inc. All rights reserved.
          </span>
        </div>

        <div className="flex items-center gap-6 text-xs text-slate-400 font-medium">
          <Link href="#features" className="hover:text-white transition-colors">
            Features
          </Link>
          <Link href="#pricing" className="hover:text-white transition-colors">
            Pricing
          </Link>
          <Link href="/login" className="hover:text-white transition-colors">
            Sign In
          </Link>
          <Link href="/register" className="hover:text-white transition-colors">
            Register Tenant
          </Link>
        </div>
      </div>
    </footer>
  );
}
