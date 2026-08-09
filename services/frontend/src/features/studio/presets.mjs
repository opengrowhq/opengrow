// Channel presets for the generator studios (Ads / Socials / Emails).
//
// The generation API is generic (it only takes a free-text `brief`), so the
// channel distinction lives entirely on the frontend: each preset frames the
// user's input with channel-specific instructions before calling the API, and
// tags the saved ContentPiece title accordingly. No API/contract changes.

export const CHANNEL_PRESETS = {
  ads: {
    key: "ads",
    icon: "ads",
    label: "Ads",
    title: "Ad Studio",
    tagline: "Scroll-stopping ad creative, generated from your brand.",
    accent: "from-og-green-950 via-og-green-700 to-og-green-600",
    placeholder: "e.g. Facebook ad for our new productivity app aimed at busy founders",
    framing:
      "You are a senior performance copywriter. Write 3 high-converting ad variations. " +
      "For each variation include: a scroll-stopping hook, primary body text, and a clear call to action. " +
      "Keep it on-brand, specific, and concise.",
    examples: [
      "Instagram ad for a limited-time 40% launch discount",
      "Facebook ad highlighting our fastest-in-class onboarding",
      "TikTok ad script hook for a Gen-Z audience",
    ],
    saveLabel: "Ad",
  },
  socials: {
    key: "socials",
    icon: "socials",
    label: "Socials",
    title: "Social Studio",
    tagline: "Consistent, on-brand social posts for every platform.",
    accent: "from-og-green-900 via-og-green-600 to-og-green-400",
    placeholder: "e.g. LinkedIn post announcing our Series A and what's next",
    framing:
      "You are a social media strategist. Write a set of platform-ready social posts. " +
      "Include a strong opening line, 2-3 short paragraphs of value, relevant hashtags, and an engaging question or CTA. " +
      "Match the brand voice and keep it native to social.",
    examples: [
      "LinkedIn thought-leadership post about AI in marketing",
      "X/Twitter thread with 5 tips for solo founders",
      "Instagram caption for a product launch carousel",
    ],
    saveLabel: "Social post",
  },
  emails: {
    key: "emails",
    icon: "emails",
    label: "Emails",
    title: "Email Studio",
    tagline: "From welcome flows to promos, without the blank page.",
    accent: "from-og-green-700 via-og-green-600 to-og-green-200",
    placeholder: "e.g. Welcome email for new trial users of our SaaS",
    framing:
      "You are an email marketing expert. Write a complete marketing email. " +
      "Include: 3 subject line options, a preview line, and a well-structured body with a single primary call to action. " +
      "Keep it on-brand, skimmable, and persuasive.",
    examples: [
      "Cart abandonment email with urgency and a discount",
      "Monthly newsletter intro summarizing 3 product updates",
      "Re-engagement email for users who went quiet",
    ],
    saveLabel: "Email",
  },
};

export const CHANNEL_KEYS = Object.keys(CHANNEL_PRESETS);

/** Frame the user's free-text input with the channel's instructions. */
export function buildBrief(preset, userInput) {
  const input = String(userInput ?? "").trim();
  if (!input) return "";
  return `${preset.framing}\n\nBrief: ${input}`;
}

/** A channel-tagged title for the saved ContentPiece. */
export function generatedTitle(preset, userInput) {
  const input = String(userInput ?? "").trim();
  const short = input.length > 48 ? `${input.slice(0, 48).trimEnd()}…` : input;
  return `${preset.saveLabel}: ${short || "Untitled"}`;
}
