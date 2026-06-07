import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, LineElement, PointElement,
  Title, Tooltip, Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend);

export default function StatsChart({ posts }) {
  if (!posts || posts.length === 0) {
    return <div style={styles.empty}>No posts yet. Run the pipeline to see data here.</div>;
  }

  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toISOString().split("T")[0];
  });

  const platformColors = {
    youtube: "#FF0000",
    instagram: "#E1306C",
    facebook: "#1877F2",
  };

  const datasets = ["youtube", "instagram", "facebook"].map((platform) => ({
    label: platform.charAt(0).toUpperCase() + platform.slice(1),
    data: last7Days.map((day) =>
      posts.filter(
        (p) => p.platform === platform && p.created_at.startsWith(day) && p.status === "success"
      ).length
    ),
    backgroundColor: platformColors[platform],
    borderRadius: 4,
  }));

  const data = {
    labels: last7Days.map((d) => d.slice(5)),
    datasets,
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { labels: { color: "#ccc" } },
      title: { display: true, text: "Posts Per Day (Last 7 Days)", color: "#fff" },
    },
    scales: {
      x: { ticks: { color: "#ccc" }, grid: { color: "#333" } },
      y: { ticks: { color: "#ccc", stepSize: 1 }, grid: { color: "#333" } },
    },
  };

  return (
    <div style={styles.container}>
      <Bar data={data} options={options} />
    </div>
  );
}

const styles = {
  container: { background: "#1a1a1a", borderRadius: "12px", padding: "20px" },
  empty: { color: "#666", textAlign: "center", padding: "40px" },
};
