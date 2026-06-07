import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import StatsChart from "../components/StatsChart";

const DavisVoice = dynamic(() => import("../components/DavisVoice"), { ssr: false });

const PLATFORM_COLORS = {
  youtube: "#FF0000",
  instagram: "#E1306C",
  facebook: "#1877F2",
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchStats = async () => {
    const res = await fetch("/api/report");
    if (res.ok) {
      const data = await res.json();
      setStats(data);
      setLastUpdated(new Date().toLocaleTimeString());
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Davis</h1>
          <p style={styles.subtitle}>AI Automation Lead Engine</p>
        </div>
        {lastUpdated && (
          <span style={styles.updated}>Updated {lastUpdated}</span>
        )}
      </header>

      <div style={styles.voiceSection}>
        <DavisVoice stats={stats} />
      </div>

      {stats && (
        <>
          <div style={styles.statsGrid}>
            <StatCard label="Videos Today" value={stats.postsToday} color="#25D366" />
            <StatCard label="Videos This Week" value={stats.totalPosts} color="#4FC3F7" />
            <StatCard label="WhatsApp Members" value={stats.leadsTotal} color="#FFD700" />
            <StatCard label="Failures (24h)" value={stats.failures} color={stats.failures > 0 ? "#FF5252" : "#25D366"} />
          </div>

          <div style={styles.section}>
            <StatsChart posts={stats.allPosts} />
          </div>

          <div style={styles.section}>
            <h2 style={styles.sectionTitle}>Recent Posts</h2>
            <div style={styles.table}>
              <div style={styles.tableHeader}>
                <span>Platform</span>
                <span>Topic</span>
                <span>Status</span>
                <span>Time</span>
              </div>
              {(stats.recentPosts || []).map((post) => (
                <div key={post.id} style={styles.tableRow}>
                  <span style={{ color: PLATFORM_COLORS[post.platform] || "#fff", fontWeight: 600 }}>
                    {post.platform}
                  </span>
                  <span style={styles.topicCell} title={post.topic}>
                    {post.topic?.slice(0, 40)}{post.topic?.length > 40 ? "…" : ""}
                  </span>
                  <span style={{ color: post.status === "success" ? "#25D366" : "#FF5252" }}>
                    {post.status}
                  </span>
                  <span style={styles.timeCell}>
                    {new Date(post.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div style={styles.card}>
      <div style={{ ...styles.cardValue, color }}>{value ?? "—"}</div>
      <div style={styles.cardLabel}>{label}</div>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#111", color: "#fff", fontFamily: "system-ui, sans-serif", padding: "24px", maxWidth: "1000px", margin: "0 auto" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" },
  title: { fontSize: "36px", fontWeight: 800, margin: 0, color: "#25D366" },
  subtitle: { color: "#888", margin: "4px 0 0", fontSize: "14px" },
  updated: { color: "#555", fontSize: "12px" },
  voiceSection: { marginBottom: "24px", display: "flex", justifyContent: "center" },
  statsGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" },
  card: { background: "#1a1a1a", borderRadius: "12px", padding: "20px", textAlign: "center" },
  cardValue: { fontSize: "42px", fontWeight: 800 },
  cardLabel: { color: "#888", fontSize: "13px", marginTop: "4px" },
  section: { marginBottom: "24px" },
  sectionTitle: { fontSize: "18px", fontWeight: 600, marginBottom: "12px", color: "#ccc" },
  table: { background: "#1a1a1a", borderRadius: "12px", overflow: "hidden" },
  tableHeader: { display: "grid", gridTemplateColumns: "1fr 2fr 1fr 1.5fr", padding: "12px 16px", background: "#222", color: "#888", fontSize: "12px", textTransform: "uppercase" },
  tableRow: { display: "grid", gridTemplateColumns: "1fr 2fr 1fr 1.5fr", padding: "12px 16px", borderTop: "1px solid #222", fontSize: "13px" },
  topicCell: { color: "#ccc", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  timeCell: { color: "#666", fontSize: "12px" },
};
