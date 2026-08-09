import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { moveSection, parseOutline, serializeOutline } from "./outline.mjs";

const TEXT = `## Why it compounds
- SEO
- trust

## How to start
- pick a topic`;

describe("outline", () => {
  it("parses headings and bullets", () => {
    const sections = parseOutline(TEXT);
    assert.equal(sections.length, 2);
    assert.equal(sections[0].heading, "Why it compounds");
    assert.deepEqual(sections[0].points, ["SEO", "trust"]);
  });
  it("ignores preamble and blank lines", () => {
    assert.equal(parseOutline("Here you go:\n\n## A\n- x").length, 1);
  });
  it("round-trips through serialize", () => {
    assert.deepEqual(parseOutline(serializeOutline(parseOutline(TEXT))), parseOutline(TEXT));
  });
  it("reorders sections", () => {
    const sections = parseOutline(TEXT);
    assert.equal(moveSection(sections, 0, 1)[0].heading, "How to start");
  });
  it("returns [] for empty input", () => {
    assert.deepEqual(parseOutline(""), []);
  });
});
