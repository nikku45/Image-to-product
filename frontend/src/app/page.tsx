"use client";

import { useEffect, useState } from "react";
import ImageUploader from "@/components/ImageUploader";
import AnalysisStatus from "@/components/AnalysisStatus";
import CandidateList from "@/components/CandidateList";
import { api, ApiClientError } from "@/lib/api";
import { HealthResponse, ProductMatchResponse } from "@/types/product";

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [matchResult, setMatchResult] = useState<ProductMatchResponse | null>(null);
  const [uploadedPreview, setUploadedPreview] = useState<string | null>(null);

  useEffect(() => {
    async function checkBackend() {
      try {
        setHealthLoading(true);
        const res = await api.getHealth();
        setHealth(res);
        setHealthError(null);
      } catch (err: unknown) {
        if (err instanceof ApiClientError) {
          setHealthError(`${err.code}: ${err.message}`);
        } else if (err instanceof Error) {
          setHealthError(err.message);
        } else {
          setHealthError("Failed to connect to backend server");
        }
      } finally {
        setHealthLoading(false);
      }
    }

    checkBackend();
  }, []);

  const handleUploadSuccess = (result: ProductMatchResponse, previewUrl: string) => {
    setMatchResult(result);
    setUploadedPreview(previewUrl);
  };

  const handleConfirmCandidate = async (asin: string) => {
    if (!matchResult) return;
    const res = await api.confirmCandidate(matchResult.search_id, asin);
    if (res.success) {
      setMatchResult({
        ...matchResult,
        selected_asin: res.confirmed_asin,
      });
    }
  };

  const handleReset = () => {
    setMatchResult(null);
    setUploadedPreview(null);
  };

  return (
    <div className="space-y-8 pb-12">
      {/* System Status Banner */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              healthLoading
                ? "bg-amber-400 animate-pulse"
                : health?.status === "ok"
                ? "bg-emerald-400"
                : "bg-rose-500"
            }`}
          />
          <div>
            <span className="text-sm font-medium text-slate-200">
              Backend Service Status:
            </span>{" "}
            <span className="text-sm font-semibold text-white">
              {healthLoading
                ? "Checking connection..."
                : health?.status === "ok"
                ? "Connected & Operational"
                : "Offline / Unreachable"}
            </span>
            {healthError && (
              <p className="text-xs text-rose-400 mt-0.5">{healthError}</p>
            )}
          </div>
        </div>

        {health && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={`px-2 py-0.5 rounded border ${
                health.gemini_configured
                  ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                  : "bg-amber-950/40 border-amber-800 text-amber-300"
              }`}
            >
              Gemini Vision: {health.gemini_configured ? "Ready" : "Key Needed"}
            </span>
            <span
              className={`px-2 py-0.5 rounded border ${
                health.serpapi_configured
                  ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                  : "bg-amber-950/40 border-amber-800 text-amber-300"
              }`}
            >
              SerpApi Amazon: {health.serpapi_configured ? "Ready" : "Key Needed"}
            </span>
            <span className="px-2 py-0.5 rounded border bg-slate-800/80 border-slate-700 text-slate-300">
              Env: {health.environment}
            </span>
          </div>
        )}
      </section>

      {/* Main Header */}
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Match Product Photos to Amazon.in
        </h2>
        <p className="text-slate-400 text-sm sm:text-base">
          Upload a clear photograph of a physical product or retail package to
          extract visual attributes and discover matching Amazon India ASINs.
        </p>
      </div>

      {/* Upload & Results Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left column: Upload area & Preview */}
        <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-semibold text-slate-200 text-base">
              1. Product Photograph
            </h3>
            {matchResult ? (
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                Analysis Complete
              </span>
            ) : (
              <span className="text-xs text-slate-500">Step 1 of 2</span>
            )}
          </div>

          <ImageUploader onUploadSuccess={handleUploadSuccess} />

          {uploadedPreview && (
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-xs font-semibold text-slate-400 block">
                Active Processed Photograph:
              </span>
              <div className="h-44 w-full rounded-lg overflow-hidden bg-slate-900 flex items-center justify-center">
                <img
                  src={uploadedPreview}
                  alt="Uploaded Product Preview"
                  className="h-full w-full object-contain"
                />
              </div>
            </div>
          )}

          <div className="text-xs text-slate-500 space-y-1.5 pt-2 border-t border-slate-800/80">
            <p className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
              <span>Orientation normalized & EXIF sanitized</span>
            </p>
            <p className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
              <span>Pillow binary signature checks (JPEG, PNG, WebP up to 10MB)</span>
            </p>
            <p className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
              <span>Multi-signal attribute ranking with conflict penalties</span>
            </p>
          </div>
        </div>

        {/* Right column: Results & Candidates view */}
        <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          {!matchResult ? (
            <div className="py-20 text-center text-slate-500 space-y-3">
              <div className="w-14 h-14 mx-auto rounded-full bg-slate-800/60 flex items-center justify-center text-slate-500">
                <svg
                  className="w-7 h-7"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.5"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <h4 className="text-base font-semibold text-slate-300">
                Awaiting Product Upload
              </h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                Upload a photograph on the left to trigger Gemini Vision analysis,
                Amazon India discovery, and match confidence ranking.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Image Preprocessing Card */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Search Session
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                    Status: {matchResult.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 block">Search UUID</span>
                    <span className="font-mono text-slate-300 break-all select-all">
                      {matchResult.search_id}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 block">Candidate Pool</span>
                    <span className="text-amber-400 font-medium">
                      {matchResult.candidates.length} Discovered on Amazon.in
                    </span>
                  </div>
                </div>
              </div>

              {/* Gemini Vision Extracted Attributes */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Extracted Visual Attributes
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                    Gemini Vision
                  </span>
                </div>

                <AnalysisStatus analysis={matchResult.analysis} searchId={matchResult.search_id} />
              </div>

              {/* Amazon.in Discovered Candidates & Confirmation (Phase 7) */}
              <CandidateList
                candidates={matchResult.candidates}
                selectedAsin={matchResult.selected_asin}
                onConfirmCandidate={handleConfirmCandidate}
                searchId={matchResult.search_id}
                onReset={handleReset}
                totalCandidates={matchResult.total_candidates}
                totalSellers={matchResult.total_sellers}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
