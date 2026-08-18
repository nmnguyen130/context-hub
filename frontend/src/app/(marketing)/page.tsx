import { LandingNavbar } from "@/components/landing/navbar";
import { LandingHero } from "@/components/landing/hero";
import { StoryPipeline } from "@/components/landing/story-pipeline";
import { PlatformTour } from "@/components/landing/platform-tour";
import { LandingFeatures } from "@/components/landing/features";
import { SecuritySection } from "@/components/landing/security-section";
import { LandingPricing } from "@/components/landing/pricing";
import { LandingFooter } from "@/components/landing/footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0b0d10] text-[#e7ebf0] flex flex-col justify-between">
      <div>
        <LandingNavbar />
        <main>
          <LandingHero />
          <StoryPipeline />
          <PlatformTour />
          <LandingFeatures />
          <SecuritySection />
          <LandingPricing />
        </main>
      </div>
      <LandingFooter />
    </div>
  );
}
