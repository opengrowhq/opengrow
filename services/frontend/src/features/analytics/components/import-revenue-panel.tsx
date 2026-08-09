"use client";

import { useState } from "react";
import { type AnalyticsImportProvider, type AnalyticsImportRow } from "../api";
import { useCreateRevenueEvent, useImportAnalyticsEvents } from "../hooks";
import { cleanImportRow, dollarsToCents } from "../import-form.mjs";

const revenueEventTypes = ["signup", "lead", "customer", "revenue"] as const;

export function ImportRevenuePanel() {
  return (
    <>
      <AnalyticsImportPanel />
      <ManualRevenueEventPanel />
    </>
  );
}

function AnalyticsImportPanel() {
  const importEvents = useImportAnalyticsEvents();
  const [provider, setProvider] = useState<AnalyticsImportProvider>("manual");
  const [contentPieceId, setContentPieceId] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [channel, setChannel] = useState("");
  const [visits, setVisits] = useState("");
  const [signups, setSignups] = useState("");
  const [leads, setLeads] = useState("");
  const [customers, setCustomers] = useState("");
  const [revenue, setRevenue] = useState("");
  const [currency, setCurrency] = useState("USD");

  const row = cleanImportRow({
    content_piece_id: contentPieceId,
    source_url: sourceUrl,
    channel,
    visits,
    signups,
    leads,
    customers,
    revenue,
    currency,
  }) as AnalyticsImportRow;
  const hasMetrics = Boolean(
    row.visits ||
      row.signups ||
      row.leads ||
      row.customers ||
      row.revenue_cents,
  );

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasMetrics) return;
    importEvents.mutate(
      {
        provider,
        rows: [row],
      },
      {
        onSuccess: () => {
          setSourceUrl("");
          setChannel("");
          setVisits("");
          setSignups("");
          setLeads("");
          setCustomers("");
          setRevenue("");
        },
      },
    );
  }

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Import metrics</h2>
        {importEvents.data && (
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            Saved
          </span>
        )}
      </div>
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <div className="grid grid-cols-3 gap-2">
          {(["manual", "ga4", "gsc"] as AnalyticsImportProvider[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setProvider(item)}
              className={`h-9 rounded-full text-xs font-semibold uppercase ${
                provider === item
                  ? "bg-interactive text-white"
                  : "border border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
        <input
          value={contentPieceId}
          onChange={(e) => setContentPieceId(e.target.value)}
          placeholder="Content piece ID (optional)"
          className="w-full rounded-full border border-gray-500 bg-white px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <input
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="Source URL"
          className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <input
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
          placeholder="Channel"
          className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <div className="grid grid-cols-2 gap-2">
          <MetricInput label="Visits" value={visits} onChange={setVisits} />
          <MetricInput label="Signups" value={signups} onChange={setSignups} />
          <MetricInput label="Leads" value={leads} onChange={setLeads} />
          <MetricInput label="Customers" value={customers} onChange={setCustomers} />
        </div>
        <div className="grid grid-cols-[minmax(0,1fr)_86px] gap-2">
          <input
            value={revenue}
            onChange={(e) => setRevenue(e.target.value)}
            inputMode="decimal"
            placeholder="Revenue"
            className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
          />
          <input
            value={currency}
            onChange={(e) => setCurrency(e.target.value.slice(0, 3).toUpperCase())}
            placeholder="USD"
            className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm uppercase outline-none focus:border-gray-700"
          />
        </div>
        {importEvents.error && (
          <p className="rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
            {importEvents.error instanceof Error
              ? importEvents.error.message
              : "Import failed"}
          </p>
        )}
        <button
          type="submit"
          disabled={importEvents.isPending || !hasMetrics}
          className="h-11 w-full rounded-full bg-gray-950 text-sm font-semibold text-white shadow-sm disabled:opacity-50"
        >
          Import
        </button>
      </form>
    </section>
  );
}

function ManualRevenueEventPanel() {
  const createRevenueEvent = useCreateRevenueEvent();
  const [eventType, setEventType] =
    useState<(typeof revenueEventTypes)[number]>("revenue");
  const [contentPieceId, setContentPieceId] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [channel, setChannel] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");

  const amountCentsValue = dollarsToCents(amount);
  const hasMeaningfulField = Boolean(
    amountCentsValue ||
      contentPieceId.trim() ||
      sourceUrl.trim() ||
      channel.trim(),
  );

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasMeaningfulField) return;
    const amountCents = dollarsToCents(amount);
    createRevenueEvent.mutate(
      {
        event_type: eventType,
        content_piece_id: contentPieceId.trim() || undefined,
        source_url: sourceUrl.trim() || undefined,
        channel: channel.trim() || undefined,
        amount_cents: amountCents || undefined,
        currency: currency.trim().toUpperCase() || undefined,
      },
      {
        onSuccess: () => {
          setContentPieceId("");
          setSourceUrl("");
          setChannel("");
          setAmount("");
        },
      },
    );
  }

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Revenue event</h2>
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <div className="grid grid-cols-4 gap-2">
          {revenueEventTypes.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setEventType(item)}
              className={`h-9 rounded-full text-xs font-semibold capitalize ${
                eventType === item
                  ? "bg-interactive text-white"
                  : "border border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
        <input
          value={contentPieceId}
          onChange={(e) => setContentPieceId(e.target.value)}
          placeholder="Content piece ID (optional)"
          className="w-full rounded-full border border-gray-500 bg-white px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <input
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="Source URL"
          className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <input
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
          placeholder="Channel"
          className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <div className="grid grid-cols-[minmax(0,1fr)_86px] gap-2">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            inputMode="decimal"
            placeholder="Amount"
            className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
          />
          <input
            value={currency}
            onChange={(e) => setCurrency(e.target.value.slice(0, 3).toUpperCase())}
            placeholder="USD"
            className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm uppercase outline-none focus:border-gray-700"
          />
        </div>
        {createRevenueEvent.error && (
          <p className="rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
            {createRevenueEvent.error instanceof Error
              ? createRevenueEvent.error.message
              : "Revenue event save failed"}
          </p>
        )}
        <button
          type="submit"
          disabled={createRevenueEvent.isPending || !hasMeaningfulField}
          className="h-11 w-full rounded-full bg-gray-950 text-sm font-semibold text-white shadow-sm disabled:opacity-50"
        >
          Save revenue event
        </button>
      </form>
    </section>
  );
}

function MetricInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      inputMode="numeric"
      placeholder={label}
      className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
    />
  );
}
