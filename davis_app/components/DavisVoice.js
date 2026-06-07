import { useEffect, useRef, useState } from "react";

const WAKE_PHRASE = "hey davis";
const COMMANDS = {
  "leads today": "leads_today",
  "leads this week": "leads_week",
  "total leads": "leads_total",
  "how many posts": "posts_today",
  "how many videos": "posts_today",
  "best platform": "best_platform",
  "any failures": "failures",
  "group count": "leads_total",
  "how are we doing": "summary",
  "give me a report": "summary",
};

export default function DavisVoice({ onCommand, stats }) {
  const [status, setStatus] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [lastResponse, setLastResponse] = useState("");
  const recognitionRef = useRef(null);
  const listeningRef = useRef(false);

  const speak = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(
      (v) => v.lang === "en-US" && v.name.toLowerCase().includes("female")
    ) || voices.find((v) => v.lang === "en-US");
    if (preferred) utterance.voice = preferred;
    window.speechSynthesis.speak(utterance);
    setLastResponse(text);
  };

  const handleCommand = (commandKey) => {
    if (!stats) {
      speak("I'm still loading your data. Please wait a moment.");
      return;
    }

    const responses = {
      leads_today: `Today you have ${stats.leadsToday ?? 0} new WhatsApp group members. Keep it up!`,
      leads_week: `This week you gained ${stats.leadsWeek ?? 0} new group members across all platforms.`,
      leads_total: `Your WhatsApp group currently has ${stats.leadsTotal ?? 0} total members.`,
      posts_today: `Today the system posted ${stats.postsToday ?? 0} videos across your platforms.`,
      best_platform: `Your best performing platform is ${stats.bestPlatform ?? "YouTube"} with the most views this week.`,
      failures: stats.failures > 0
        ? `There ${stats.failures === 1 ? "was" : "were"} ${stats.failures} failed post${stats.failures === 1 ? "" : "s"} in the last 24 hours. Check the dashboard for details.`
        : "No failures in the last 24 hours. Everything is running smoothly!",
      summary: `Here's your summary: ${stats.postsToday ?? 0} videos posted today, ${stats.leadsToday ?? 0} new WhatsApp members, and ${stats.totalPosts ?? 0} total videos this week. Your top platform is ${stats.bestPlatform ?? "YouTube"}.`,
    };

    const response = responses[commandKey] || "I didn't understand that command. Try asking about leads, posts, or which platform is working best.";
    speak(response);
    onCommand?.(commandKey, response);
  };

  const matchCommand = (text) => {
    const lower = text.toLowerCase();
    for (const [phrase, key] of Object.entries(COMMANDS)) {
      if (lower.includes(phrase)) return key;
    }
    return null;
  };

  useEffect(() => {
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    recognition.onresult = (event) => {
      const last = event.results[event.results.length - 1];
      const text = last[0].transcript.toLowerCase().trim();
      setTranscript(text);

      if (!listeningRef.current && text.includes(WAKE_PHRASE)) {
        listeningRef.current = true;
        setStatus("listening");
        speak("Yes? What would you like to know?");
        setTimeout(() => { listeningRef.current = false; setStatus("watching"); }, 6000);
        return;
      }

      if (listeningRef.current) {
        const cmd = matchCommand(text);
        if (cmd) {
          handleCommand(cmd);
        } else {
          speak("I didn't catch that. Try asking about leads, posts, or platform performance.");
        }
        listeningRef.current = false;
        setStatus("watching");
      }
    };

    recognition.onerror = () => {
      recognition.stop();
      setTimeout(() => recognition.start(), 1000);
    };

    recognition.onend = () => {
      if (status !== "idle") recognition.start();
    };

    recognition.start();
    setStatus("watching");

    return () => recognition.stop();
  }, []);

  const statusColors = { idle: "#666", watching: "#25D366", listening: "#FFD700" };
  const statusLabels = {
    idle: "Offline",
    watching: 'Watching — say "Hey Davis"',
    listening: "Listening...",
  };

  return (
    <div style={styles.container}>
      <div style={{ ...styles.dot, background: statusColors[status] }} />
      <span style={styles.label}>{statusLabels[status]}</span>
      {transcript && (
        <p style={styles.transcript}>You: "{transcript}"</p>
      )}
      {lastResponse && (
        <p style={styles.response}>Davis: "{lastResponse}"</p>
      )}
    </div>
  );
}

const styles = {
  container: {
    display: "flex", flexDirection: "column", alignItems: "center",
    gap: "8px", padding: "16px", background: "#1a1a1a",
    borderRadius: "12px", minWidth: "300px",
  },
  dot: {
    width: "16px", height: "16px", borderRadius: "50%",
    boxShadow: "0 0 12px currentColor", transition: "background 0.3s",
  },
  label: { color: "#ccc", fontSize: "14px" },
  transcript: { color: "#888", fontSize: "13px", fontStyle: "italic", margin: 0 },
  response: { color: "#25D366", fontSize: "14px", margin: 0, textAlign: "center" },
};
