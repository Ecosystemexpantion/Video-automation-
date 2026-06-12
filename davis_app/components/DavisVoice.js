import { useEffect, useRef, useState } from "react";

const WAKE_PHRASE = "hey davis";

const COMMANDS = {
  "leads today": "leads_today",
  "leads this week": "leads_week",
  "total leads": "leads_total",
  "how many leads": "leads_total",
  "how many posts": "posts_today",
  "how many videos": "posts_today",
  "videos today": "posts_today",
  "best platform": "best_platform",
  "which platform": "best_platform",
  "any failures": "failures",
  "group count": "leads_total",
  "how are we doing": "summary",
  "give me a report": "summary",
  "full report": "summary",
  "how is it going": "summary",
};

export default function DavisVoice({ stats }) {
  const [status, setStatus] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [lastResponse, setLastResponse] = useState("");
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef(null);
  const awaitingCommandRef = useRef(false);
  const timeoutRef = useRef(null);

  const speak = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.92;
    utterance.pitch = 1.05;
    utterance.volume = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const preferred =
      voices.find((v) => v.lang === "en-US" && /female|aria|samantha|zira/i.test(v.name)) ||
      voices.find((v) => v.lang === "en-US") ||
      voices[0];
    if (preferred) utterance.voice = preferred;
    window.speechSynthesis.speak(utterance);
    setLastResponse(text);
  };

  const buildResponse = (commandKey) => {
    if (!stats) return "I'm still loading your data. Give me a moment.";
    const { postsToday = 0, totalPosts = 0, leadsTotal = 0, leadsToday = 0, leadsWeek = 0, failures = 0, bestPlatform = "YouTube" } = stats;

    const map = {
      leads_today: `Today you got ${leadsToday} new WhatsApp group members. Keep the momentum going!`,
      leads_week: `This week you gained ${leadsWeek} new members across all platforms.`,
      leads_total: `Your WhatsApp group currently has ${leadsTotal} members.`,
      posts_today: `Today the system posted ${postsToday} videos across your platforms.`,
      best_platform: `Your best performing platform this week is ${bestPlatform}.`,
      failures:
        failures > 0
          ? `There ${failures === 1 ? "was" : "were"} ${failures} failed post${failures === 1 ? "" : "s"} in the last 24 hours. Check the dashboard.`
          : "No failures in the last 24 hours. Everything is running smoothly.",
      summary: `Here's your report: ${postsToday} videos posted today, ${totalPosts} total this week, ${leadsTotal} WhatsApp members, top platform is ${bestPlatform}${failures > 0 ? `, and ${failures} failure${failures === 1 ? "" : "s"} to check` : ", and no failures"}.`,
    };

    return map[commandKey] || "I didn't understand that. Try asking about leads, posts, or which platform is doing best.";
  };

  const matchCommand = (text) => {
    const lower = text.toLowerCase();
    for (const [phrase, key] of Object.entries(COMMANDS)) {
      if (lower.includes(phrase)) return key;
    }
    return null;
  };

  const activateListen = () => {
    awaitingCommandRef.current = true;
    setStatus("listening");
    speak("Yes? What would you like to know?");
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      awaitingCommandRef.current = false;
      setStatus("watching");
    }, 7000);
  };

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setSupported(false);
      return;
    }

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    recognition.onresult = (event) => {
      const text = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      setTranscript(text);

      if (!awaitingCommandRef.current) {
        if (text.includes(WAKE_PHRASE)) activateListen();
        return;
      }

      clearTimeout(timeoutRef.current);
      awaitingCommandRef.current = false;
      setStatus("watching");

      const cmd = matchCommand(text);
      speak(buildResponse(cmd));
    };

    recognition.onerror = (e) => {
      if (e.error !== "no-speech") {
        recognition.stop();
        setTimeout(() => { try { recognition.start(); } catch (_) {} }, 1500);
      }
    };

    recognition.onend = () => {
      setTimeout(() => { try { recognition.start(); } catch (_) {} }, 500);
    };

    recognition.start();
    setStatus("watching");

    return () => {
      clearTimeout(timeoutRef.current);
      recognition.stop();
    };
  }, []);

  if (!supported) {
    return (
      <div style={S.container}>
        <span style={{ color: "#555", fontSize: "13px" }}>
          Voice not supported in this browser. Use Chrome on desktop.
        </span>
      </div>
    );
  }

  const dotColor = { idle: "#333", watching: "#25D366", listening: "#FFD700" }[status];
  const label = {
    idle: "Offline",
    watching: 'Say "Hey Davis" to activate',
    listening: "Listening… ask me anything",
  }[status];

  return (
    <div style={S.container}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={{ ...S.dot, background: dotColor, boxShadow: status === "listening" ? `0 0 14px ${dotColor}` : "none" }} />
        <span style={{ color: status === "listening" ? "#FFD700" : "#888", fontSize: "14px", fontWeight: status === "listening" ? 600 : 400 }}>
          {label}
        </span>
      </div>

      {status === "listening" && (
        <div style={S.waves}>
          {[0, 0.15, 0.3, 0.15, 0].map((delay, i) => (
            <div key={i} style={{ ...S.wave, animationDelay: `${delay}s` }} />
          ))}
        </div>
      )}

      {transcript && (
        <p style={S.transcript}>You: &ldquo;{transcript}&rdquo;</p>
      )}
      {lastResponse && (
        <p style={S.response}>Davis: &ldquo;{lastResponse}&rdquo;</p>
      )}

      <style>{`
        @keyframes wave {
          0%, 100% { transform: scaleY(0.4); }
          50% { transform: scaleY(1.4); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

const S = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "10px",
    padding: "20px 28px",
    background: "#161616",
    border: "1px solid #1e1e1e",
    borderRadius: "16px",
    minWidth: "340px",
    maxWidth: "500px",
  },
  dot: {
    width: "12px",
    height: "12px",
    borderRadius: "50%",
    transition: "background 0.3s, box-shadow 0.3s",
    flexShrink: 0,
  },
  waves: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    height: "24px",
  },
  wave: {
    width: "4px",
    height: "20px",
    background: "#FFD700",
    borderRadius: "2px",
    animation: "wave 0.8s ease-in-out infinite",
  },
  transcript: {
    color: "#666",
    fontSize: "12px",
    fontStyle: "italic",
    margin: 0,
    textAlign: "center",
    maxWidth: "380px",
  },
  response: {
    color: "#25D366",
    fontSize: "13px",
    margin: 0,
    textAlign: "center",
    maxWidth: "380px",
    lineHeight: 1.5,
  },
};
