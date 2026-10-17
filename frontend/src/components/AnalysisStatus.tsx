"use client";

import React from "react";
import { ImageAnalysis } from "@/types/product";

interface AnalysisStatusProps {
  analysis: ImageAnalysis | null;
  searchId: string;
}

export default function AnalysisStatus({ analysis, searchId }: AnalysisStatusProps) {
  if (!analysis) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 text-sm">
        No vision analysis data available.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Primary Extracted Entity Tags */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
            Category
          </span>
          <span className="text-sm font-semibold text-slate-200 capitalize mt-0.5 block truncate">
            {analysis.product_category || "Unclassified"}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
            Brand
          </span>
          <span className={`text-sm font-semibold mt-0.5 block truncate ${analysis.brand ? "text-emerald-400" : "text-slate-500 italic"}`}>
            {analysis.brand || "Unspecified"}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
            Model
          </span>
          <span className={`text-sm font-semibold mt-0.5 block truncate ${analysis.model ? "text-indigo-400" : "text-slate-500 italic"}`}>
            {analysis.model || "Unspecified"}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
            Color
          </span>
          <span className={`text-sm font-semibold mt-0.5 block truncate capitalize ${analysis.color ? "text-slate-200" : "text-slate-500 italic"}`}>
            {analysis.color || "Unspecified"}
          </span>
        </div>
      </div>

      {/* Visible Text Badges */}
      {analysis.visible_text && analysis.visible_text.length > 0 && (
        <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400">
            <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
            </svg>
            Visible Packaging & Product Text
          </div>
          <div className="flex flex-wrap gap-1.5">
            {analysis.visible_text.map((text, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded-md text-xs font-mono bg-indigo-950/50 border border-indigo-800/60 text-indigo-300"
              >
                "{text}"
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Physical Attributes & Identifying Features */}
      {analysis.identifying_attributes && analysis.identifying_attributes.length > 0 && (
        <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400">
            <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Visual Attributes Identified
          </div>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs text-slate-300">
            {analysis.identifying_attributes.map((attr, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-emerald-400 mt-0.5">•</span>
                <span>{attr}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Search Queries Generated */}
      {analysis.search_queries && analysis.search_queries.length > 0 && (
        <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
            <span className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Amazon.in Search Queries Dispatched
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              Max 3 queries bounded
            </span>
          </div>
          <div className="space-y-1">
            {analysis.search_queries.map((q, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300"
              >
                <span className="w-4 h-4 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[10px] shrink-0">
                  {idx + 1}
                </span>
                <span className="truncate">{q}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ambiguities / Uncertainties */}
      {analysis.uncertainties && analysis.uncertainties.length > 0 && (
        <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-900/40 space-y-1 text-xs">
          <span className="font-semibold text-amber-400 block">
            Uncertainties Noted by Vision AI
          </span>
          <ul className="space-y-0.5 text-slate-400">
            {analysis.uncertainties.map((u, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-amber-500 mt-0.5">-</span>
                <span>{u}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
