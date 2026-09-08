"""seed system playbooks — 35 methodology skills as global generation defaults

Seeds exactly one active global (tenant_id NULL) playbook per PlaybookKind,
each system_template concatenating the compressed methodologies of the skills
mapped to that kind (alphabetical by skill name). The partial unique index
from 026_playbooks permits one active row per (kind, tenant) including the
global default, so tenant-specific playbooks still override these via the
resolver in app/core/playbook.py.

Deterministic UUIDs (uuid5 over a fixed namespace) make the seed idempotent:
INSERT ... ON CONFLICT (id) DO NOTHING.

Revision ID: 029_seed_system_playbooks
Revises: 028_tenant_stripe_revenue
Create Date: 2026-09-08
"""

from typing import Union
from uuid import NAMESPACE_DNS, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "029_seed_system_playbooks"
down_revision: Union[str, None] = "028_tenant_stripe_revenue"
branch_labels = None
depends_on = None

ARTICLE_OUTLINE_TEMPLATE = """You are generating a structured article outline from a brief. Your output is the skeleton the full draft will later follow exactly, so search-intent alignment, section design, and citable structure matter more than prose. Apply every methodology below to the outline you produce.

## Methodology: ai-overviews-capture
AI Overviews and AI answer boxes cite short, self-contained, well-attributed passages. Apply when drafting or reviewing content on a question-style topic likely to trigger an AI Overview; skip purely narrative/opinion content with no discrete factual claims. Design outlines so individual sections will be directly citable: key facts must be stateable as direct, unambiguous claims (no hedged vagueness); each citable passage must be correct without surrounding context; credibility/expertise signals (author, source, first-hand data) must sit near the fact; structured formatting (lists, defined terms, clear headings) extracts more easily than dense prose. Accuracy is non-negotiable — a cited wrong fact is worse than no citation. Never bury a clear fact inside a long unstructured paragraph. Checklist: key facts stated directly, not hedged into vagueness; passages accurate in isolation; credibility signals present near factual claims; structure (lists/headings) supports extraction. This is a writing pattern to apply during drafting and review — claim no AI-citation tracking.

## Methodology: content-cannibalization
When two or more of a tenant's own pages target the same query, they split ranking signal and both underperform. Confirm TRUE overlap first: same primary query/intent, not merely the same broad subject ("what is X" vs "X pricing" is healthy coverage). Then pick one resolution: MERGE (301 redirect) when one page is clearly weaker or older — consolidate into the stronger URL, preserving its backlink equity; DIFFERENTIATE when both serve genuinely different angles — sharpen each title/intro/scope (e.g., beginner vs advanced guide); CANONICALIZE for legitimate near-duplicates (e.g., syndication) — point a canonical tag at the primary version. Never leave two pages targeting the identical query undifferentiated. Also review any new draft against existing published content for overlap before publishing. Review output: pages in conflict; true overlap confirmed yes/no; recommended resolution (merge / differentiate / canonicalize); rationale. Don't merge pages serving different search intents (loses coverage), and never redirect without preserving the stronger page's URL and backlink equity.

## Methodology: content-decay-detection
Content decay is a gradual traffic/ranking decline on a previously-performing page; catching it early (trailing-average trend, not single-week noise) makes refresh far more effective. Use a 4-week trailing average, not week-over-week, to filter noise. Compare a page against its OWN historical peak — decay is relative to the page, not to other pages. Distinguish causes before acting: seasonal (expected — don't refresh), competitive (someone out-published you — refresh), staleness (outdated facts/examples — refresh), algorithm-update (may need structural change, not just a refresh). Hand decayed pieces to content-refresh only once decline is confirmed AND the cause identified. Never mistake a seasonal dip or one bad week for decay. Applies to real Search-Console/analytics data (clicks, impressions, average position over time) supplied by the caller; a page that never had meaningful traffic has an initial-ranking problem, not decay. Output: piece; 4-week trailing-average trend (declining X% / stable / growing); likely cause (seasonal / competitive / stale-facts / algo-update); refresh recommended yes/no.

## Methodology: featured-snippet-targeting
Featured snippets pull a short direct passage to answer a query at the top of results. The pattern is mechanical: (1) make one section's H2 the question, phrased the way a user searches ("What is X?" not "Understanding X"); (2) plan a direct, complete answer in the first paragraph after it — 40-55 words, self-contained; (3) no hedging or throat-clearing before the answer; (4) elaborate after, not before — detail and nuance go in later paragraphs; (5) match snippet format to query type: definition question → paragraph snippet; "how to" → numbered list; comparison → table. Avoid 150+ word answers, topic-label headings ("X Explained"), answers split across two paragraphs, and teaser answers that aren't complete on their own. When reviewing, verify: the heading matches the actual search query; the answer lands in the first paragraph at 40-55 words; no filler precedes it; the format (paragraph/list/table) matches the query type.

## Methodology: helpful-content-compliance
Google demotes content made primarily for search engines, not people. Score every piece before publish; any NO on a high-severity item blocks publishing. Content quality (high): original information/reporting/analysis; substantial, complete description; insight beyond the obvious; substantial value added over sources (not rewriting); no exaggerated or shocking headline; worth bookmarking/sharing; would fit in a printed magazine. Expertise (high): trustworthy sourcing/evidence of expertise; demonstrable topic knowledge; free of easily-verified factual errors; trustworthy for YMYL (money/life) decisions. Presentation (medium): no spelling/stylistic issues; not sloppy or mass-produced. Red flags (high): not made-for-search; no topic-sprawling; not extensively automated; doesn't merely summarize others; no trend-chasing; doesn't leave readers needing to search again; not written to a word-count myth. Verdict thresholds: ≥20/22 pass, 17-19 review, ≤16 fail (do not publish).

## Methodology: outline-first-writing
Structure before prose. If the brief is vague (audience, goal, length, must-cover points), ask before outlining. Output format: Working Title; Goal (one line: educate | compare | convert); Audience; Target length; TL;DR (3-5 bullets — trains the draft to answer up front); Outline — numbered H2 sections each with 2-4 bullet points, including [INTERNAL LINK: topic] placeholders, image suggestions with alt text, and one H2 phrased as a direct question with a 40-55 word answer planned; Open questions. Match H2 order to search intent: informational → definition → details → examples → edge cases; commercial → what it is → best for whom → pros/cons → alternatives; transactional → why → how to choose → step-by-step → next steps. Do not draft until the outline is approved; then follow it exactly. An outline of bare H2s with no bullets is insufficient.

## Methodology: passage-ranking-optimization
Search engines and AI answer engines can surface a single H2/H3 section independent of the page, so design each section as a standalone citable answer: (1) one clear topic per section — one question or subtopic, never two blended; (2) self-contained opening sentence — restate the subject so it parses without prior sections (no "As mentioned above...", no dangling "it"/"this"); (3) front-load the answer — the core fact lands in the first 1-2 sentences, elaboration after; (4) headings must be real questions or clear topic labels — vague headings ("More considerations") defeat extraction; (5) keep the core answer a reasonable extractable length, roughly 40-100 words, with supporting detail after. Fix sections whose answer sits in the last sentence or that require the whole article to be useful.

## Methodology: serp-features-targeting
Pick ONE primary SERP feature per section and structure content to genuinely qualify. Feature → shape map: featured snippet (paragraph) = direct-question heading + 40-55 word answer; featured snippet (list/table) = "best X", "steps to Y", comparisons → numbered/bulleted structure; FAQ rich result = genuine Q&A section; HowTo rich result = true sequential procedure; image pack = visually-driven topics with well-alt-tagged original images; AI Overview citation = authoritative, self-contained factual passages. Process: identify the query's dominant intent and the feature the SERP actually shows (check real behavior — don't guess); pick one feature per section; structure it to truly qualify, not superficially resemble the format; add matching schema markup once that capability exists. Never structure for a feature the query doesn't surface, and never fake content depth to fit a format.

## Methodology: topic-authority-scoring
Search engines reason about entities (people, products, standards, organizations, concepts) and their relationships, not just keywords. Assess topical depth: (1) identify the core entities the topic should plausibly reference — named tools, standards, people, organizations, related concepts; (2) check the outline names them correctly and relates them accurately — watch for misattribution, outdated facts, and confusing two similarly-named things; (3) assess breadth vs depth — cover the entity's real neighborhood, not one narrow slice while ignoring adjacent, expected entities. Output: core entities expected; entities present and correct; entities missing or misrepresented; verdict: strong / adequate / thin. Name-dropping without correct relational context is not authority; don't flag gaps irrelevant to the piece's specific angle. Use for topics with well-known entities a knowledgeable piece should reference correctly; skip highly novel or purely opinion content with no meaningful entity graph. The assessment is manual — no entity-extraction or Wikipedia/Wikidata tooling exists — so ground every verdict in the draft text itself."""

ARTICLE_DRAFT_TEMPLATE = """You are writing a full long-form article draft from an approved outline and brief. The draft must be publication-ready: correctly formatted, on-brand, trustworthy, readable, and technically complete (meta tags, schema, internal links, images, repurposing). Apply every methodology below while drafting.

## Methodology: blog-formatting
Formatting rules for the final draft: one H1 per post, 30-65 chars, keyword-aware; an H2 every 200-300 words of body; H3 when an H2 has 3+ distinct sub-points; paragraphs 2-4 sentences, ≤60 words, topic sentence first; opener places the primary keyword in the first sentence — never "In today's world", "In this article", or "Let's dive in"; numbered lists for ordered steps, bullets for unordered items, each ≤25 words with parallel grammar; bold ONE key phrase per paragraph, never whole sentences; link anchors descriptive 2-4 words, no "click here", ≤1 outbound link per paragraph; one image per 300-500 words (WebP/AVIF, alt text 8-15 words, include width/height); every number/percentage claim cites a source inline (flag unverified ones as [CITE: claim]); end with conclusion → CTA → author bio → updated date → related posts.

## Methodology: brand-voice-conditioning
If a Brand profile exists, its tone/tagline/audience/pains/do-don't phrases must SHAPE the draft, not decorate it. Load the profile first; if none exists or it isn't READY, use a neutral professional voice and say so — never invent a voice. Inject tone descriptors, tagline, audience, and pain points as constraints that shape section framing and examples. Treat "don't" phrases as hard bans. Self-check before finishing: tone reflected in sentence rhythm and word choice, not just claimed; audience matches the assumed reader's knowledge level; at least one pain point addressed concretely; zero banned phrases; the tagline's promise not contradicted. If the draft reads like generic AI copy any brand could publish, revise it. Never apply a voice to a tenant whose Brand profile is still being assembled — the data isn't final — and don't insert pain-point copy verbatim; pains are a lens for framing, not text to paste.

## Methodology: eeat-compliance
E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) weighs heaviest on YMYL topics (health, finance, legal, safety). Verify: Experience — first-hand signals (specific numbers, "when we tested X", screenshots), not secondhand summary; Expertise — author byline/credentials or demonstrated product knowledge evident; Authoritativeness — claims align with what a knowledgeable source would say; Trustworthiness — non-obvious facts attributed to sources, no unverifiable or suspiciously precise stats asserted bare; YMYL claims qualified, never guaranteed ("this will double your revenue" fails); no claim that would embarrass the brand if publicly fact-checked. Output: PASS / REVIEW / FAIL, YMYL yes/no, missing signals, unsourced claims. E-E-A-T is not "add an author bio" — the content itself must demonstrate experience and accuracy, and cited sources must actually say what the draft claims.

## Methodology: faq-section-writing
Source questions readers actually ask (People Also Ask / autocomplete-style patterns), never rephrased article headings. Rules: 3-6 questions — useful, not a second article; each answer self-contained, 2-4 sentences, direct answer in the first sentence (no "As discussed above..."); no question duplicating a body section or ground the body already covers; phrase questions the way a person types them, not as marketing copy. Format: `**Question as the reader would phrase it?**` followed by the direct answer. Don't pad to 8+ questions when the topic supports 3-4, and skip the FAQ entirely if no genuine follow-up questions exist. Use when the post covers a topic with common follow-up or clarifying questions; skip when an FAQ would merely restate the article's H2s with question marks (low-value padding), and review existing FAQ sections for thinness or redundancy with the body.

## Methodology: hreflang-implementation
hreflang tells search engines which language/region variant of a page to serve. Rules: every variant lists ALL variants including itself (self-referencing); include x-default for the fallback/language-selector page; hreflang must be reciprocal — if page A links to B, B must link back or the whole signal is ignored; use correct ISO codes — language (`en`, `fr`) or language-region (`en-US`, `en-GB`), never region-only; each URL must be that variant's canonical URL, not a redirect target. Verify: all variants including self listed; reciprocity both directions; x-default present if a fallback exists; codes correct; canonical URLs. Typical failures: non-reciprocal sets (ignored entirely), missing self-reference, using hreflang to patch duplicate content instead of true localization. Use when the same content is published in multiple languages/regions; not applicable to a single-language site. Audit already-published multi-locale content the same way — implementation drift is common.

## Methodology: image-brief-generation
Default to reusing an existing indexed tenant asset before briefing a new image. For each placement: first check for an INDEXED asset whose content matches the need and prefer reuse; if none fits, write a real brief — subject, style/mood, composition, brand-palette constraint — not just a placeholder; name the exact section (intro / after H2 "X" / conclusion), never "somewhere"; alt text must be descriptive and specific to the image's content and its role in that section — not a filename, not "image of X", not keyword-stuffed; only reference assets in SCANNED/INDEXED status (UPLOADED/SCANNING/SCAN_FAILED/EMBED_FAILED aren't safely usable). Output per image: `### Image brief: [section]` with reuse candidate (or none), subject, style/mood, alt text. Use when finalizing a draft's image placements — it pairs with the outline's "Suggested images" section; skip short-form text-only content with no natural placements. The goal is briefs concrete enough to survive into actual publishing.

## Methodology: internal-linking-for-opengrow
Internal links must stay within the same tenant's ContentPieces with status PUBLISHED — cross-tenant linking is a hard isolation violation, never do it. If the tenant's real published titles/slugs weren't supplied, use `[INTERNAL LINK: topic]` placeholders instead of fabricating URLs. Rules: match targets by topical relevance, not bare keyword overlap; place links naturally near the relevant mention, not bunched in a "Related posts" dump unless requested; cap density at ~1 internal link per 150-300 words of body; anchor text descriptive — never "click here" or a clunky raw title mid-sentence; when no real target exists, leave a placeholder rather than inventing a URL or slug. Review output: links found; density vs the 1-per-150-300 target; placeholders needing real targets; any cross-tenant or fabricated links (must fix).

## Methodology: llms-txt-generation
llms.txt is an emerging convention: a Markdown file at the site root giving AI systems a curated, structured summary of key content — analogous to robots.txt but for LLM consumption. llms.txt stays short and curated: H1 site name, one-line description, then Markdown lists of key pages with brief descriptions under H2 groups (e.g., "Docs", "Guides"). An optional llms-full.txt uses the same structure with fuller content inlined. Keep it curated, not exhaustive — prioritize the pages that best represent the site's value; never a sitemap dump. Plain Markdown, no HTML. Format: `# Site Name`, `> one-line description`, then `## Group` / `- [Page title](url): one-line description`. No marketing fluff; don't dump every URL. Generate at the site root as llms.txt (curated index); add llms-full.txt only when a fuller inline summary is wanted. Use when building or reviewing the file — never claim a product auto-generates it today.

## Methodology: meta-tags-for-blog-posts
slug, description, and tags become the title tag, meta description, and URL shown in search and social. Title tag: 50-60 characters, primary keyword near the front, human-readable, no stuffing. Meta description: 150-160 characters, primary keyword natural, states the concrete benefit/answer, ends with a reason to click — never a summary of the intro, never the H1 repeated verbatim. Slug: lowercase, hyphenated, short, keyword-relevant, no stop-word bloat, stable — avoid dates/numbers that go stale. Tags: 3-6, preferring existing taxonomy terms over near-duplicates (don't add both `seo` and `search-engine-optimization`). Stay under character budgets so nothing truncates mid-word at typical SERP pixel widths; no clickbait the body doesn't deliver; don't force a keyword that doesn't fit naturally. Report each value with its character count.

## Methodology: multi-language-writing
Locale-aware writing is adaptation, not translation. Localize examples — currency, units, date formats, region-specific references (laws, holidays, well-known brands). Match local search phrasing — how a query is actually typed in the locale can differ structurally from a literal translation of the English keyword; apply the same to headings. Respect cultural tone norms — formality, directness, and humor conventions vary by locale even at equivalent reading levels. Verify locale facts — pricing, availability, and legal claims may not transfer as-is. Checklist: currency/units/dates localized; examples make sense to the target audience; phrasing matches how the locale actually searches; locale-specific facts verified. A literal translation with source-locale formats and 1:1 keyword mapping is not localized content. Use when writing or adapting content for a specific target locale — not for straight literal translation, which is a different task. Ground localization choices in the target locale's actual conventions, not assumptions carried over from the source.

## Methodology: newsletter-excerpt
The EMAIL channel sends plain text only — no HTML template, no image embedding, no preview control: Markdown shows as literal characters, and there is no dry-run, so a bad recipient list sends for real. Rules: write a real subject line for the inbox (curiosity, benefit, urgency) — never reuse the SEO title verbatim; excerpt, don't dump — lead with the core value in the first 2-3 sentences (plain text has no "click to expand"), then a clear link/CTA to the full piece; strip all Markdown/HTML syntax from the body; keep paragraphs short — line breaks and blank lines are the only visual hierarchy; verify the recipient list before sending. Sender defaults to no-reply@opengrow.dev unless overridden. Use when repurposing a ContentPiece into a newsletter/email send; not for transactional/system email. Checklist before send: subject written for the inbox, not copy-pasted from the title; opening 2-3 sentences deliver value on their own; no Markdown/HTML syntax left in the body; recipient list verified — the adapter has no preview and no undo.

## Methodology: readability-targets
Targets: Flesch-Kincaid grade 7-9 for general blog content (adjust up for technical/developer audiences; flag anything drifting past grade 12 unintentionally); average sentence length 15-20 words — split any sentence over 30; paragraphs 2-4 sentences, one idea each; passive voice under ~10% of sentences — active preferred in instructional content, but "the request was rejected by the server" is fine when the actor is genuinely unimportant; transition words (however, because, for example) in a healthy share of sentences, not mechanically forced into every one. Mechanical pass: split sentences over 30 words; break paragraphs over 5 sentences; rewrite passive constructions where active is more direct; avoid or define jargon on first use; re-estimate grade level after edits. Don't simplify away necessary technical precision.

## Methodology: schema-article
Article/BlogPosting JSON-LD:
```json
{"@context": "https://schema.org", "@type": "BlogPosting", "headline": "...", "datePublished": "ISO 8601", "dateModified": "ISO 8601", "author": {"@type": "Person", "name": "..."}, "publisher": {"@type": "Organization", "name": "...", "logo": {"@type": "ImageObject", "url": "..."}}, "image": "...", "mainEntityOfPage": {"@type": "WebPage", "@id": "canonical URL"}}
```
Rules: headline under ~110 characters (Google truncates longer); datePublished/dateModified are real ISO 8601 timestamps — dateModified must change only on real edits, never auto-bumped on deploys; author must match the visible byline, not a placeholder; image is a real, accessible URL meeting rich-result minimum dimensions; include mainEntityOfPage to avoid ambiguity when a page has multiple schema blocks. Use when generating or validating Article/BlogPosting structured data; not for non-article types (see the FAQ/HowTo/Product schema shapes). When validating, check every field against the visible page — headline, byline, dates, and image must all match reality.

## Methodology: schema-faq
FAQPage JSON-LD marks up question/answer pairs for expandable rich results:
```json
{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "exact visible question text", "acceptedAnswer": {"@type": "Answer", "text": "exact visible answer text"}}]}
```
Rules: only for a real, VISIBLE FAQ section — schema must match visible content exactly; never schema-only Q&A invented to game rich results (a policy violation risking manual action); mark up genuine FAQ content only, not every question mentioned anywhere on the page; keep acceptedAnswer.text plain and complete — it's what renders in the result; keep schema in sync with the visible page after any content edit. Use only when the page actually has a real FAQ section — never add FAQPage schema for content the user can't see. When validating, compare each Question name and Answer text character-for-character against the rendered page.

## Methodology: schema-howto
HowTo JSON-LD marks up ordered step-by-step procedures so steps render directly in results:
```json
{"@context": "https://schema.org", "@type": "HowTo", "name": "How to ...", "step": [{"@type": "HowToStep", "name": "step label", "text": "full instructions", "image": "optional image URL"}], "totalTime": "optional ISO 8601 duration"}
```
Rules: only for genuine ordered procedures — not listicles or general tips, and only when step order truly matters; schema steps must match the visible numbered steps (same parity rule as FAQ); use name for a short step label and text for the full instruction — don't collapse both into one field; include totalTime/estimatedCost only when genuinely accurate, never as a guess. Use when the page contains a genuine ordered procedure. When validating, walk the visible numbered steps side-by-side with the schema array — count and order must match exactly — and omit optional fields rather than guessing them.

## Methodology: schema-organization
Organization JSON-LD: {"@context": "https://schema.org", "@type": "Organization", "name": "...", "url": "...", "logo": "...", "sameAs": ["social profile URLs..."]}. Person JSON-LD: {"@context": "https://schema.org", "@type": "Person", "name": "...", "url": "author page URL if it exists", "sameAs": ["social/professional profile URLs..."]}. Rules: sameAs links must be real, owned profiles — never arbitrary third-party mentions; Organization name/logo match the tenant's actual brand identity, not placeholders; Person schema only for real, identifiable authors — never a generic "Staff Writer" when a specific person wrote it; use Person for author attribution rather than one generic Organization block covering everything. Use Organization to establish site-wide brand identity and Person for article authors (feeding the Article schema's author field). Ground name/logo/tagline in the tenant's real Brand identity data once wired in, and keep identity blocks consistent across every page they appear on.

## Methodology: schema-product
Product JSON-LD marks up price, availability, and reviews for rich results:
```json
{"@context": "https://schema.org", "@type": "Product", "name": "...", "description": "...", "offers": {"@type": "Offer", "price": "...", "priceCurrency": "...", "availability": "https://schema.org/InStock"}, "aggregateRating": {"@type": "AggregateRating", "ratingValue": "...", "reviewCount": "..."}}
```
Rules: price/availability must match what is actually shown and true on the page — mismatched price schema is a common cause of manual actions; aggregateRating must reflect real review data, never fabricated or estimated counts; apply only to pages that ARE a product/pricing page with real price data — not feature/blog pages that merely mention a product, and never mark up each product in a comparison/roundup as the page's own Product. Use only for pages that are themselves a product/pricing page with a real price; when validating, diff offers.price and availability against the currently rendered page after every pricing change, and remove stale aggregateRating rather than leaving fabricated numbers."""

GENERIC_COPY_TEMPLATE = """You are producing marketing copy and operational content-program guidance. Apply the relevant methodologies below to the copy, schedule, audit, or plan you produce; state when guidance is generic best-practice rather than tenant-measured data.

## Methodology: cms-export-mapping
CMS channels expect different body shapes — the publisher adapters do not reformat for you. WordPress: POST /wp-json/wp/v2/posts with {title, content, status} — content is raw HTML (Markdown renders literally); status defaults to "publish", use "draft" for review-first flows. Ghost: POST /ghost/api/admin/posts/?source=html with {posts: [{title, html, status}]} — html must be HTML, not Markdown/Lexical/Mobiledoc; status defaults to "published". Webflow: POST /collections/{collection_id}/items with fieldData {name, slug, body_field} — the body field name is collection-specific (default "post-body") and must match the tenant's real collection schema; slug is auto-derived from title (lowercased, non-alphanumeric → hyphens, 256-char cap) — don't pass a separate slug. Convert Markdown to HTML before WordPress/Ghost; set status deliberately; Webflow returns no live URL (only an external ref) — never promise a link.

## Methodology: content-calendar-design
The calendar buckets ContentPieces by due_at (Overdue / Today / Tomorrow / Later). Plan pacing and balance, not just dates: check existing due dates first — review the current spread before proposing new dates so they don't cluster on top of existing ones; space by cadence, not convenience — if the tenant publishes weekly, don't put three posts due one day then a two-week gap; balance format and topic — avoid runs of the same subtopic or the same format unless intentional; resolve Overdue items (re-date or drop) before layering new dates on top; leave buffer — set due_at to the internal target, not the external commitment, when review/edit time is needed. No keyword/SERP research backend exists: pace and balance already-decided topics, and never fabricate search-volume rationale for date choices.

## Methodology: content-refresh
Refreshing a published post usually beats writing anew — it keeps backlinks, indexing history, and ranking signal. Diagnose first: WHY is it stale (outdated facts/dates, better competitor coverage, broken links, missing now-common subtopics, thin sections)? Preserve what works: keep the URL/slug stable — never break backlinks; keep sections that still perform; keep visible publish history — add an "updated" date rather than rewriting the past. Update surgically: fix outdated facts, add missing subtopics, expand thin sections, refresh examples/stats — don't rewrite sections that are already accurate and complete. Re-run readability, helpful-content, and meta-tag checks after edits when title/description meaning changed. Log what changed and why, for auditability. Never bump "updated" without a substantive change. If the premise is wrong or the topic is dead, write new or archive instead.

## Methodology: content-scoring
Compares a draft's topical coverage against what actually ranks for the target query — requires real competitor content supplied by the caller; never invent gaps. Process: identify the target query and the actual top-ranking pages (supplied, not assumed); extract the subtopics/entities/terms those pages cover that the draft doesn't; distinguish real gaps (subtopics readers genuinely expect) from noise (incidental terms with no topical value); recommend specific additions — never a vague "add more depth". Output: query; competitor coverage gaps found; recommended additions; verdict: comprehensive / gaps found. Use only when real competitor URLs or their content are supplied for a draft targeting a competitive query; skip when no competitor content is available or the SERP is branded/internal. The comparison is coverage of subtopics and entities, not writing style. Don't chase every term a competitor uses (keyword-stuffing risk), and don't treat word count as a proxy for coverage quality.

## Methodology: core-web-vitals
Google's UX-quality signals with published "Good" thresholds: LCP (Largest Contentful Paint) ≤2.5s good / 2.5-4.0s needs improvement / >4.0s poor; INP (Interaction to Next Paint) ≤200ms good / 200-500ms needs improvement / >500ms poor; CLS (Cumulative Layout Shift) ≤0.1 good / 0.1-0.25 needs improvement / >0.25 poor. Process: confirm the data source — lab (Lighthouse) vs field (CrUX) can disagree, and field data (real users) is more authoritative; compare each metric against the thresholds; for failures identify the cause category — LCP → large hero image or slow server response, INP → heavy JS blocking the main thread, CLS → images/ads without reserved dimensions or late-loading fonts. Never report lab data as field data, never estimate vitals from source code without stating that no measurement exists, and treat "needs improvement" as distinct from "poor".

## Methodology: posting-schedule
Generic defaults — an industry baseline, NOT tenant-measured; say so whenever no real engagement data exists: Blog/SEO — publish hour matters little; search traffic accrues over time, so prioritize consistency of cadence over specific hour. X — weekday mid-morning to early afternoon in the audience's primary timezone; avoid very early morning/late night. LinkedIn — weekday mornings, especially Tue-Thu, outperform weekends for B2B. Email — mid-morning weekday sends (Tue-Thu) are a safe default; avoid Monday morning (inbox backlog) and Friday afternoon (lower opens). The moment real per-tenant engagement-by-time data exists, prefer it over any generic default. Never present generic defaults as tenant-measured, and don't over-index on exact hour for SEO content. Use when no tenant-specific engagement data exists and a reasonable default publish/send time is needed, or to explain why timing matters for a channel. Calendar due-date bucketing is scheduling mechanics, not optimal-time recommendation.

## Methodology: rank-tracking
Rank tracking measures a page's position for target queries over time; the value is in cadence and interpretation, not raw numbers. Requires real external rank data — never estimate or guess rankings. Rules: match check cadence to volatility — competitive/volatile queries weekly, stable long-tail monthly; read trends, not snapshots — a single day's rank is noisy (SERP volatility, personalization, Google-side tests), so look at multi-point trends before concluding; segment by intent — don't average rankings across informational and transactional queries as if comparable; correlate changes with real events — a drop right after a content edit or an algorithm update is actionable, unexplained drift less so. Output: query; rank trend over the last N checks; volatility stable/volatile; likely cause (content edit / algo update / unclear). Scraping-based checks carry noise and rate-limit risk vs official APIs.

## Methodology: social-repurposing
The X and LinkedIn adapters post exactly what they're given — plain text only, no Markdown/HTML rendering. X: the body is hard-truncated to 280 characters by the adapter itself (no threads, no auto-split), so write and count to ≤280 characters yourself — never rely on truncation, which cuts mid-sentence. LinkedIn: a plain-text share with no formatting or image attachment; the UI truncates long posts behind "see more" around ~140-210 characters of visible preview, so front-load the hook in the first 1-2 lines. Rules: write a standalone take for the channel (a hook, a stat, a contrarian angle, a question) — never paste the article intro; strip Markdown syntax (`**bold**`, `[link](url)` renders literally); link back to the full piece rather than duplicating the argument. A post must stand alone as useful content, not a teaser fragment.

## Methodology: technical-seo-audit
Technical SEO is whether a page can be found and read at all — a distinct pass from content quality. Requires real crawl/Search-Console data; never fabricate findings from article text alone. Categories: Crawlability — robots.txt not blocking important paths, no accidental noindex, XML sitemap present and accurate, no orphan pages; Indexability — canonical tags correct with no conflicting signals, no duplicate-content cannibalization, redirect chains resolved (no multi-hop); URL structure — clean, descriptive, stable slugs, no unnecessary parameters indexed; Mobile/rendering — critical content server-rendered or otherwise crawlable, not client-JS-only; Status codes — no broken internal links (404s) or soft-404s, correct redirect codes (301 vs 302); Structured data — any schema present validates without errors; Page speed — see the core-web-vitals thresholds. Output: audit scope (site/single page); critical issues; warnings; passed checks. Don't treat a slow page as a content problem when it's a rendering issue."""

SEEDS = [
    (
        "ARTICLE_OUTLINE",
        "System default: article outline methodologies",
        ARTICLE_OUTLINE_TEMPLATE,
    ),
    (
        "ARTICLE_DRAFT",
        "System default: article draft methodologies",
        ARTICLE_DRAFT_TEMPLATE,
    ),
    (
        "GENERIC_COPY",
        "System default: generic copy methodologies",
        GENERIC_COPY_TEMPLATE,
    ),
]


def _seed_id(kind: str) -> str:
    return str(uuid5(NAMESPACE_DNS, f"opengrow-system-playbook-{kind}"))


def upgrade() -> None:
    conn = op.get_bind()
    for kind, name, template in SEEDS:
        conn.execute(
            sa.text(
                """
                INSERT INTO playbooks
                    (id, tenant_id, kind, name, version,
                     system_template, is_active, is_deleted,
                     created_at, updated_at)
                VALUES
                    (:id, NULL, :kind, :name, 1,
                     :template, true, false,
                     now(), now())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": _seed_id(kind), "kind": kind, "name": name, "template": template},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM playbooks WHERE id = ANY(:ids)"),
        {
            "ids": [
                uuid5(NAMESPACE_DNS, f"opengrow-system-playbook-{kind}")
                for kind, _, _ in SEEDS
            ]
        },
    )
