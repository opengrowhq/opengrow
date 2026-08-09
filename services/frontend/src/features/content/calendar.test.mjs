import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { calendarBucket, sortByDueDate } from "./calendar.mjs";

describe("content calendar helpers", () => {
  it("sorts due content before unscheduled content", () => {
    const items = sortByDueDate([
      { title: "Later", due_at: null, updated_at: "2026-07-22T09:00:00Z" },
      { title: "First", due_at: "2026-07-22T08:00:00Z", updated_at: "2026-07-20T09:00:00Z" },
      { title: "Second", due_at: "2026-07-23T08:00:00Z", updated_at: "2026-07-21T09:00:00Z" },
    ]);

    assert.deepEqual(items.map((item) => item.title), ["First", "Second", "Later"]);
  });

  it("buckets content by due date", () => {
    const now = new Date("2026-07-22T12:00:00Z");

    assert.equal(calendarBucket({ due_at: "2026-07-21T12:00:00Z" }, now), "Overdue");
    assert.equal(calendarBucket({ due_at: "2026-07-22T20:00:00Z" }, now), "Today");
    assert.equal(calendarBucket({ due_at: "2026-07-23T08:00:00Z" }, now), "Tomorrow");
    assert.equal(calendarBucket({ due_at: null }, now), "Later");
  });
});
