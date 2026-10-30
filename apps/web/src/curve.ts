export interface CurveNode {
  x: number;
  y: number;
  /** incoming control point (absolute) */
  in?: [number, number];
  /** outgoing control point (absolute) */
  out?: [number, number];
}

export interface CurvePath {
  nodes: CurveNode[];
  closed: boolean;
}

type Token = string;

function tokenize(d: string): Token[] | null {
  return d.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/g);
}

/** Parse absolute M/L/C/Z paths. Curves, arcs and multiple subpaths return null. */
export function parseCurve(d: string): CurvePath | null {
  const tokens = tokenize(d);
  if (!tokens) return null;

  const nodes: CurveNode[] = [];
  let command = "";
  let closed = false;
  let index = 0;

  const number = (): number | null => {
    const value = Number(tokens[index]);
    if (!Number.isFinite(value)) return null;
    index += 1;
    return value;
  };

  while (index < tokens.length) {
    const token = tokens[index];
    if (/[A-Za-z]/.test(token)) {
      command = token;
      index += 1;
      if (command === "Z" || command === "z") {
        closed = true;
        continue;
      }
      if (!["M", "L", "C"].includes(command)) return null;
      if (command === "M" && nodes.length > 0) return null;
      continue;
    }
    if (command === "M" || command === "L") {
      const x = number();
      const y = number();
      if (x === null || y === null) return null;
      nodes.push({ x, y });
      if (command === "M") command = "L";
      continue;
    }
    if (command === "C") {
      const c1x = number();
      const c1y = number();
      const c2x = number();
      const c2y = number();
      const x = number();
      const y = number();
      if (c1x === null || c1y === null || c2x === null || c2y === null || x === null || y === null) {
        return null;
      }
      const previous = nodes[nodes.length - 1];
      if (!previous) return null;
      previous.out = [c1x, c1y];
      nodes.push({ x, y, in: [c2x, c2y] });
      continue;
    }
    return null;
  }

  if (nodes.length < 2) return null;
  return { nodes, closed };
}

function fmt(value: number): string {
  return String(Number(value.toFixed(3)));
}

export function serializeCurve(path: CurvePath): string {
  const first = path.nodes[0];
  const parts = [`M ${fmt(first.x)},${fmt(first.y)}`];

  const segment = (from: CurveNode, to: CurveNode) => {
    if (from.out || to.in) {
      const c1 = from.out ?? [from.x, from.y];
      const c2 = to.in ?? [to.x, to.y];
      parts.push(
        `C ${fmt(c1[0])},${fmt(c1[1])} ${fmt(c2[0])},${fmt(c2[1])} ${fmt(to.x)},${fmt(to.y)}`,
      );
    } else {
      parts.push(`L ${fmt(to.x)},${fmt(to.y)}`);
    }
  };

  for (let index = 1; index < path.nodes.length; index += 1) {
    segment(path.nodes[index - 1], path.nodes[index]);
  }

  if (path.closed) {
    const last = path.nodes[path.nodes.length - 1];
    if (last.out || first.in) {
      const c1 = last.out ?? [last.x, last.y];
      const c2 = first.in ?? [first.x, first.y];
      parts.push(
        `C ${fmt(c1[0])},${fmt(c1[1])} ${fmt(c2[0])},${fmt(c2[1])} ${fmt(first.x)},${fmt(first.y)}`,
      );
    }
    parts.push("Z");
  }

  return parts.join(" ");
}

export function moveNode(
  path: CurvePath,
  index: number,
  dx: number,
  dy: number,
): CurvePath {
  const nodes = path.nodes.map((node, i) => {
    if (i !== index) return node;
    return {
      ...node,
      x: node.x + dx,
      y: node.y + dy,
      in: node.in ? ([node.in[0] + dx, node.in[1] + dy] as [number, number]) : undefined,
      out: node.out ? ([node.out[0] + dx, node.out[1] + dy] as [number, number]) : undefined,
    };
  });
  return { ...path, nodes };
}

export function moveHandle(
  path: CurvePath,
  index: number,
  which: "in" | "out",
  x: number,
  y: number,
): CurvePath {
  const nodes = path.nodes.map((node, i) =>
    i === index ? { ...node, [which]: [x, y] as [number, number] } : node,
  );
  return { ...path, nodes };
}
