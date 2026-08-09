import { ContentCalendar } from "@/features/content";

export default async function TenantCalendarPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <ContentCalendar slug={slug} />;
}
