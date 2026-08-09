import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

type Connector = {
  id: string;
  provider: string;
  status: string;
  display_name: string;
  external_property_id: string | null;
  site_url: string | null;
  scopes: string[];
  last_sync_at: string | null;
  last_sync_error: string | null;
  metadata: unknown;
  created_at: string;
  updated_at: string;
};

const connectorFixture = (over: Partial<Connector> = {}): Connector => ({
  id: "c1",
  provider: "ga4",
  status: "CONNECTED",
  display_name: "Main GA4",
  external_property_id: "123",
  site_url: null,
  scopes: [],
  last_sync_at: null,
  last_sync_error: null,
  metadata: null,
  created_at: "",
  updated_at: "",
  ...over,
});

let connectorsData: Connector[] = [];
let googleAuthData:
  | {
      configured: boolean;
      provider: string;
      scopes: string[];
      auth_url: string | null;
      state: string | null;
      message: string | null;
    }
  | undefined;

const createMutate = vi.fn();
const disconnectMutate = vi.fn();
const syncMutate = vi.fn();
const googleAuthMutate = vi.fn();
const completeMutate = vi.fn();

vi.mock("../hooks", () => ({
  useAnalyticsConnectors: () => ({ data: connectorsData }),
  useCreateAnalyticsConnector: () => ({ mutate: createMutate, isPending: false, error: null }),
  useDisconnectAnalyticsConnector: () => ({ mutate: disconnectMutate, isPending: false }),
  useSyncAnalyticsConnector: () => ({ mutate: syncMutate, isPending: false }),
  useGoogleAuthUrl: () => ({ mutate: googleAuthMutate, data: googleAuthData, isPending: false }),
  useCompleteGoogleConnectorOAuth: () => ({ mutate: completeMutate, isPending: false }),
}));

import { ConnectorsPanel } from "./connectors-panel";

beforeEach(() => {
  connectorsData = [connectorFixture()];
  googleAuthData = undefined;
  for (const fn of [createMutate, disconnectMutate, syncMutate, googleAuthMutate, completeMutate]) {
    fn.mockClear();
  }
  // Mirror the real mutation: a successful completion clears the pasted code.
  completeMutate.mockImplementation((_vars, opts) => opts?.onSuccess?.());
});

describe("ConnectorsPanel", () => {
  it("lists existing connectors", () => {
    render(<ConnectorsPanel />);
    expect(screen.getByText(/Main GA4/)).toBeInTheDocument();
  });

  it("enables Sync for a CONNECTED connector", () => {
    render(<ConnectorsPanel />);
    expect(screen.getByRole("button", { name: "Sync" })).toBeEnabled();
  });

  it("disables Sync for a non-CONNECTED connector", () => {
    connectorsData = [connectorFixture({ status: "PENDING" })];
    render(<ConnectorsPanel />);
    expect(screen.getByRole("button", { name: "Sync" })).toBeDisabled();
  });

  it("requests an OAuth URL for the currently selected provider", async () => {
    const user = userEvent.setup();
    render(<ConnectorsPanel />);
    await user.click(screen.getByRole("button", { name: "OAuth URL" }));
    expect(googleAuthMutate).toHaveBeenCalledWith("ga4");

    await user.click(screen.getByRole("button", { name: "gsc" }));
    await user.click(screen.getByRole("button", { name: "OAuth URL" }));
    expect(googleAuthMutate).toHaveBeenCalledWith("gsc");
  });

  it("renders the Google consent link when an auth URL comes back", () => {
    googleAuthData = {
      configured: true,
      provider: "ga4",
      scopes: ["scope"],
      auth_url: "https://accounts.google.com/o/oauth2/auth?x=1",
      state: "st",
      message: null,
    };
    render(<ConnectorsPanel />);
    const link = screen.getByRole("link", { name: /open google consent/i });
    expect(link).toHaveAttribute("href", googleAuthData.auth_url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noreferrer"));
  });

  it("shows the backend message when OAuth is not configured", () => {
    googleAuthData = {
      configured: false,
      provider: "ga4",
      scopes: [],
      auth_url: null,
      state: null,
      message: "Google OAuth is not configured on this deployment.",
    };
    render(<ConnectorsPanel />);
    expect(screen.getByText(/not configured/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /open google consent/i })).not.toBeInTheDocument();
  });

  it("switches the identifier field between GA4 property ID and GSC site URL", async () => {
    const user = userEvent.setup();
    render(<ConnectorsPanel />);
    expect(screen.getByPlaceholderText("GA4 property ID")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "gsc" }));
    expect(screen.getByPlaceholderText("Site URL")).toBeInTheDocument();
  });

  it("submits the built connector payload", async () => {
    const user = userEvent.setup();
    render(<ConnectorsPanel />);
    await user.type(screen.getByPlaceholderText("Display name"), "  My GA4  ");
    await user.type(screen.getByPlaceholderText("GA4 property ID"), "123");
    await user.click(screen.getByRole("button", { name: /save connector/i }));
    expect(createMutate).toHaveBeenCalledTimes(1);
    const [payload] = createMutate.mock.calls[0];
    expect(payload.provider).toBe("ga4");
    expect(payload.display_name).toBe("My GA4");
    expect(payload.external_property_id).toBe("123");
  });

  it("completes OAuth with the pasted code and the issued state", async () => {
    const user = userEvent.setup();
    googleAuthData = {
      configured: true,
      provider: "ga4",
      scopes: [],
      auth_url: "https://accounts.google.com/o/oauth2/auth?x=1",
      state: "state-123",
      message: null,
    };
    render(<ConnectorsPanel />);
    const input = screen.getByPlaceholderText("OAuth code");
    await user.type(input, "  code-abc  ");
    await user.click(screen.getByRole("button", { name: "Complete" }));
    expect(completeMutate).toHaveBeenCalledWith(
      { id: "c1", code: "code-abc", state: "state-123" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(input).toHaveValue("");
  });

  it("keeps Complete disabled until a code is pasted and a state was issued", async () => {
    const user = userEvent.setup();
    render(<ConnectorsPanel />);
    const input = screen.getByPlaceholderText("OAuth code");
    expect(screen.getByRole("button", { name: "Complete" })).toBeDisabled();
    // A pasted code alone is not enough without an issued OAuth state.
    await user.type(input, "code-abc");
    expect(screen.getByRole("button", { name: "Complete" })).toBeDisabled();
  });

  it("disconnects a connector by id", async () => {
    const user = userEvent.setup();
    render(<ConnectorsPanel />);
    await user.click(screen.getByRole("button", { name: "Disconnect" }));
    expect(disconnectMutate).toHaveBeenCalledWith("c1");
  });

  it("surfaces a sync error on the connector card", () => {
    connectorsData = [connectorFixture({ last_sync_error: "token expired" })];
    render(<ConnectorsPanel />);
    expect(screen.getByText("token expired")).toBeInTheDocument();
  });
});
