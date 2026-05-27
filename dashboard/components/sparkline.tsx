interface Props {
  points: number[];
  width?: number;
  height?: number;
  className?: string;
}

export function Sparkline({
  points,
  width = 120,
  height = 32,
  className,
}: Props) {
  if (points.length < 2) {
    return (
      <svg width={width} height={height} className={className}>
        <line
          x1="0"
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="3 3"
          opacity="0.3"
        />
      </svg>
    );
  }

  const pad = 2;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;

  const xs = points.map(
    (_, i) => pad + (i / (points.length - 1)) * (width - pad * 2),
  );
  const ys = points.map(
    (v) => height - pad - ((v - min) / range) * (height - pad * 2),
  );

  const d = xs
    .map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`)
    .join(" ");

  const areaD = [
    `M${xs[0].toFixed(1)},${height}`,
    ...xs.map((x, i) => `L${x.toFixed(1)},${ys[i].toFixed(1)}`),
    `L${xs[xs.length - 1].toFixed(1)},${height}`,
    "Z",
  ].join(" ");

  return (
    <svg width={width} height={height} className={className}>
      <path d={areaD} fill="currentColor" opacity="0.08" />
      <path
        d={d}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle
        cx={xs[xs.length - 1].toFixed(1)}
        cy={ys[ys.length - 1].toFixed(1)}
        r="2"
        fill="currentColor"
      />
    </svg>
  );
}
