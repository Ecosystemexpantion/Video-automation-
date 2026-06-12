import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import StatsChart from "../components/StatsChart";

const DavisVoice = dynamic(() => import("../components/DavisVoice"), { ssr: false });

const PLATFORM_COLORS = {
  youtube: "#FF0000",
  instagram: "#E1306C",
  facebook: "#1877F2",
};

const PLATFORM_ICONS = { youtube: "▶", instagram: "◉", facebook: "f" };

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch("/api/report");
      if (res.ok) {
        setStats(await res.json());
        setLastUpdated(new Date());
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const id = setInterval(fetchStats, 60_000);
    return () => clearInterval(id);
  }, [fetchStats]);

  const platformBreakdown = stats
    ? ["youtube", "instagram", "facebook"].map((p) => ({
        name: p,
        count: (stats.allPosts || []).filter((x) => x.platform === p && x.status === "success").length,
      }))
    : [];

  return (
    <div style={S.page}>
      <header style={S.header}>
        <div>
          <h1 style={S.title}>Davis</h1>
          <p style={S.subtitle}>AI Automation Lead Engine</p>
        </div>
        <div style={{ textAlign: "right" }}>
          {lastUpdated && (
            <p style={S.updated}>
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
          <p style={{ ...S.updated, color: "#333" }}>Auto-refreshes every 60s</p>
        </div>
      </header>

      <div style={S.voiceSection}>
        <DavisVoice stats={stats} />
      </div>

      {loading && !stats && (
        <div style={S.loadingBox}>
          <div style={S.spinner} />
          <p style={{ color: "#888", marginTop: "12px" }}>Loading your data...</p>
        </div>
      )}

      {stats && (
        <>
          <div style={S.statsGrid}>
            <StatCard
              label="Videos Today"
              value={stats.postsToday}
              sub={`${stats.successRate ?? 0}% success rate`}
              color="#25D366"
            />
            <StatCard
              label="Videos This Week"
              value={stats.totalPosts}
              sub="across all platforms"
              color="#4FC3F7"
            />
            <StatCard
              label="WhatsApp Members"
              value={stats.leadsTotal ?? "—"}
              sub="latest snapshot"
              color="#FFD700"
            />
            <StatCard
              label="Failures (24h)"
              value={stats.failures}
              sub={stats.failures > 0 ? "check logs below" : "all clear"}
              color={stats.failures > 0 ? "#FF5252" : "#25D366"}
            />
          </div>

          <div style={S.twoCol}>
            <div style={S.panel}>
              <h2 style={S.panelTitle}>Platform Breakdown (7 days)</h2>
              {platformBreakdown.map(({ name, count }) => (
                <div key={name} style={S.platformRow}>
                  <span style={{ color: PLATFORM_COLORS[name], fontWeight: 700, fontSize: "14px" }}>
                    {PLATFORM_ICONS[name]}  {name.charAt(0).toUpperCase() + name.slice(1)}
                  </span>
                  <div style={S.barTrack}>
                    <div
                      style={{
                        ...S.barFill,
                        width: `${Math.min(100, (count / Math.max(1, stats.totalPosts)) * 100)}%`,
                        background: PLATFORM_COLORS[name],
                      }}
                    />
                  </div>
                  <span style={S.barCount}>{count}</span>
                </div>
              ))}
            </div>

            <div style={S.panel}>
              <h2 style={S.panelTitle}>Posts Per Day</h2>
              <StatsChart posts={stats.allPosts} />
            </div>
          </div>

          <div style={S.panel}>
            <h2 style={S.panelTitle}>Recent Posts</h2>
            <div style={S.table}>
              <div style={S.tableHeader}>
                <span>Platform</span>
                <span>Topic</span>
                <span>Status</span>
                <span>Time</span>
              </div>
              {(stats.recentPosts || []).map((post) => (
                <div key={post.id} style={S.tableRow}>
                  <span style={{ color: PLATFORM_COLORS[post.platform] || "#fff", fontWeight: 600, fontSize: "13px" }}>
                    {PLATFORM_ICONS[post.platform] || "•"}  {post.platform}
                  </span>
                  <span style={S.topicCell} title={post.topic}>
                    {post.topic?.slice(0, 45)}{post.topic?.length > 45 ? "…" : ""}
                  </span>
                  <span style={{ color: post.status === "success" ? "#25D366" : "#FF5252", fontSize: "12px" }}>
                    {post.status === "success" ? "✓ posted" : "✗ failed"}
                  </span>
                  <span style={S.timeCell}>
                    {new Date(post.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
              {(stats.recentPosts || []).length === 0 && (
                <div style={{ padding: "24px", color: "#555", textAlign: "center", fontSize: "14px" }}>
                  No posts yet — run the pipeline to get started.
                </div>
              )}
            </div>
          </div>
        </>
      )}

      <footer style={S.footer}>
        Davis AI Lead Engine · Running on GitHub Actions · Free Forever
      </footer>
    </div>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <div style={S.card}>
      <div style={{ ...S.cardValue, color }}>{value ?? "—"}</div>
      <div style={S.cardLabel}>{label}</div>
      {sub && <div style={S.cardSub}>{sub}</div>}
    </div>
  );
}

const S = {
  page: {
    minHeight: "100vh",
    background: "#0d0d0d",
    color: "#fff",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
    padding: "24px 20px",
    maxWidth: "1100px",
    margin: "0 auto",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "28px",
    borderBottom: "1px solid #1e1e1e",
    paddingBottom: "20px",
  },
  title: { fontSize: "40px", fontWeight: 900, margin: 0, color: "#25D366", letterSpacing: "-1px" },
  subtitle: { color: "#666", margin: "4px 0 0", fontSize: "13px", letterSpacing: "0.5px" },
  updated: { color: "#555", fontSize: "12px", margin: 0 },
  voiceSection: { marginBottom: "28px", display: "flex", justifyContent: "center" },
  loadingBox: { display: "flex", flexDirection: "column", alignItems: "center", padding: "60px 0" },
  spinner: {
    width: "32px", height: "32px", border: "3px solid #222",
    borderTop: "3px solid #25D366", borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "16px",
    marginBottom: "20px",
  },
  card: {
    background: "#161616",
    border: "1px solid #1e1e1e",
    borderRadius: "14px",
    padding: "20px",
    textAlign: "center",
  },
  cardValue: { fontSize: "44px", fontWeight: 900, lineHeight: 1 },
  cardLabel: { color: "#888", fontSize: "13px", marginTop: "6px", fontWeight: 500 },
  cardSub: { color: "#444", fontSize: "11px", marginTop: "4px" },
  twoCol: { display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: "16px", marginBottom: "20px" },
  panel: {
    background: "#161616",
    border: "1px solid #1e1e1e",
    borderRadius: "14px",
    padding: "20px",
    marginBottom: "20px",
  },
  panelTitle: { fontSize: "15px", fontWeight: 600, marginBottom: "16px", color: "#aaa", margin: "0 0 16px" },
  platformRow: { display: "flex", alignItems: "center", gap: "12px", marginBottom: "14px" },
  barTrack: { flex: 1, background: "#222", borderRadius: "4px", height: "8px", overflow: "hidden" },
  barFill: { height: "100%", borderRadius: "4px", transition: "width 0.5s ease" },
  barCount: { color: "#888", fontSize: "13px", minWidth: "24px", textAlign: "right" },
  table: { borderRadius: "10px", overflow: "hidden", border: "1px solid #1e1e1e" },
  tableHeader: {
    display: "grid",
    gridTemplateColumns: "1fr 2.5fr 1fr 1.5fr",
    padding: "10px 16px",
    background: "#111",
    color: "#555",
    fontSize: "11px",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  tableRow: {
    display: "grid",
    gridTemplateColumns: "1fr 2.5fr 1fr 1.5fr",
    padding: "12px 16px",
    borderTop: "1px solid #1a1a1a",
    fontSize: "13px",
    transition: "background 0.15s",
  },
  topicCell: { color: "#ccc", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  timeCell: { color: "#555", fontSize: "11px" },
  footer: { marginTop: "40px", color: "#333", fontSize: "12px", textAlign: "center", paddingTop: "20px", borderTop: "1px solid #1a1a1a" },
};
