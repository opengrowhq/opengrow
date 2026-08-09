import { BrandPage } from "@/features/brand";

export default async function TenantBrandPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <BrandPage slug={slug} />;
}
