import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { Mic, Square, Send, Plus, Trash2, Volume2, VolumeX, Pencil } from "lucide-react";
import Orb, { OrbState } from "../components/Orb";
import Waveform from "../components/Waveform";
import { api, ChatMessage, ConversationSummary } from "../services/apiClient";

interface ChatReply {
  conversation_id: string;
  reply: ChatMessage;
}

interface ConversationDetail extends ConversationSummary {
  messages: ChatMessage[];
}

const SpeechRecognitionApi: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

const statusText: Record<OrbState, string> = {
  idle: "Tap the microphone and speak",
  listening: "You are speaking...",
  thinking: "AI is thinking...",
  speaking: "AI is speaking...",
  error: "Something went wrong",
};

function plainText(markdown: string) {
  return markdown.replace(/[*_`#>]/g, "").replace(/\[(.*?)\]\(.*?\)/g, "$1");
}

export default function VoiceAgentPage() {
  const [params, setParams] = useSearchParams();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(params.get("c"));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<OrbState>("idle");
  const [mode, setMode] = useState<"voice" | "text">("voice");
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [muted, setMuted] = useState(false);
  const [interim, setInterim] = useState("");
  const [search, setSearch] = useState("");
  const recognition = useRef<any>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const supported = Boolean(SpeechRecognitionApi) && "speechSynthesis" in window;

  const loadConversations = useCallback(async () => {
    setConversations(await api<ConversationSummary[]>(`/conversations${search ? `?q=${encodeURIComponent(search)}` : ""}`));
  }, [search]);

  useEffect(() => {
    loadConversations().catch((err) => setError(err.message));
  }, [loadConversations]);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    api<ConversationDetail>(`/conversations/${activeId}`)
      .then((detail) => setMessages(detail.messages))
      .catch((err) => setError(err.message));
  }, [activeId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, state]);

  useEffect(() => () => {
    window.speechSynthesis?.cancel();
    recognition.current?.abort();
  }, []);

  const speak = (text: string) => {
    if (muted || !("speechSynthesis" in window)) {
      setState("idle");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(plainText(text));
    utterance.onstart = () => setState("speaking");
    utterance.onend = () => setState("idle");
    utterance.onerror = () => setState("idle");
    window.speechSynthesis.speak(utterance);
  };

  const send = async (text: string, via: "voice" | "text") => {
    const message = text.trim();
    if (!message) return;
    setError("");
    setInput("");
    setState("thinking");
    const optimistic: ChatMessage = { id: `tmp-${Date.now()}`, role: "user", content: message, mode: via, tools_used: [], sources: [], created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, optimistic]);
    try {
      const data = await api<ChatReply>("/agent/chat", {
        method: "POST",
        body: JSON.stringify({ message, conversation_id: activeId, mode: via }),
      });
      setMessages((prev) => [...prev, data.reply]);
      if (!activeId) {
        setActiveId(data.conversation_id);
        setParams({ c: data.conversation_id }, { replace: true });
      }
      loadConversations().catch(() => {});
      if (via === "voice") speak(data.reply.content);
      else setState("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setState("error");
    }
  };

  const startListening = () => {
    if (!supported) {
      setError("Voice needs a browser with speech recognition, such as Chrome or Edge. Use text mode instead.");
      return;
    }
    window.speechSynthesis.cancel();
    const instance = new SpeechRecognitionApi();
    instance.lang = navigator.language || "en-US";
    instance.interimResults = true;
    instance.continuous = false;
    let finalText = "";
    instance.onstart = () => {
      setError("");
      setState("listening");
    };
    instance.onresult = (event: any) => {
      let partial = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += piece;
        else partial += piece;
      }
      setInterim(finalText + partial);
    };
    instance.onerror = (event: any) => {
      setInterim("");
      if (event.error === "not-allowed" || event.error === "service-not-allowed") setError("Microphone access was denied. Allow it in your browser settings.");
      else if (event.error === "no-speech") setError("No speech detected. Try again.");
      else if (event.error !== "aborted") setError("Speech recognition failed. Check your connection and try again.");
      setState(event.error === "no-speech" || event.error === "aborted" ? "idle" : "error");
    };
    instance.onend = () => {
      setInterim("");
      if (finalText.trim()) send(finalText, "voice");
      else setState((current) => (current === "listening" ? "idle" : current));
    };
    recognition.current = instance;
    instance.start();
  };

  const stopAll = () => {
    recognition.current?.stop();
    window.speechSynthesis?.cancel();
    setState("idle");
  };

  const newConversation = () => {
    stopAll();
    setActiveId(null);
    setMessages([]);
    setParams({}, { replace: true });
  };

  const remove = async (id: string) => {
    await api(`/conversations/${id}`, { method: "DELETE" });
    if (id === activeId) newConversation();
    loadConversations();
  };

  const rename = async (item: ConversationSummary) => {
    const title = window.prompt("Rename conversation", item.title);
    if (!title || !title.trim()) return;
    await api(`/conversations/${item.id}`, { method: "PATCH", body: JSON.stringify({ title }) });
    loadConversations();
  };

  const busy = state === "thinking";

  return (
    <div className="voice-layout">
      <aside className="history">
        <button className="primary-btn small" onClick={newConversation}><Plus size={16} /> New conversation</button>
        <input className="search" placeholder="Search conversations" value={search} onChange={(e) => setSearch(e.target.value)} />
        <ul>
          {conversations.map((item) => (
            <li key={item.id} className={item.id === activeId ? "active" : ""}>
              <button className="history-title" onClick={() => setActiveId(item.id)}>{item.title}</button>
              <button className="icon-btn" onClick={() => rename(item)} aria-label="Rename"><Pencil size={14} /></button>
              <button className="icon-btn" onClick={() => remove(item.id)} aria-label="Delete"><Trash2 size={14} /></button>
            </li>
          ))}
          {conversations.length === 0 && <li className="muted empty">No conversations yet</li>}
        </ul>
      </aside>

      <section className="stage">
        <div className="mode-switch">
          <button className={mode === "voice" ? "on" : ""} onClick={() => setMode("voice")}>Voice mode</button>
          <button className={mode === "text" ? "on" : ""} onClick={() => setMode("text")}>Text mode</button>
        </div>

        {mode === "voice" && (
          <div className="voice-center">
            <Orb state={state} />
            <p className="status" aria-live="polite">{statusText[state]}</p>
            <Waveform active={state === "listening" || state === "speaking"} />
            {interim && <p className="interim">{interim}</p>}
            <div className="voice-controls">
              <button className="icon-btn big" onClick={() => setMuted(!muted)} aria-label={muted ? "Unmute voice" : "Mute voice"}>
                {muted ? <VolumeX size={22} /> : <Volume2 size={22} />}
              </button>
              <button className={`mic-btn ${state === "listening" ? "live" : ""}`} onClick={state === "listening" ? stopAll : startListening} disabled={busy} aria-label="Microphone">
                <Mic size={34} />
              </button>
              <button className="icon-btn big" onClick={stopAll} aria-label="Stop"><Square size={22} /></button>
            </div>
            {!supported && <p className="form-error">This browser has no speech recognition. Use Chrome or Edge, or switch to text mode.</p>}
          </div>
        )}

        <div className={`transcript ${mode === "text" ? "tall" : ""}`}>
          {messages.map((m) => (
            <div key={m.id} className={`bubble ${m.role}`}>
              <ReactMarkdown>{m.content}</ReactMarkdown>
              {m.role === "assistant" && (m.sources.length > 0 || m.tools_used.length > 0) && (
                <div className="meta">
                  {m.sources.map((s) => <span key={s} className="chip">Source: {s}</span>)}
                  {m.tools_used.map((t, i) => <span key={`${t}${i}`} className="chip tool">{t}</span>)}
                </div>
              )}
              <small>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small>
            </div>
          ))}
          {busy && <div className="bubble assistant typing">Thinking...</div>}
          <div ref={bottom} />
        </div>

        {error && <div className="form-error" role="alert">{error}</div>}

        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input, "text"); }}>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a message" maxLength={4000} disabled={busy} />
          <button className="primary-btn small" type="submit" disabled={busy || !input.trim()}><Send size={16} /> Send</button>
        </form>
      </section>
    </div>
  );
}
