const COLORS = {
  CRITICAL: { bg: "#fee2e2", text: "#991b1b", dot: "#dc2626" },
  HIGH:     { bg: "#ffedd5", text: "#9a3412", dot: "#ea580c" },
  MEDIUM:   { bg: "#fef9c3", text: "#854d0e", dot: "#ca8a04" },
  LOW:      { bg: "#dcfce7", text: "#166534", dot: "#16a34a" },
};

export default function SeverityBadge({ severity }) {
  const s = (severity || "MEDIUM").toUpperCase();
  const c = COLORS[s] || COLORS.MEDIUM;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 10px",
        borderRadius: 9999,
        background: c.bg,
        color: c.text,
        fontWeight: 600,
        fontSize: 12,
        letterSpacing: "0.05em",
      }}
    >
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: c.dot }} />
      {s}
    </span>
  );
}
