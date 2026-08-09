import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { slugify } from "./slugify.mjs";

describe("slugify", () => {
  it("lowercases and hyphenates", () => {
    assert.equal(slugify("Why Founders Blog"), "why-founders-blog");
  });
  it("strips punctuation and collapses separators", () => {
    assert.equal(slugify("Hello,   World!! -- again"), "hello-world-again");
  });
  it("never returns an empty slug", () => {
    assert.equal(slugify("!!!"), "post");
    assert.equal(slugify(""), "post");
  });
});
