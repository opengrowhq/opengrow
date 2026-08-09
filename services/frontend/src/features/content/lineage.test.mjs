import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { contentOriginLabel, lineageRows, shortId } from "./lineage.mjs";

describe("content lineage helpers", () => {
  it("shortens long ids for compact UI", () => {
    assert.equal(shortId("12345678-abcdef"), "12345678");
    assert.equal(shortId("short"), "short");
  });

  it("labels generated blog posts as article drafts", () => {
    assert.equal(
      contentOriginLabel({
        format: "blog_post",
        source_generation_id: "draft-id",
      }),
      "Article draft",
    );
    assert.equal(
      contentOriginLabel({ format: "tweet", source_generation_id: "gen-id" }),
      "Generated",
    );
    assert.equal(contentOriginLabel({ format: "blog_post" }), null);
  });

  it("connects content to draft and parent outline generations", () => {
    const rows = lineageRows(
      {
        format: "blog_post",
        source_generation_id: "draft-id",
      },
      {
        id: "draft-id",
        status: "COMPLETE",
        brief: "Draft brief",
        parent_generation_id: "outline-id",
      },
      {
        id: "outline-id",
        status: "COMPLETE",
        brief: "Outline brief",
      },
    );

    assert.deepEqual(rows, [
      {
        key: "draft",
        label: "Draft generation",
        id: "draft-id",
        status: "COMPLETE",
        brief: "Draft brief",
      },
      {
        key: "outline",
        label: "Outline generation",
        id: "outline-id",
        status: "COMPLETE",
        brief: "Outline brief",
      },
    ]);
  });
});
