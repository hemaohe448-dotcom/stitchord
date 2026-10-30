import { describe, expect, it } from "vitest";
import { movePolylinePoint, parsePolyline, serializePolyline } from "./path";

describe("parsePolyline", () => {
  it("parses a closed rectangle", () => {
    const poly = parsePolyline("M 10,10 L 50,10 L 50,40 L 10,40 Z");
    expect(poly?.closed).toBe(true);
    expect(poly?.points).toHaveLength(4);
  });

  it("parses an open line", () => {
    const poly = parsePolyline("M 10,50 L 50,50 L 50,80");
    expect(poly?.closed).toBe(false);
    expect(poly?.points).toHaveLength(3);
  });

  it("refuses curves", () => {
    expect(parsePolyline("M 0,0 C 1,2 3,4 5,6 Z")).toBeNull();
  });

  it("refuses multiple subpaths", () => {
    expect(parsePolyline("M 0,0 L 1,1 M 2,2 L 3,3")).toBeNull();
  });
});

describe("serializePolyline", () => {
  it("round-trips", () => {
    const poly = parsePolyline("M 10,10 L 50,10 L 50,40 Z");
    if (!poly) throw new Error("parse failed");
    expect(parsePolyline(serializePolyline(poly))).toEqual(poly);
  });

  it("moves one point", () => {
    const poly = parsePolyline("M 0,0 L 10,0 L 10,10 Z");
    if (!poly) throw new Error("parse failed");
    const moved = movePolylinePoint(poly, 1, 20, 5);
    expect(moved.points[1]).toEqual([20, 5]);
    expect(moved.points[0]).toEqual([0, 0]);
  });
});
