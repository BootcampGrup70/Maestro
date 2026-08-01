type View = "orchestrate" | "settings" | "library";

interface Props {
  activeView: View;
  onViewChange: (v: View) => void;
}

const btnStyle = (active: boolean): React.CSSProperties => ({
  width: "40px",
  height: "40px",
  borderRadius: "8px",
  border: "none",
  background: active ? "#1e3a5f" : "transparent",
  color: active ? "#3b82f6" : "#6b7280",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "20px",
});

export default function Sidebar({ activeView, onViewChange }: Props) {
  return (
    <div style={{
      width: "56px",
      height: "100vh",
      background: "#0d1117",
      borderRight: "1px solid #1f2937",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      paddingTop: "16px",
      gap: "8px",
      flexShrink: 0,
    }}>
      <div style={{ marginBottom: "16px", color: "#3b82f6", fontSize: "18px", fontWeight: 700 }}>M</div>

      <button
        onClick={() => onViewChange("orchestrate")}
        title="Orchestrate"
        style={btnStyle(activeView === "orchestrate")}
      >
        ◈
      </button>

      <button
        onClick={() => onViewChange("library")}
        title="Library"
        style={btnStyle(activeView === "library")}
      >
        ▤
      </button>

      <button
        onClick={() => onViewChange("settings")}
        title="Settings"
        style={btnStyle(activeView === "settings")}
      >
        ⚙
      </button>
    </div>
  );
}