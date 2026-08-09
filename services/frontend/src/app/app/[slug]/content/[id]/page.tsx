import { ContentEditor } from "@/features/content";

export default async function TenantContentDetailPage({
  params,
}: {
  params: Promise<{ slug: string; id: string }>;
}) {
  const { slug, id } = await params;
  return <ContentEditor id={id} slug={slug} />;
}
