import Link from "next/link";
import { Sparkles } from "lucide-react";
import { RegisterForm } from "@/features/auth/register-form";

export default function RegisterPage() {
  return (
    <div className="min-h-screen bg-[#090d16] flex items-center justify-center p-4 relative overflow-hidden py-12">
      <div className="ambient-glow w-[500px] h-[500px] bg-purple-600/20 top-0 right-1/4" />

      <div className="w-full max-w-lg relative z-10">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-4 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 p-0.5">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <span className="font-bold text-2xl tracking-tight text-white font-outfit">
              Context<span className="text-gradient">Hub</span>
            </span>
          </Link>
          <h1 className="text-2xl font-bold text-white font-outfit">Register new organization</h1>
          <p className="text-slate-400 text-xs mt-1">Setup your multi-tenant AI Knowledge Platform</p>
        </div>

        <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-slate-800 shadow-2xl bg-slate-950/80">
          <RegisterForm />
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          Already registered?{" "}
          <Link href="/login" className="text-indigo-400 font-semibold hover:underline">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
