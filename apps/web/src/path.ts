export interface Polyline {
  points: Array<[number, number]>;
  closed: boolean;
}

/**
 * Parse a simple absolute polyline (M/L/Z only). Curves, arcs and multiple
 * subpaths return null so node editing can refuse instead of corrupting data.
 */
export function parsePolyline(d: string): Polyline | null {
  const tokens = d.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/g);
  if (!tokens) return null;

  const points: Array<[number, number]> = [];
  let closed = false;
  let command = "";
  let index = 0;
  let moved = false;

  while (index < tokens.length) {
    const token = tokens[index];
    if (/[A-Za-z]/.test(token)) {
      command = token;
      index += 1;
      if (command === "Z" || command === "z") {
        closed = true;
        continue;
      }
      if (command !== "M" && command !== "L") return null;
      continue;
    }
    if (command !== "M" && command !== "L") return null;
    const x = Number(tokens[index]);
    const y = Number(tokens[index + 1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    index += 2;
    if (command === "M") {
      if (moved) return null; // multiple subpaths are not supported
      moved = true;
      command = "L";
    }
    points.push([x, y]);
  }

  if (points.length < 2) return null;
  return { points, closed };
}

export function serializePolyline(polyline: Polyline): string {
  const [first, ...rest] = polyline.points;
  const round = (value: number) => Number(value.toFixed(3));
  const head = `M ${round(first[0])},${round(first[1])}`;
  const body = rest.map(([x, y]) => `L ${round(x)},${round(y)}`).join(" ");
  return `${head}${body ? ` ${body}` : ""}${polyline.closed ? " Z" : ""}`;
}

export function movePolylinePoint(
  polyline: Polyline,
  index: number,
  x: number,
  y: number,
): Polyline {
  const points = polyline.points.map((point, i) =>
    i === index ? ([x, y] as [number, number]) : point,
  );
  return { ...polyline, points };
}
