export function shortId(id) {
  return typeof id === "string" && id.length > 8 ? id.slice(0, 8) : id || "";
}

export function contentOriginLabel(content) {
  if (!content?.source_generation_id) return null;
  if (content?.format === "blog_post") return "Article draft";
  return "Generated";
}

export function lineageRows(content, draft, outline) {
  if (!content?.source_generation_id) return [];
  const rows = [
    {
      key: "draft",
      label: content.format === "blog_post" ? "Draft generation" : "Source generation",
      id: content.source_generation_id,
      status: draft?.status ?? "Loading",
      brief: draft?.brief ?? "",
    },
  ];
  const outlineId = draft?.parent_generation_id;
  if (outlineId) {
    rows.push({
      key: "outline",
      label: "Outline generation",
      id: outlineId,
      status: outline?.status ?? "Loading",
      brief: outline?.brief ?? "",
    });
  }
  return rows;
}
