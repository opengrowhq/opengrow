import { OnboardingFlow } from "@/features/brand";

export default async function TenantOnboardingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <OnboardingFlow slug={slug} />;
}
