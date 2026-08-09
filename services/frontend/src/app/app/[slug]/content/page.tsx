import { ContentList } from "@/features/content";

export default async function TenantContentPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <ContentList slug={slug} />;
}
