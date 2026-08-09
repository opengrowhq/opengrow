import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { cleanArticleBrief, defaultArticleBrief, validateArticleBrief } from "./article-brief.mjs";

describe("article brief", () => {
  it("has sensible defaults", () => {
    const b = defaultArticleBrief();
    assert.equal(b.goal, "educate");
    assert.equal(b.length_words, 1200);
    assert.equal(b.sections_target, 5);
    assert.equal(b.topic, "");
  });

  it("requires a topic", () => {
    assert.ok(validateArticleBrief({ ...defaultArticleBrief(), topic: "  " }).topic);
    assert.equal(validateArticleBrief({ ...defaultArticleBrief(), topic: "Blogging" }).topic, undefined);
  });

  it("rejects out-of-range length and sections", () => {
    const base = { ...defaultArticleBrief(), topic: "x" };
    assert.ok(validateArticleBrief({ ...base, length_words: 50 }).length_words);
    assert.ok(validateArticleBrief({ ...base, length_words: 99999 }).length_words);
    assert.ok(validateArticleBrief({ ...base, sections_target: 0 }).sections_target);
  });

  it("cleans comma lists into arrays and coerces numbers", () => {
    const out = cleanArticleBrief({
      ...defaultArticleBrief(),
      topic: "  Blogging  ",
      secondary_keywords: "seo, content , seo",
      tags: "growth",
      length_words: "1500",
    });
    assert.equal(out.topic, "Blogging");
    assert.deepEqual(out.secondary_keywords, ["seo", "content"]);
    assert.deepEqual(out.tags, ["growth"]);
    assert.equal(out.length_words, 1500);
  });
});
