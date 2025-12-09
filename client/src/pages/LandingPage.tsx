import React from "react";
import { useNavigate } from "react-router-dom";
import { Navbar } from "../components/landing/Navbar";
import { Hero } from "../components/landing/Hero";
import { FeatureSection } from "../components/landing/FeatureSection";
import { Support } from "../components/landing/Support";
// import { Container } from '../components/landing/Container';

export default function LandingPage() {
  const navigate = useNavigate();

  const handleStartMailing = () => {
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-main-bg text-dark-slate font-sans">
      <Navbar>
        <main>
          <Hero />
          <FeatureSection />
          <Support />
        </main>
      </Navbar>
    </div>
  );
}
