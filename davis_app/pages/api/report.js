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
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekStart = new Date(now);
  weekStart.setDate(weekStart.getDate() - 7);
  const prevWeekStart = new Date(now);
  prevWeekStart.setDate(prevWeekStart.getDate() - 14);

  const [todayRes, weekRes, recentRes, allLeadsRes] = await Promise.all([
    supabase.from("posts").select("*").gte("created_at", todayStart.toISOString()),
    supabase.from("posts").select("*").gte("created_at", weekStart.toISOString()),
    supabase.from("posts").select("*").order("created_at", { ascending: false }).limit(20),
    supabase.from("leads").select("*").order("recorded_at", { ascending: false }).limit(30),
  ]);

  const todayData = todayRes.data || [];
  const weekData = weekRes.data || [];
  const recent = recentRes.data || [];
  const leads = allLeadsRes.data || [];

  const successToday = todayData.filter((p) => p.status === "success");
  const failuresToday = todayData.filter((p) => p.status === "failed").length;
  const successWeek = weekData.filter((p) => p.status === "success");
  const successRate = todayData.length > 0
    ? Math.round((successToday.length / todayData.length) * 100)
    : 100;

  const platformCounts = {};
  successWeek.forEach((p) => {
    platformCounts[p.platform] = (platformCounts[p.platform] || 0) + 1;
  });
  const bestPlatform = Object.entries(platformCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || "none";

  const latestLead = leads[0];
  const leadsTotal = latestLead?.whatsapp_member_count ?? 0;

  const todayLeadsEntry = leads.find((l) => new Date(l.recorded_at) >= todayStart);
  const weekLeadsEntry = leads.find((l) => new Date(l.recorded_at) >= weekStart);
  const leadsToday = todayLeadsEntry?.whatsapp_member_count
    ? leadsTotal - (leads[leads.indexOf(todayLeadsEntry) + 1]?.whatsapp_member_count ?? leadsTotal)
    : 0;
  const leadsWeek = weekLeadsEntry?.whatsapp_member_count
    ? leadsTotal - (leads[leads.indexOf(weekLeadsEntry) + 1]?.whatsapp_member_count ?? leadsTotal)
    : 0;

  res.setHeader("Cache-Control", "no-store");
  res.json({
    postsToday: successToday.length,
    totalPosts: successWeek.length,
    successRate,
    bestPlatform,
    failures: failuresToday,
    leadsTotal,
    leadsToday: Math.max(0, leadsToday),
    leadsWeek: Math.max(0, leadsWeek),
    recentPosts: recent,
    allPosts: weekData,
  });
}
