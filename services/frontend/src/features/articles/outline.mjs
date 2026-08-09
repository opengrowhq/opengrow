export function parseOutline(text) {
  const sections = [];
  for (const rawLine of String(text ?? "").split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading) {
      sections.push({ heading: heading[1].trim(), points: [] });
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet && sections.length) sections[sections.length - 1].points.push(bullet[1].trim());
  }
  return sections;
}

export function serializeOutline(sections) {
  return (sections ?? [])
    .map((s) => [`## ${s.heading}`, ...(s.points ?? []).map((p) => `- ${p}`)].join("\n"))
    .join("\n\n");
}

export function moveSection(sections, from, to) {
  const next = [...(sections ?? [])];
  if (from < 0 || to < 0 || from >= next.length || to >= next.length) return next;
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}
