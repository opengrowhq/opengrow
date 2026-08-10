import { AcceptInviteForm } from "@/features/team";

export default async function AcceptInvitePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <AcceptInviteForm token={token} />;
}
