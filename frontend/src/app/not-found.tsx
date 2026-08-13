import Link from "next/link";
import { Sparkles, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#090d16] flex items-center justify-center p-6 text-center">
      <div className="glass-panel p-8 rounded-2xl max-w-md border border-slate-800 bg-slate-950/80 shadow-2xl">
        <div className="w-12 h-12 rounded-xl bg-indigo-950/80 text-indigo-400 border border-indigo-500/30 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-6 h-6" />
        </div>
        <h1 className="text-4xl font-extrabold text-white font-outfit">404</h1>
        <h2 className="text-lg font-bold text-slate-200 font-outfit mt-1">Page Not Found</h2>
        <p className="text-xs text-slate-400 mt-2 mb-6">
          The page or workspace resource you are looking for does not exist.
        </p>

        <Link href="/dashboard">
          <Button leftIcon={<ArrowLeft className="w-4 h-4" />}>Return to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}
