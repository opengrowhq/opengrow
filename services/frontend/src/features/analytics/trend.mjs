export function trendLabel(delta) {
  if (!delta) return "No change";
  const absolute = Number(delta.absolute ?? 0);
  const percent = delta.percent;
  if (absolute === 0) return "No change";
  const sign = absolute > 0 ? "+" : "";
  if (percent === null || percent === undefined) {
    return `${sign}${absolute}`;
  }
  return `${sign}${absolute} (${sign}${percent}%)`;
}

export function trendTone(delta) {
  const absolute = Number(delta?.absolute ?? 0);
  if (absolute > 0) return "up";
  if (absolute < 0) return "down";
  return "flat";
}
