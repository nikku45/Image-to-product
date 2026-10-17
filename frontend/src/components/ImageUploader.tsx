"use client";

import React, { useState, useRef, DragEvent, ChangeEvent } from "react";
import { api, ApiClientError } from "@/lib/api";
import { ProductMatchResponse } from "@/types/product";

interface ImageUploaderProps {
  onUploadSuccess: (result: ProductMatchResponse, previewUrl: string) => void;
  isLoading?: boolean;
}

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function ImageUploader({
  onUploadSuccess,
  isLoading = false,
}: ImageUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return "Unsupported file type. Please upload a JPEG, PNG, or WebP image.";
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File exceeds the maximum size of ${MAX_SIZE_BYTES / (1024 * 1024)}MB.`;
    }
    if (file.size === 0) {
      return "File appears to be empty.";
    }
    return null;
  };

  const handleFileSelect = (file: File) => {
    setError(null);
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleClear = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setError(null);
    setUploading(true);

    try {
      const response = await api.createProductMatch(selectedFile);
      if (previewUrl) {
        onUploadSuccess(response, previewUrl);
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(`[${err.code}] ${err.message}`);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unknown error occurred while uploading the image.");
      }
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const busy = uploading || isLoading;

  return (
    <div className="space-y-4">
      {/* Hidden Native File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleInputChange}
        className="hidden"
        disabled={busy}
      />

      {/* Drag & Drop Box */}
      {!previewUrl ? (
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer select-none ${
            dragActive
              ? "border-orange-500 bg-orange-500/10 scale-[1.01]"
              : "border-slate-700 hover:border-orange-500/60 bg-slate-950/40 hover:bg-slate-950/80"
          }`}
        >
          <div className="mx-auto w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-400 mb-3 group-hover:text-orange-400 transition-colors shadow-inner">
            <svg
              className="w-7 h-7 text-slate-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.75"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-200">
            Click to upload, or drag & drop photograph
          </p>
          <p className="text-xs text-slate-400 mt-1">
            JPEG, PNG, or WebP up to 10 MB
          </p>
          <div className="mt-4 flex items-center justify-center gap-3 text-xs text-slate-400 font-mono">
            <span className="px-2 py-0.5 rounded bg-slate-800/80">.jpg</span>
            <span className="px-2 py-0.5 rounded bg-slate-800/80">.png</span>
            <span className="px-2 py-0.5 rounded bg-slate-800/80">.webp</span>
          </div>
        </div>
      ) : (
        /* Image Preview Card */
        <div className="border border-slate-800 rounded-2xl p-4 bg-slate-950/70 space-y-4">
          <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-slate-900 border border-slate-800 flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Selected product preview"
              className="max-h-full max-w-full object-contain"
            />
            {busy && (
              <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-xs flex flex-col items-center justify-center space-y-2 text-white">
                <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs font-medium text-slate-300">
                  Validating & Sanitizing image...
                </span>
              </div>
            )}
          </div>

          {selectedFile && (
            <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-3">
              <div className="truncate max-w-[200px] sm:max-w-xs">
                <p className="font-medium text-slate-200 truncate">
                  {selectedFile.name}
                </p>
                <p className="text-slate-500">
                  {formatFileSize(selectedFile.size)} • {selectedFile.type}
                </p>
              </div>
              <button
                type="button"
                onClick={handleClear}
                disabled={busy}
                className="px-2.5 py-1 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors disabled:opacity-50 text-xs font-medium"
              >
                Change Image
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleUpload}
            disabled={busy || !selectedFile}
            className="w-full py-3 px-4 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-orange-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Processing Image...</span>
              </>
            ) : (
              <>
                <span>Search Amazon.in Matches</span>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M14 5l7 7m0 0l-7 7m7-7H3"
                  />
                </svg>
              </>
            )}
          </button>
        </div>
      )}

      {/* Error Message Alert */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2.5">
          <svg
            className="w-4 h-4 text-rose-400 shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div className="flex-1">
            <span className="font-semibold block">Validation Error:</span>
            <span>{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
