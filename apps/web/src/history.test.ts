import { describe, expect, it } from "vitest";
import { HISTORY_LIMIT, pushHistory } from "./history";

describe("pushHistory", () => {
  it("keeps at most 100 snapshots", () => {
    let past: number[] = [];
    for (let index = 0; index < 150; index += 1) {
      past = pushHistory(past, index);
    }
    expect(past).toHaveLength(HISTORY_LIMIT);
    expect(past[0]).toBe(50);
    expect(past[HISTORY_LIMIT - 1]).toBe(149);
  });

  it("keeps insertion order", () => {
    expect(pushHistory([], "a")).toEqual(["a"]);
    expect(pushHistory(["a"], "b")).toEqual(["a", "b"]);
  });
});
