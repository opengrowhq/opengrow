export const analyticsWindows = ["7", "30", "90", "all"];

export function analyticsWindowLabel(window) {
  if (window === "all") return "All";
  return `${window}d`;
}

export function analyticsWindowQuery(window) {
  if (!window || window === "all") return "";
  const days = Number(window);
  if (!Number.isInteger(days) || days < 1 || days > 365) return "";
  return `?days=${days}`;
}
