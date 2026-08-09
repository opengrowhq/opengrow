import { redirect } from "next/navigation";

// The open-source self-hosted product has no marketing/pricing funnel — the
// root goes straight to sign-in. (Marketing + pricing are hosted-only surfaces
// and are not part of the open-source app.)
export default function RootPage() {
  redirect("/login");
}
