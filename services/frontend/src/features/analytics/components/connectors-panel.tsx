"use client";

import { useState } from "react";
import { type AnalyticsConnectorInput } from "../api";
import {
  useAnalyticsConnectors,
  useCompleteGoogleConnectorOAuth,
  useCreateAnalyticsConnector,
  useDisconnectAnalyticsConnector,
  useGoogleAuthUrl,
  useSyncAnalyticsConnector,
} from "../hooks";
import { buildConnectorInput } from "../connector-form.mjs";

export function ConnectorsPanel() {
  const { data: connectors } = useAnalyticsConnectors();
  const createConnector = useCreateAnalyticsConnector();
  const disconnectConnector = useDisconnectAnalyticsConnector();
  const completeOAuth = useCompleteGoogleConnectorOAuth();
  const syncConnector = useSyncAnalyticsConnector();
  const googleAuth = useGoogleAuthUrl();
  const [provider, setProvider] = useState<"ga4" | "gsc">("ga4");
  const [displayName, setDisplayName] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const [siteUrl, setSiteUrl] = useState("");
  const [oauthCodes, setOauthCodes] = useState<Record<string, string>>({});

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    createConnector.mutate(
      buildConnectorInput({
        provider,
        display_name: displayName,
        external_property_id: propertyId,
        site_url: siteUrl,
      }) as AnalyticsConnectorInput,
      {
        onSuccess: () => {
          setDisplayName("");
          setPropertyId("");
          setSiteUrl("");
        },
      },
    );
  }

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Connectors</h2>
        <button
          type="button"
          onClick={() => googleAuth.mutate(provider)}
          className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50"
        >
          OAuth URL
        </button>
      </div>
      {googleAuth.data && (
        <div className="mt-3 rounded-2xl border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-500">
          {googleAuth.data.auth_url ? (
            <a
              href={googleAuth.data.auth_url}
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-gray-800 hover:text-interactive"
            >
              Open Google consent
            </a>
          ) : (
            googleAuth.data.message
          )}
        </div>
      )}
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {(["ga4", "gsc"] as const).map((item) => (
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
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Display name"
          className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        <input
          value={provider === "ga4" ? propertyId : siteUrl}
          onChange={(e) =>
            provider === "ga4"
              ? setPropertyId(e.target.value)
              : setSiteUrl(e.target.value)
          }
          placeholder={provider === "ga4" ? "GA4 property ID" : "Site URL"}
          className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
        />
        {createConnector.error && (
          <p className="rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
            {createConnector.error instanceof Error
              ? createConnector.error.message
              : "Connector save failed"}
          </p>
        )}
        <button
          type="submit"
          disabled={createConnector.isPending}
          className="h-11 w-full rounded-full bg-gray-950 text-sm font-semibold text-white shadow-sm disabled:opacity-50"
        >
          Save connector
        </button>
      </form>
      <div className="mt-4 space-y-2">
        {(connectors ?? []).length === 0 && (
          <p className="rounded-2xl border border-dashed border-gray-200 py-5 text-center text-xs text-gray-400">
            No connectors yet.
          </p>
        )}
        {(connectors ?? []).map((connector) => (
          <div
            key={connector.id}
            className="rounded-2xl border border-gray-100 bg-gray-50 p-3"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">
                  {connector.display_name}
                </p>
                <p className="text-xs uppercase text-gray-400">
                  {connector.provider} · {connector.status.replace("_", " ")}
                </p>
                {connector.last_sync_at && (
                  <p className="text-xs text-gray-400">
                    Synced {new Date(connector.last_sync_at).toLocaleDateString()}
                  </p>
                )}
                {connector.last_sync_error && (
                  <p className="mt-1 line-clamp-2 text-xs text-red-500">
                    {connector.last_sync_error}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => syncConnector.mutate(connector.id)}
                  disabled={
                    syncConnector.isPending || connector.status !== "CONNECTED"
                  }
                  className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-500 hover:bg-white disabled:opacity-50"
                >
                  Sync
                </button>
                <button
                  type="button"
                  onClick={() => disconnectConnector.mutate(connector.id)}
                  disabled={disconnectConnector.isPending}
                  className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-500 hover:bg-white disabled:opacity-50"
                >
                  Disconnect
                </button>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <input
                value={oauthCodes[connector.id] ?? ""}
                onChange={(e) =>
                  setOauthCodes((codes) => ({
                    ...codes,
                    [connector.id]: e.target.value,
                  }))
                }
                placeholder="OAuth code"
                className="min-w-0 flex-1 rounded-full border border-gray-500 bg-white px-3 py-2 text-xs outline-none focus:border-gray-700"
              />              <button
                type="button"
                onClick={() =>
                  completeOAuth.mutate(
                    {
                      id: connector.id,
                      code: (oauthCodes[connector.id] ?? "").trim(),
                      state: googleAuth.data?.state ?? "",
                    },
                    {
                      onSuccess: () =>
                        setOauthCodes((codes) => ({ ...codes, [connector.id]: "" })),
                    },
                  )
                }
                disabled={
                  completeOAuth.isPending ||
                  !(oauthCodes[connector.id] ?? "").trim() ||
                  !googleAuth.data?.state
                }
                title={
                  googleAuth.data?.state
                    ? undefined
                    : "Get an OAuth URL first — the code is verified against it"
                }
                className="rounded-full bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-sm disabled:opacity-50"
              >
                Complete
              </button>
            </div>
            {completeOAuth.error && (
              <p className="mt-2 rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
                {completeOAuth.error instanceof Error
                  ? completeOAuth.error.message
                  : "OAuth completion failed"}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
