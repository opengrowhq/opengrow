"use client";

import { useState } from "react";
import { type TrackingStatus } from "../api";
import {
  conversionFetchSnippet,
  trackingPixelSnippet,
} from "../tracking-snippet.mjs";
import {
  trackingStatusDetail,
  trackingStatusLabel,
  trackingStatusTone,
} from "../tracking-status.mjs";
import { API_BASE } from "@/lib/http";

const conversionTypes = ["signup", "lead", "customer", "revenue"] as const;

export function TrackingStatusCard({
  status,
  tenantSlug,
}: {
  status?: TrackingStatus;
  tenantSlug: string;
}) {
  const [contentPieceId, setContentPieceId] = useState("");
  const [conversionType, setConversionType] =
    useState<(typeof conversionTypes)[number]>("lead");
  const pixel = trackingPixelSnippet(API_BASE, tenantSlug, contentPieceId);
  const conversion = conversionFetchSnippet(
    API_BASE,
    tenantSlug,
    contentPieceId,
    conversionType,
  );
  const tone = trackingStatusTone(status);

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Tracking</h2>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
            tone === "installed"
              ? "bg-emerald-50 text-emerald-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {trackingStatusLabel(status)}
        </span>
      </div>
      <p className="mt-2 text-xs text-gray-400">{trackingStatusDetail(status)}</p>
      {status?.last_seen_at && (
        <p className="mt-1 text-xs text-gray-400">
          Last seen {new Date(status.last_seen_at).toLocaleDateString()}
        </p>
      )}
      <div className="mt-4 space-y-3">
        <input
          value={contentPieceId}
          onChange={(e) => setContentPieceId(e.target.value)}
          placeholder="Content piece ID (optional)"
          className="w-full rounded-full border border-gray-500 bg-white px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <div className="grid grid-cols-4 gap-2">
          {conversionTypes.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setConversionType(item)}
              className={`h-9 rounded-full text-xs font-semibold capitalize ${
                conversionType === item
                  ? "bg-interactive text-white"
                  : "border border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
        <SnippetBox label="Pixel" value={pixel} />
        <SnippetBox label="Conversion" value={conversion} />
      </div>
    </section>
  );
}

function SnippetBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase text-gray-400">{label}</p>
        <button
          type="button"
          onClick={() => navigator.clipboard?.writeText(value)}
          className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-600 shadow-sm hover:text-gray-950"
        >
          Copy
        </button>
      </div>
      <textarea
        readOnly
        value={value}
        rows={label === "Pixel" ? 3 : 7}
        className="w-full resize-none rounded-xl border border-gray-500 bg-white p-3 font-mono text-[11px] leading-5 text-gray-600 outline-none"
      />
    </div>
  );
}
