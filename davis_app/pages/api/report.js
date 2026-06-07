import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const now = new Date();
  const todayStart = new Date(now);
  todayStart.setHours(0, 0, 0, 0);

  const weekStart = new Date(now);
  weekStart.setDate(weekStart.getDate() - 7);

  const [todayPosts, weekPosts, recentPosts, latestLead] = await Promise.all([
    supabase
      .from("posts")
      .select("*")
      .gte("created_at", todayStart.toISOString()),
    supabase
      .from("posts")
      .select("*")
      .gte("created_at", weekStart.toISOString()),
    supabase
      .from("posts")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(20),
    supabase
      .from("leads")
      .select("*")
      .order("recorded_at", { ascending: false })
      .limit(1),
  ]);

  const todayData = todayPosts.data || [];
  const weekData = weekPosts.data || [];
  const recent = recentPosts.data || [];

  const platformCounts = {};
  weekData.filter((p) => p.status === "success").forEach((p) => {
    platformCounts[p.platform] = (platformCounts[p.platform] || 0) + 1;
  });
  const bestPlatform = Object.entries(platformCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "none";

  const failures24h = todayData.filter((p) => p.status === "failed").length;

  const leadsToday = latestLead.data?.[0]?.whatsapp_member_count ?? 0;
  const leadsTotal = latestLead.data?.[0]?.whatsapp_member_count ?? 0;

  res.json({
    postsToday: todayData.filter((p) => p.status === "success").length,
    totalPosts: weekData.filter((p) => p.status === "success").length,
    bestPlatform,
    failures: failures24h,
    leadsToday,
    leadsWeek: leadsToday,
    leadsTotal,
    recentPosts: recent,
    allPosts: weekData,
  });
}
