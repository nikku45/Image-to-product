"use client";

import React, { useState, useMemo } from "react";
import { ProductCandidate } from "@/types/product";
import CandidateCard from "./CandidateCard";

interface CandidateListProps {
  candidates: ProductCandidate[];
  selectedAsin?: string | null;
  onConfirmCandidate: (asin: string) => Promise<void>;
  searchId: string;
  onReset: () => void;
  totalCandidates?: number;
  totalSellers?: number;
}

export default function CandidateList({
  candidates,
  selectedAsin,
  onConfirmCandidate,
  searchId,
  onReset,
  totalCandidates,
  totalSellers,
}: CandidateListProps) {
  const [confirmingAsin, setConfirmingAsin] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const handleConfirm = async (asin: string) => {
    setConfirmError(null);
    setConfirmingAsin(asin);
    try {
      await onConfirmCandidate(asin);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setConfirmError(err.message);
      } else {
        setConfirmError("Failed to confirm candidate ASIN");
      }
    } finally {
      setConfirmingAsin(null);
    }
  };

  const topCandidate = candidates.length > 0 ? candidates[0] : null;
  const isLowConfidence =
    topCandidate && (topCandidate.match_confidence === "low" || topCandidate.match_score < 0.6);

  const confirmedCandidate = candidates.find((c) => c.asin === selectedAsin);

  // Derive unique seller count from unique ASINs in candidates if not provided from API
  const derivedTotalSellers = useMemo(() => {
    if (totalSellers !== undefined && totalSellers > 0) return totalSellers;
    const uniqueAsins = new Set(candidates.map((c) => c.asin));
    return uniqueAsins.size;
  }, [candidates, totalSellers]);

  const derivedTotalCandidates = totalCandidates ?? candidates.length;

  // Confidence tier breakdown
  const confidenceTiers = useMemo(() => {
    const high = candidates.filter((c) => c.match_confidence === "high");
    const medium = candidates.filter((c) => c.match_confidence === "medium");
    const low = candidates.filter((c) => c.match_confidence === "low");
    return { high, medium, low };
  }, [candidates]);

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-white">Amazon.in Candidates</h3>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {candidates.length} Discovered
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            All matching products from Amazon.in, ranked by explainable multi-signal visual attribute comparison
          </p>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Upload Another Photo
        </button>
      </div>

      {/* ═══ Marketplace Competition Summary ═══ */}
      {candidates.length > 0 && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-950/60 border border-indigo-500/20 space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-indigo-500/20 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
              Marketplace Competition Summary
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Total Products Found */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
              <span className="text-slate-500 text-[11px] block mb-1">Total Products</span>
              <span className="text-2xl font-bold text-white">{derivedTotalCandidates}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">matching listings</span>
            </div>

            {/* Unique Sellers */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-indigo-500/20 text-center">
              <span className="text-slate-500 text-[11px] block mb-1">Unique Sellers</span>
              <span className="text-2xl font-bold text-indigo-400">{derivedTotalSellers}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">distinct sellers</span>
            </div>

            {/* High Confidence Matches */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
              <span className="text-slate-500 text-[11px] block mb-1">High Confidence</span>
              <span className="text-2xl font-bold text-emerald-400">{confidenceTiers.high.length}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">score ≥ 85%</span>
            </div>

            {/* Medium / Low Confidence */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
              <span className="text-slate-500 text-[11px] block mb-1">Med / Low</span>
              <div className="flex items-center justify-center gap-1.5">
                <span className="text-lg font-bold text-amber-400">{confidenceTiers.medium.length}</span>
                <span className="text-slate-600">/</span>
                <span className="text-lg font-bold text-rose-400">{confidenceTiers.low.length}</span>
              </div>
              <span className="text-[10px] text-slate-400 block mt-0.5">other matches</span>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
            <svg className="w-3 h-3 text-slate-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Unique sellers count is derived from the total number of unique product listings (ASINs) — each unique listing implies a distinct seller offering.
          </p>
        </div>
      )}

      {/* Confirmation Success Callout */}
      {confirmedCandidate && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 flex items-start gap-3 text-xs">
          <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div className="flex-1 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-300 text-sm">
                Candidate ASIN Confirmed
              </span>
              <span className="font-mono text-emerald-400 font-semibold">{confirmedCandidate.asin}</span>
            </div>
            <p className="text-emerald-200/80">
              The listing has been confirmed as the verified match. You can now track pricing, inventory, and competitive catalog data.
            </p>
          </div>
        </div>
      )}

      {/* Low Confidence Warning Callout */}
      {isLowConfidence && !selectedAsin && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/30 flex items-start gap-3 text-xs text-amber-200">
          <span className="text-lg leading-none">⚠️</span>
          <div>
            <span className="font-bold block text-amber-300">
              Provisional Match: Low Confidence
            </span>
            <p className="text-amber-200/80 mt-0.5">
              Top candidate score is below 60%. Please verify packaging text, model number, and variant details on Amazon.in before confirming.
            </p>
          </div>
        </div>
      )}

      {/* Error Message for Confirmation */}
      {confirmError && (
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-xs text-rose-300 flex items-center justify-between">
          <span>{confirmError}</span>
          <button
            type="button"
            onClick={() => setConfirmError(null)}
            className="text-rose-400 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* ═══ ALL Candidate Cards ═══ */}
      {candidates.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="w-12 h-12 mx-auto rounded-full bg-slate-800/80 flex items-center justify-center text-slate-500">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h4 className="text-sm font-semibold text-slate-200">
            No Matching Amazon.in Listings Found
          </h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The generated search queries did not yield organic product listings on Amazon.in. Try uploading a clearer image showing product labels, brand names, or model numbers.
          </p>
          <button
            type="button"
            onClick={onReset}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
          >
            Upload Different Image
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {candidates.map((candidate, idx) => (
            <CandidateCard
              key={candidate.asin}
              candidate={candidate}
              rank={idx + 1}
              isConfirmed={selectedAsin === candidate.asin}
              onConfirm={handleConfirm}
              confirmLoading={confirmingAsin === candidate.asin}
            />
          ))}

          {/* Summary footer */}
          <div className="text-center text-[11px] text-slate-500 pt-2 border-t border-slate-800/50">
            {derivedTotalCandidates} product listing{derivedTotalCandidates !== 1 ? "s" : ""} from SerpApi •{" "}
            {derivedTotalSellers} unique seller{derivedTotalSellers !== 1 ? "s" : ""} (by unique ASIN)
          </div>
        </div>
      )}
    </div>
  );
}
