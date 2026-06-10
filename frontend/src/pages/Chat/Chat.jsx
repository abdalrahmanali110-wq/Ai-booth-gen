import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate, useParams } from "react-router-dom";
import SessionSidebar from "../../components/SessionSidebar";
import RequirementsPanel from "../../components/RequirementsPanel";
import MessageList from "../../components/MessageList";
import {
  createSession,
  deleteSession,
  generateBooth,
  getMessages,
  getSession,
  listSessions,
  sendMessage,
  updateSession,
} from "../../services/chatService";
import { useTheme } from "../../hooks/useTheme";

const DEFAULT_TITLE = "New Booth Consultation";
const MOBILE_BREAKPOINT = 900;

function mapMessages(rows) {
  return (rows || []).map((row) => ({
    id: row.id,
    role: row.role,
    message: row.message,
  }));
}

function isMobileViewport() {
  return typeof window !== "undefined" && window.innerWidth < MOBILE_BREAKPOINT;
}

export default function Chat() {
  const { sessionId: routeSessionId } = useParams();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [requirements, setRequirements] = useState({});
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [generationResult, setGenerationResult] = useState(null);
  const [error, setError] = useState("");
  const [requirementsComplete, setRequirementsComplete] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [regenerateError, setRegenerateError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(() => !isMobileViewport());
  const [isMobile, setIsMobile] = useState(isMobileViewport);

  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const chatStageRef = useRef(null);
  const shouldScrollRef = useRef(true);
  const loadingSessionRef = useRef(null);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions || []);
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const patchSessionTitle = useCallback((id, title) => {
    if (!title) return;
    setSessions((prev) =>
      prev.map((session) =>
        session.id === id ? { ...session, title } : session
      )
    );
  }, []);

  const loadSession = useCallback(async (id) => {
    if (!id) return;

    loadingSessionRef.current = id;
    setSessionLoading(true);
    setError("");
    setSessionId(id);

    try {
      const [sessionData, messagesData] = await Promise.all([
        getSession(id),
        getMessages(id),
      ]);

      if (loadingSessionRef.current !== id) return;

      setMessages(mapMessages(messagesData.messages));
      setRequirements(sessionData.requirements || {});
      setRequirementsComplete(
        Object.values(sessionData.requirements || {}).filter(Boolean).length >= 6
      );
      setGenerationResult(sessionData.generation_result || null);
      setRegenerateError("");
      shouldScrollRef.current = true;
    } catch (err) {
      if (loadingSessionRef.current !== id) return;
      setError(err.response?.data?.detail || "Failed to load conversation.");
      setMessages([]);
      setRequirements({});
    } finally {
      if (loadingSessionRef.current === id) {
        setSessionLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    let timeoutId = null;

    function handleResize() {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        const mobile = isMobileViewport();
        setIsMobile(mobile);
        if (!mobile) {
          setSidebarOpen(true);
        }
      }, 150);
    }

    window.addEventListener("resize", handleResize);
    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  useEffect(() => {
    if (routeSessionId) {
      loadSession(routeSessionId);
    } else {
      loadingSessionRef.current = null;
      setSessionId(null);
      setMessages([]);
      setRequirements({});
      setGenerationResult(null);
      setError("");
      setSessionLoading(false);
    }
  }, [routeSessionId, loadSession]);

  useEffect(() => {
    if (!shouldScrollRef.current) return;

    const container = chatStageRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
      return;
    }

    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [input]);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((open) => {
      if (!open) {
        setDetailsOpen(false);
      }
      return !open;
    });
  }, []);

  const toggleDetails = useCallback(() => {
    setDetailsOpen((open) => {
      if (!open && isMobileViewport()) {
        setSidebarOpen(false);
      }
      return !open;
    });
  }, []);

  const closeSidebar = useCallback(() => {
    if (isMobileViewport()) {
      setSidebarOpen(false);
    }
  }, []);

  const handleNewChat = useCallback(async () => {
    setError("");
    setLoading(true);
    closeSidebar();

    try {
      const data = await createSession();
      await refreshSessions();
      navigate(`/chat/${data.session.id}`);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to start chat. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  }, [closeSidebar, navigate, refreshSessions]);

  const handleSelectSession = useCallback(
    (id) => {
      if (id === sessionId) {
        closeSidebar();
        return;
      }
      navigate(`/chat/${id}`);
      closeSidebar();
    },
    [sessionId, navigate, closeSidebar]
  );

  const handleRenameSession = useCallback(async (id, title) => {
    try {
      const data = await updateSession(id, title);
      patchSessionTitle(id, data.session.title);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to rename session.");
    }
  }, [patchSessionTitle]);

  const handleDeleteSession = useCallback(
    async (id) => {
      const session = sessions.find((s) => s.id === id);
      const label = session?.title || "this conversation";
      if (!window.confirm(`Delete "${label}"? This cannot be undone.`)) {
        return;
      }

      try {
        await deleteSession(id);
        setSessions((prev) => prev.filter((session) => session.id !== id));

        if (sessionId === id) {
          navigate("/chat");
          setSessionId(null);
          setMessages([]);
          setRequirements({});
          setGenerationResult(null);
        }
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to delete session.");
      }
    },
    [sessions, sessionId, navigate]
  );

  const handleRegenerate = useCallback(async () => {
    if (!sessionId || regenerating) return;

    setRegenerating(true);
    setRegenerateError("");
    setError("");

    try {
      const data = await generateBooth(sessionId);
      setGenerationResult(data.result);
      shouldScrollRef.current = true;
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-gen-${Date.now()}`,
          role: "assistant",
          message: (
            "Your booth concept has been regenerated. "
            "See the updated analysis below for UAE cost estimates and contractors."
          ),
        },
      ]);
    } catch (err) {
      const message =
        err.response?.data?.detail || "Image generation failed.";
      setRegenerateError(message);
      setError(message);
    } finally {
      setRegenerating(false);
    }
  }, [sessionId, regenerating]);

  const handleSend = useCallback(
    async (event) => {
      event.preventDefault();
      if (!input.trim() || loading) return;

      let activeId = sessionId;

      if (!activeId) {
        try {
          const data = await createSession();
          activeId = data.session.id;
          setSessionId(activeId);
          navigate(`/chat/${activeId}`, { replace: true });
          setSessions((prev) => [data.session, ...prev]);
        } catch (err) {
          setError(err.response?.data?.detail || "Failed to create session.");
          return;
        }
      }

      const userText = input.trim();
      setInput("");
      setError("");
      shouldScrollRef.current = true;
      closeSidebar();

      setMessages((prev) => [
        ...prev,
        { id: `user-${Date.now()}`, role: "user", message: userText },
      ]);

      setLoading(true);

      try {
        const data = await sendMessage(activeId, userText);

        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            message: data.reply,
          },
        ]);
        setRequirements(data.requirements || {});
        setRequirementsComplete(Boolean(data.requirements_complete));

        if (data.generation_result) {
          setGenerationResult(data.generation_result);
        }

        const eventName = data.requirements?.event_name;
        if (eventName) {
          setSessions((prev) => {
            const existing = prev.find((s) => s.id === activeId);
            if (
              !existing ||
              (existing.title && existing.title !== DEFAULT_TITLE)
            ) {
              return prev;
            }
            return prev.map((session) =>
              session.id === activeId
                ? { ...session, title: eventName }
                : session
            );
          });
        }
      } catch (err) {
        const isTimeout = err.code === "ECONNABORTED";
        setError(
          isTimeout
            ? "Request timed out. Image generation can take up to a minute."
            : err.response?.data?.detail || "Failed to send message."
        );
      } finally {
        setLoading(false);
      }
    },
    [input, loading, sessionId, navigate, closeSidebar]
  );

  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSend(event);
      }
    },
    [handleSend]
  );

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === sessionId),
    [sessions, sessionId]
  );

  const showWelcome = !sessionLoading && messages.length === 0 && !loading;
  const generationImageUrl =
    generationResult?.generated_image?.image_url || null;
  const consultationReport = generationResult?.consultation_report || null;

  return (
    <div
      className={`app-shell${sidebarOpen ? " sidebar-open" : ""}${
        detailsOpen ? " details-open" : ""
      }`}
    >
      <SessionSidebar
        sessions={sessions}
        activeSessionId={sessionId}
        loading={sessionsLoading}
        theme={theme}
        onToggleTheme={toggleTheme}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
      />

      <div className="chat-shell">
        <header className="chat-topbar">
          <button
            type="button"
            className="icon-btn mobile-menu-btn"
            onClick={toggleSidebar}
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            aria-expanded={sidebarOpen}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M4 7h16M4 12h16M4 17h16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>

          <div className="topbar-title">
            <h1>{activeSession?.title || "Booth consultation"}</h1>
            <p>AI exhibition consultant</p>
          </div>

          <button
            type="button"
            className={`details-toggle pressable${detailsOpen ? " active" : ""}`}
            onClick={toggleDetails}
            aria-expanded={detailsOpen}
          >
            Details
          </button>
        </header>

        <main className="chat-stage" ref={chatStageRef}>
          <div className="chat-thread">
            {sessionLoading && (
              <div className="message assistant">
                <div className="message-content">
                  <p>Loading conversation...</p>
                </div>
              </div>
            )}

            {showWelcome && (
              <div className="welcome-screen">
                <div className="welcome-icon" aria-hidden="true" />
                <h2>Design your exhibition booth</h2>
                <p>
                  Tell me about your event, booth size, budget, and style.
                  I&apos;ll collect the details and generate a concept for you.
                </p>
                <div className="welcome-suggestions">
                  {[
                    "I need a booth for Arab Health",
                    "6x6 booth for a book expo in Sharjah",
                    "Modern tech booth, budget 50,000 AED",
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="suggestion-chip pressable"
                      onClick={() => setInput(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <MessageList
              messages={messages}
              loading={loading}
              requirementsComplete={requirementsComplete}
              generationImageUrl={generationImageUrl}
              consultationReport={consultationReport}
              bottomRef={bottomRef}
            />
          </div>
        </main>

        {error && (
          <div className="chat-error-banner">
            <p>{error}</p>
            {requirementsComplete && sessionId && (
              <button
                type="button"
                onClick={handleRegenerate}
                disabled={regenerating}
              >
                {regenerating ? "Generating..." : "Retry generation"}
              </button>
            )}
          </div>
        )}

        <footer className="chat-composer">
          <form className="composer-form" onSubmit={handleSend}>
            <div className="composer-box">
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message Booth AI..."
                disabled={loading}
              />
              <button
                type="submit"
                className="send-btn"
                disabled={!input.trim() || loading}
                aria-label="Send message"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 19V5M5 12l7-7 7 7"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
            <p className="composer-hint">
              Booth AI can make mistakes. Verify important details before ordering.
            </p>
          </form>
        </footer>
      </div>

      {isMobile && sidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop visible"
          onClick={closeSidebar}
          aria-label="Close sidebar"
        />
      )}

      <RequirementsPanel
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        requirements={requirements}
        generationResult={generationResult}
        onRegenerate={handleRegenerate}
        regenerating={regenerating}
        regenerateError={regenerateError}
      />
    </div>
  );
}
