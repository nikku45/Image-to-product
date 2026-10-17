"use client";

import React, { useState } from "react";
import { ProductCandidate } from "@/types/product";

interface CandidateCardProps {
  candidate: ProductCandidate;
  rank: number;
  isConfirmed: boolean;
  onConfirm: (asin: string) => Promise<void>;
  confirmLoading: boolean;
}

export default function CandidateCard({
  candidate,
  rank,
  isConfirmed,
  onConfirm,
  confirmLoading,
}: CandidateCardProps) {
  const [showSignals, setShowSignals] = useState(false);
  const [copiedAsin, setCopiedAsin] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleCopyAsin = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(candidate.asin);
    setCopiedAsin(true);
    setTimeout(() => setCopiedAsin(false), 2000);
  };

  const confidenceStyles = {
    high: {
      badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
      bar: "bg-emerald-500",
      label: "High Confidence",
    },
    medium: {
      badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
      bar: "bg-amber-500",
      label: "Medium Confidence",
    },
    low: {
      badge: "bg-rose-500/15 text-rose-400 border-rose-500/30",
      bar: "bg-rose-500",
      label: "Low Confidence",
    },
  }[candidate.match_confidence];

  const scorePercentage = Math.round(candidate.match_score * 100);

  // Format retrieval time
  const formattedTime = (() => {
    try {
      return new Date(candidate.retrieved_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return candidate.retrieved_at;
    }
  })();

  const signals = candidate.match_signals as Record<string, any> | undefined;

  return (
    <div
      className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
        isConfirmed
          ? "bg-slate-900 border-emerald-500/60 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/40"
          : "bg-slate-900/90 border-slate-800 hover:border-slate-700 shadow-md"
      }`}
    >
      {/* Top Banner with Rank and Confirmation Status */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center gap-2">
          <span
            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              rank === 1
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                : "bg-slate-800 text-slate-300 border border-slate-700"
            }`}
          >
            #{rank}
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {rank === 1 ? "Top Recommendation" : `Candidate #${rank}`}
          </span>
        </div>

        {isConfirmed ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
            </svg>
            Confirmed Match
          </span>
        ) : (
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${confidenceStyles.badge}`}
          >
            {confidenceStyles.label} ({scorePercentage}%)
          </span>
        )}
      </div>

      <div className="p-5 space-y-4">
        {/* Main Product Info: Image + Title + ASIN */}
        <div className="flex gap-4 items-start">
          {/* Product Thumbnail */}
          <div className="w-24 h-24 rounded-xl bg-slate-950 border border-slate-800 flex-shrink-0 overflow-hidden flex items-center justify-center p-1.5 relative group">
            {candidate.image_url && !imageError ? (
              <img
                src={candidate.image_url}
                alt={candidate.title}
                onError={() => setImageError(true)}
                className="w-full h-full object-contain group-hover:scale-105 transition-transform"
              />
            ) : (
              <div className="text-slate-600 text-center text-xs flex flex-col items-center gap-1">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.5"
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <span>No Photo</span>
              </div>
            )}
          </div>

          {/* Details */}
          <div className="flex-1 min-w-0 space-y-2">
            <h4
              className="text-sm font-semibold text-slate-100 line-clamp-2 hover:text-amber-400 transition-colors"
              title={candidate.title}
            >
              {candidate.title}
            </h4>

            {/* ASIN + Copy + Amazon Link */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="inline-flex items-center gap-1.5 bg-slate-950 border border-slate-800 rounded-md px-2 py-1 font-mono text-slate-300">
                <span className="text-slate-500">ASIN:</span>
                <span className="font-semibold text-amber-300">{candidate.asin}</span>
                <button
                  type="button"
                  onClick={handleCopyAsin}
                  className="text-slate-400 hover:text-white transition-colors ml-1"
                  title="Copy ASIN"
                >
                  {copiedAsin ? (
                    <span className="text-emerald-400 font-sans text-[10px]">Copied</span>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                  )}
                </button>
              </div>

              <a
                href={candidate.product_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 hover:underline transition-colors px-2 py-1 rounded bg-sky-950/30 border border-sky-800/40"
              >
                <span>View on Amazon.in</span>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          </div>
        </div>

        {/* Marketplace Metrics: Price & Seller Count (Phase 6 Compliance) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs">
          {/* Listed Price */}
          <div>
            <span className="text-slate-500 block mb-0.5">Listed Price</span>
            {candidate.price_amount !== null ? (
              <span className="text-base font-bold text-emerald-400">
                ₹{candidate.price_amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 font-medium">
                Unavailable
              </span>
            )}
          </div>

          {/* Seller Count (Explicitly Unavailable per ADR-004) */}
          <div>
            <div className="flex items-center gap-1 mb-0.5">
              <span className="text-slate-500">Seller Count</span>
              <span
                className="text-slate-500 hover:text-slate-300 cursor-help"
                title="SerpApi organic search results do not expose seller count per ADR-004 specification."
              >
                ⓘ
              </span>
            </div>
            {candidate.seller_count !== null ? (
              <span className="text-sm font-semibold text-white">{candidate.seller_count} sellers</span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-950/30 text-amber-400 border border-amber-900/40 font-medium">
                Unavailable
              </span>
            )}
          </div>

          {/* Retrieved Timestamp */}
          <div className="col-span-2 sm:col-span-1">
            <span className="text-slate-500 block mb-0.5">Retrieved At</span>
            <span className="text-slate-300 font-mono text-[11px]" title={candidate.retrieved_at}>
              {formattedTime} UTC
            </span>
          </div>
        </div>

        {/* Match Score Meter */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Attribute Match Score</span>
            <span className="font-semibold text-slate-200">{scorePercentage}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${confidenceStyles.bar}`}
              style={{ width: `${Math.max(scorePercentage, 4)}%` }}
            />
          </div>
        </div>

        {/* Explainable Match Signals Collapsible Section */}
        {signals && (
          <div className="border-t border-slate-800/80 pt-3">
            <button
              type="button"
              onClick={() => setShowSignals(!showSignals)}
              className="flex items-center justify-between w-full text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              <span className="font-medium flex items-center gap-1.5">
                <svg
                  className={`w-3.5 h-3.5 transition-transform ${showSignals ? "rotate-90" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                </svg>
                Explainable Match Breakdown
              </span>
              <span className="text-[11px] text-slate-500">
                {showSignals ? "Hide signals" : "View weights & signals"}
              </span>
            </button>

            {showSignals && (
              <div className="mt-3 p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2 text-xs">
                {/* Brand */}
                {signals.brand && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Brand Match (25% weight):</span>
                    <span
                      className={`font-medium ${
                        signals.brand.status === "exact_match"
                          ? "text-emerald-400"
                          : signals.brand.status === "conflict"
                          ? "text-rose-400"
                          : "text-slate-400"
                      }`}
                    >
                      {signals.brand.status === "exact_match"
                        ? "✓ Verified Match"
                        : signals.brand.status === "conflict"
                        ? "⚠ Brand Conflict"
                        : "Unknown"}
                    </span>
                  </div>
                )}

                {/* Model */}
                {signals.model && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Model Match (30% weight):</span>
                    <span
                      className={`font-medium ${
                        signals.model.status === "exact_match"
                          ? "text-emerald-400"
                          : signals.model.status === "partial_match"
                          ? "text-amber-400"
                          : signals.model.status === "conflict"
                          ? "text-rose-400"
                          : "text-slate-400"
                      }`}
                    >
                      {signals.model.status === "exact_match"
                        ? "✓ Exact Model"
                        : signals.model.status === "partial_match"
                        ? "~ Partial Model"
                        : signals.model.status === "conflict"
                        ? "⚠ Model Conflict"
                        : "Unknown"}
                    </span>
                  </div>
                )}

                {/* Category */}
                {signals.category && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Category (15% weight):</span>
                    <span
                      className={`font-medium ${
                        signals.category.status === "match"
                          ? "text-emerald-400"
                          : signals.category.status === "partial"
                          ? "text-amber-400"
                          : "text-slate-400"
                      }`}
                    >
                      {signals.category.status === "match"
                        ? "✓ Match"
                        : signals.category.status === "partial"
                        ? "~ Partial Match"
                        : "Unknown"}
                    </span>
                  </div>
                )}

                {/* Variant Attributes */}
                {signals.variant && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Variant Attributes (20% weight):</span>
                    <span className="text-slate-300 font-medium">
                      {Array.isArray(signals.variant.sub_signals)
                        ? `${signals.variant.sub_signals.filter((s: any) => s.status === "match").length}/${signals.variant.sub_signals.length} matched`
                        : "Evaluated"}
                    </span>
                  </div>
                )}

                {/* Penalties */}
                {Array.isArray(signals.applied_penalties) && signals.applied_penalties.length > 0 && (
                  <div className="pt-1.5 border-t border-slate-800 text-rose-400">
                    <span className="font-semibold block mb-0.5">Applied Penalties:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                      {signals.applied_penalties.map((p: any, idx: number) => (
                        <li key={idx}>
                          {p.reason} ({Math.round(p.factor * 100)}% multiplier)
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Confirmation Button */}
        <div className="pt-2">
          {isConfirmed ? (
            <button
              type="button"
              disabled
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center justify-center gap-2 cursor-default"
            >
              <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
              </svg>
              Selected as Verified Match
            </button>
          ) : (
            <button
              type="button"
              disabled={confirmLoading}
              onClick={() => onConfirm(candidate.asin)}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 shadow-md shadow-amber-500/10 hover:shadow-amber-500/20 transition-all flex items-center justify-center gap-2 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {confirmLoading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  <span>Confirming Match...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Confirm as Correct Amazon.in Match</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
