/**
 * @param {{
 *   summary?: Record<string, unknown>,
 *   topContent?: Array<Record<string, unknown>>,
 *   topChannels?: Array<Record<string, unknown>>,
 *   trackingStatus?: Record<string, unknown>
 * }} input
 */
export function attributionRecommendations({
  summary,
  topContent = [],
  topChannels = [],
  trackingStatus,
}) {
  const recommendations = [];
  const visits = Number(summary?.visits ?? 0);
  const leads = Number(summary?.leads ?? 0);
  const customers = Number(summary?.customers ?? 0);
  const revenue = Number(summary?.revenue_cents ?? 0);
  const winner = topContent.find((item) => Number(item.events ?? 0) > 0);
  const channel = topChannels.find((item) => Number(item.events ?? 0) > 0);

  if (!trackingStatus?.installed) {
    recommendations.push({
      title: "Install first-party tracking",
      detail: "Add the pixel and one conversion example before judging content.",
      tone: "urgent",
    });
  }

  if (winner) {
    recommendations.push({
      title: `Scale ${winner.title}`,
      detail: `${winner.leads ?? 0} leads, ${winner.customers ?? 0} customers, ${winner.events ?? 0} events.`,
      tone: "growth",
    });
  }

  if (visits > 0 && leads === 0) {
    recommendations.push({
      title: "Tighten the page offer",
      detail: "Traffic is landing, but no leads have been attributed yet.",
      tone: "warning",
    });
  } else if (leads > 0 && customers === 0) {
    recommendations.push({
      title: "Improve lead follow-up",
      detail: "Leads exist, but no customer events have been attributed yet.",
      tone: "warning",
    });
  } else if (customers > 0 && revenue === 0) {
    recommendations.push({
      title: "Track revenue events",
      detail: "Customer events exist, but revenue is not attached yet.",
      tone: "warning",
    });
  }

  if (channel) {
    recommendations.push({
      title: `Review ${channel.channel.replace("_", " ")}`,
      detail: `${channel.visits ?? 0} visits, ${channel.leads ?? 0} leads, ${channel.customers ?? 0} customers.`,
      tone: "neutral",
    });
  }

  if (recommendations.length === 0) {
    recommendations.push({
      title: "Create the first signal",
      detail: "Publish a page, install tracking, then import or capture conversions.",
      tone: "neutral",
    });
  }

  return recommendations.slice(0, 3);
}
