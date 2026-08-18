"use client";

import { useState } from "react";
import Link from "next/link";
import { Terminal, Menu, X, ArrowRight } from "lucide-react";

export function LandingNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-canvas/90 backdrop-blur-md border-b border-stroke">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-md bg-surface border border-stroke flex items-center justify-center text-accent group-hover:border-accent/50 transition-colors">
              <Terminal className="w-3.5 h-3.5" />
            </div>
            <span className="font-bold text-sm tracking-tight text-primary font-heading">
              Context<span className="text-accent">Hub</span>
            </span>
          </Link>

          {/* System Status Tag (Desktop) */}
          <div className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded border border-stroke bg-surface text-[10px] text-muted font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
            <span>MULTI-TENANT AI PLATFORM</span>
          </div>
        </div>

        {/* Navigation links (Desktop) */}
        <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-muted">
          <a href="#pipeline" className="hover:text-primary transition-colors">
            Architecture Pipeline
          </a>
          <a href="#tour" className="hover:text-primary transition-colors">
            Platform Demo
          </a>
          <a href="#capabilities" className="hover:text-primary transition-colors">
            Capabilities
          </a>
          <a href="#security" className="hover:text-primary transition-colors">
            Security & Multi-Tenancy
          </a>
          <a href="#pricing" className="hover:text-primary transition-colors">
            Pricing
          </a>
        </nav>

        {/* Auth CTA buttons (Desktop) */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-xs text-muted hover:text-primary font-medium px-3 py-1.5 transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-white text-xs font-semibold px-3.5 py-1.5 rounded-md transition-colors shadow-sm"
          >
            <span>Launch Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile menu toggle */}
        <div className="flex md:hidden items-center gap-2">
          <Link
            href="/login"
            className="text-xs text-muted hover:text-primary font-medium px-2 py-1"
          >
            Sign In
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded border border-stroke bg-surface text-muted hover:text-primary cursor-pointer"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-stroke bg-surface-dark px-4 py-4 space-y-3 text-xs">
          <a
            href="#pipeline"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-muted hover:text-primary py-1"
          >
            Architecture Pipeline
          </a>
          <a
            href="#tour"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-muted hover:text-primary py-1"
          >
            Platform Demo
          </a>
          <a
            href="#capabilities"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-muted hover:text-primary py-1"
          >
            Capabilities
          </a>
          <a
            href="#security"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-muted hover:text-primary py-1"
          >
            Security & Multi-Tenancy
          </a>
          <a
            href="#pricing"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-muted hover:text-primary py-1"
          >
            Pricing
          </a>
          <div className="pt-3 border-t border-stroke flex flex-col gap-2">
            <Link
              href="/register"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center bg-accent hover:bg-accent-hover text-white text-xs font-semibold py-2 rounded-md transition-colors"
            >
              Launch Workspace
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
