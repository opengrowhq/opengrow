"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Badge } from "@/components/ui/data-display";
import { useCreateInvite, useInvites, useMembers, useRemoveMember, useRevokeInvite } from "../hooks";

export function TeamCard() {
  const { data: members, isLoading: membersLoading } = useMembers();
  const { data: invites, isLoading: invitesLoading } = useInvites();
  const createInvite = useCreateInvite();
  const revokeInvite = useRevokeInvite();
  const removeMember = useRemoveMember();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"member" | "admin">("member");
  const [notice, setNotice] = useState<string | null>(null);

  function onInvite(e: React.FormEvent) {
    e.preventDefault();
    setNotice(null);
    createInvite.mutate(
      { email, role },
      {
        onSuccess: () => {
          setEmail("");
          setNotice(`Invite sent to ${email}.`);
        },
      },
    );
  }

  const pendingInvites = (invites ?? []).filter((i) => i.status === "PENDING");
  const error =
    (createInvite.error instanceof Error ? createInvite.error.message : null) ??
    (revokeInvite.error instanceof Error ? revokeInvite.error.message : null) ??
    (removeMember.error instanceof Error ? removeMember.error.message : null);

  return (
    <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
      <div>
        <h2 className="text-sm font-black text-gray-900">Team</h2>
        <p className="mt-1 text-xs font-medium text-gray-500">
          Invite teammates to this workspace.
        </p>
      </div>

      <form onSubmit={onInvite} className="mt-4 flex flex-wrap items-end gap-2">
        <div className="min-w-[220px] flex-1">
          <Field label="Email">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="teammate@company.com"
            />
          </Field>
        </div>
        <div>
          <Field label="Role">
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as "member" | "admin")}
              className="h-11 rounded-xl border border-gray-300 px-3 text-sm font-medium"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
          </Field>
        </div>
        <Button type="submit" loading={createInvite.isPending}>
          {createInvite.isPending ? "Sending…" : "Send invite"}
        </Button>
      </form>

      {notice && (
        <p className="mt-3 rounded-xl border border-green-100 bg-green-50 px-3 py-2 text-xs font-semibold text-green-700">
          {notice}
        </p>
      )}
      {error && (
        <p className="mt-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6">
        <h3 className="text-xs font-black uppercase tracking-wide text-gray-500">
          Members
        </h3>
        {membersLoading && !members && (
          <p className="mt-2 text-xs font-medium text-gray-400">Loading…</p>
        )}
        <ul className="mt-2 space-y-1">
          {(members ?? []).map((m) => (
            <li
              key={m.id}
              className="flex items-center justify-between gap-2 rounded-xl border border-gray-100 px-3 py-2 text-sm"
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900">{m.display_name}</span>
                <span className="text-xs font-medium text-gray-500">{m.email}</span>
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => removeMember.mutate(m.id)}
                loading={removeMember.isPending}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      </div>

      {!invitesLoading && pendingInvites.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-black uppercase tracking-wide text-gray-500">
            Pending invites
          </h3>
          <ul className="mt-2 space-y-1">
            {pendingInvites.map((i) => (
              <li
                key={i.id}
                className="flex items-center justify-between gap-2 rounded-xl border border-gray-100 px-3 py-2 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">{i.email}</span>
                  <Badge tone="neutral">{i.role.toUpperCase()}</Badge>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => revokeInvite.mutate(i.id)}
                  loading={revokeInvite.isPending}
                >
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
