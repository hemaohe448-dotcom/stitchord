import { describe, expect, it } from "vitest";
import {
  moveHandle,
  moveNode,
  parseCurve,
  serializeCurve,
} from "./curve";

describe("parseCurve", () => {
  it("parses line segments", () => {
    const path = parseCurve("M 0,0 L 10,0 L 10,10 Z");
    expect(path?.nodes).toHaveLength(3);
    expect(path?.closed).toBe(true);
  });

  it("parses cubic segments and handles", () => {
    const path = parseCurve("M 0,0 C 1,2 3,4 5,6 C 7,8 9,10 11,12 Z");
    expect(path?.nodes).toHaveLength(3);
    expect(path?.nodes[0].out).toEqual([1, 2]);
    expect(path?.nodes[1].in).toEqual([3, 4]);
    expect(path?.nodes[2].in).toEqual([9, 10]);
    expect(path?.closed).toBe(true);
  });

  it("refuses arcs and multiple subpaths", () => {
    expect(parseCurve("M 0,0 A 1 1 0 0 0 5 5")).toBeNull();
    expect(parseCurve("M 0,0 L 1,1 M 2,2 L 3,3")).toBeNull();
  });
});

describe("serializeCurve", () => {
  it("round-trips lines and curves", () => {
    const source = "M 0,0 C 1,2 3,4 5,6 C 7,8 9,10 11,12 Z";
    const path = parseCurve(source);
    if (!path) throw new Error("parse failed");
    const reparsed = parseCurve(serializeCurve(path));
    expect(reparsed).toEqual(path);
  });

  it("round-trips mixed line and curve segments", () => {
    const source = "M 0,0 L 5,0 C 6,1 7,2 8,3 Z";
    const path = parseCurve(source);
    if (!path) throw new Error("parse failed");
    expect(parseCurve(serializeCurve(path))).toEqual(path);
  });

  it("moves a node and its handles", () => {
    const path = parseCurve("M 0,0 C 1,2 3,4 5,6 Z");
    if (!path) throw new Error("parse failed");
    const moved = moveNode(path, 1, 10, 20);
    expect(moved.nodes[1].x).toBe(15);
    expect(moved.nodes[1].y).toBe(26);
    expect(moved.nodes[1].in).toEqual([13, 24]);
  });

  it("moves a handle", () => {
    const path = parseCurve("M 0,0 C 1,2 3,4 5,6 Z");
    if (!path) throw new Error("parse failed");
    const moved = moveHandle(path, 0, "out", 9, 9);
    expect(moved.nodes[0].out).toEqual([9, 9]);
  });
});
