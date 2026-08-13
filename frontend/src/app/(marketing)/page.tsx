import { LandingNavbar } from "@/components/landing/navbar";
import { LandingHero } from "@/components/landing/hero";
import { RAGDemoPreview } from "@/components/landing/rag-demo-preview";
import { LandingFeatures } from "@/components/landing/features";
import { LandingPricing } from "@/components/landing/pricing";
import { LandingFooter } from "@/components/landing/footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col justify-between">
      <div>
        <LandingNavbar />
        <main>
          <LandingHero />
          <RAGDemoPreview />
          <LandingFeatures />
          <LandingPricing />
        </main>
      </div>
      <LandingFooter />
    </div>
  );
}
