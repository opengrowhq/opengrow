export function defaultArticleBrief() {
  return {
    topic: "",
    primary_keyword: "",
    secondary_keywords: "",
    audience: "",
    goal: "educate",
    tone: "",
    length_words: 1200,
    sections_target: 5,
    notes: "",
    slug: "",
    description: "",
    tags: "",
  };
}

function parseList(value) {
  if (Array.isArray(value)) return value;
  const seen = new Set();
  const out = [];
  for (const raw of String(value ?? "").split(",")) {
    const s = raw.trim();
    if (s && !seen.has(s)) {
      seen.add(s);
      out.push(s);
    }
  }
  return out;
}

export function validateArticleBrief(brief) {
  const errors = {};
  if (!String(brief.topic ?? "").trim()) errors.topic = "Enter a topic.";
  const words = Number(brief.length_words);
  if (!Number.isFinite(words) || words < 200 || words > 10000)
    errors.length_words = "Use 200–10000 words.";
  const sections = Number(brief.sections_target);
  if (!Number.isFinite(sections) || sections < 1 || sections > 15)
    errors.sections_target = "Use 1–15 sections.";
  return errors;
}

export function cleanArticleBrief(brief) {
  return {
    topic: String(brief.topic ?? "").trim(),
    primary_keyword: String(brief.primary_keyword ?? "").trim(),
    secondary_keywords: parseList(brief.secondary_keywords),
    audience: String(brief.audience ?? "").trim(),
    goal: String(brief.goal ?? "educate").trim(),
    tone: String(brief.tone ?? "").trim(),
    length_words: Number(brief.length_words) || 1200,
    sections_target: Number(brief.sections_target) || 5,
    notes: String(brief.notes ?? "").trim(),
    slug: String(brief.slug ?? "").trim(),
    description: String(brief.description ?? "").trim(),
    tags: parseList(brief.tags),
  };
}
