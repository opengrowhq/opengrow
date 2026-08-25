import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    listMembers: vi.fn(),
    listInvites: vi.fn(),
    createInvite: vi.fn(),
    revokeInvite: vi.fn(),
    removeMember: vi.fn(),
  };
});

import { listMembers, listInvites, createInvite, revokeInvite, removeMember } from "../api";
import { TeamCard } from "./team-card";

const listMembersMock = vi.mocked(listMembers);
const listInvitesMock = vi.mocked(listInvites);
const createInviteMock = vi.mocked(createInvite);
const revokeInviteMock = vi.mocked(revokeInvite);
const removeMemberMock = vi.mocked(removeMember);

const members = [{ id: "u1", email: "owner@acme.com", display_name: "Owner" }];
const pendingInvite = {
  id: "inv1",
  email: "new@acme.com",
  role: "member",
  status: "PENDING",
  expires_at: "2026-09-01T00:00:00Z",
};

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TeamCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("opengrow.token", "test-token");
  listMembersMock.mockResolvedValue(members);
  listInvitesMock.mockResolvedValue([]);
});

describe("TeamCard", () => {
  it("lists current members", async () => {
    renderCard();
    expect(await screen.findByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("owner@acme.com")).toBeInTheDocument();
  });

  it("sends an invite and shows a confirmation", async () => {
    const user = userEvent.setup();
    createInviteMock.mockResolvedValue(pendingInvite);
    renderCard();

    await screen.findByText("Owner");
    const emailInput = document.querySelector('input[type="email"]') as HTMLInputElement;
    await user.type(emailInput, "new@acme.com");
    await user.click(screen.getByRole("button", { name: /send invite/i }));

    await waitFor(() => {
      expect(createInviteMock).toHaveBeenCalledWith("new@acme.com", "member");
      expect(screen.getByText("Invite sent to new@acme.com.")).toBeInTheDocument();
    });
  });

  it("lists pending invites and revokes one", async () => {
    listInvitesMock.mockResolvedValue([pendingInvite]);
    revokeInviteMock.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderCard();

    expect(await screen.findByText("new@acme.com")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /revoke/i }));

    await waitFor(() => {
      expect(revokeInviteMock).toHaveBeenCalledWith("inv1");
    });
  });

  it("removes a member", async () => {
    removeMemberMock.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderCard();

    expect(await screen.findByText("Owner")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /remove/i }));

    await waitFor(() => {
      expect(removeMemberMock).toHaveBeenCalledWith("u1");
    });
  });

  it("shows the backend error when removal is rejected", async () => {
    removeMemberMock.mockRejectedValue(
      new Error("You can't remove yourself from the workspace"),
    );
    const user = userEvent.setup();
    renderCard();

    expect(await screen.findByText("Owner")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /remove/i }));

    expect(
      await screen.findByText("You can't remove yourself from the workspace"),
    ).toBeInTheDocument();
  });
});
