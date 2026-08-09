import { test } from "node:test";
import assert from "node:assert/strict";
import { CHANNEL_PRESETS, CHANNEL_KEYS, buildBrief, generatedTitle } from "./presets.mjs";

test("CHANNEL_KEYS covers ads/socials/emails", () => {
  assert.deepEqual(CHANNEL_KEYS.sort(), ["ads", "emails", "socials"]);
});

test("buildBrief frames input with the channel instructions", () => {
  const out = buildBrief(CHANNEL_PRESETS.ads, "  Launch sale for founders  ");
  assert.match(out, /high-converting ad variations/);
  assert.match(out, /Brief: Launch sale for founders$/);
});

test("buildBrief returns empty string for blank input", () => {
  assert.equal(buildBrief(CHANNEL_PRESETS.emails, "   "), "");
  assert.equal(buildBrief(CHANNEL_PRESETS.socials, undefined), "");
});

test("generatedTitle tags with the channel label and truncates", () => {
  assert.equal(generatedTitle(CHANNEL_PRESETS.emails, "Welcome flow"), "Email: Welcome flow");
  const long = "a".repeat(80);
  const title = generatedTitle(CHANNEL_PRESETS.socials, long);
  assert.match(title, /^Social post: a+…$/);
  assert.ok(title.length < 80);
});

test("generatedTitle falls back to Untitled", () => {
  assert.equal(generatedTitle(CHANNEL_PRESETS.ads, "   "), "Ad: Untitled");
});
