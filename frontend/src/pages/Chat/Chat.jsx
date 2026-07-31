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
import BoothWorkspace from "../../components/BoothWorkspace";
import {
  createSession,
  deleteSession,
  generateBooth,
  getMessages,
  getQuota,
  getSession,
  listSessions,
  sendMessage,
  updateSession,
} from "../../services/chatService";
import { createModel3D, getModel3DJob } from "../../services/model3dService";
import { completeOAuth } from "../../services/authService";
import { getSupabaseClient } from "../../services/supabaseClient";
import {
  clearStoredAuth,
  consumePendingConvert,
  getPendingAuthSession,
  getStoredAuth,
  setStoredAuth,
} from "../../services/storage";
import AuthModal from "../../components/AuthModal";
import { getQuickReplies } from "../../utils/intake";
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
  const [historyLocked, setHistoryLocked] = useState(
    () => !getStoredAuth()?.auth_user_id
  );
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
  const [quota, setQuota] = useState({
    used: 0,
    remaining: 999,
    max: 999,
    unlimited: true,
  });
  const [authUser, setAuthUser] = useState(() => getStoredAuth());
  const [authOpen, setAuthOpen] = useState(false);
  const [converting3d, setConverting3d] = useState(false);
  const [modelJob, setModelJob] = useState(null);
  const [authIntent, setAuthIntent] = useState("signin");

  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const chatStageRef = useRef(null);
  const shouldScrollRef = useRef(true);
  const loadingSessionRef = useRef(null);

  const refreshSessions = useCallback(async () => {
    const signedIn = Boolean(getStoredAuth()?.auth_user_id);
    // Client-side gate: never show history without Google sign-in,
    // even if an older API still returns sessions.
    if (!signedIn) {
      setHistoryLocked(true);
      setSessions([]);
      try {
        const data = await listSessions();
        if (data.quota) setQuota(data.quota);
      } catch {
        // ignore
      } finally {
        setSessionsLoading(false);
      }
      return;
    }

    try {
      const data = await listSessions();
      setHistoryLocked(Boolean(data.history_locked));
      setSessions(data.history_locked ? [] : data.sessions || []);
      if (data.quota) setQuota(data.quota);
    } catch {
      setSessions([]);
      setHistoryLocked(true);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const refreshQuota = useCallback(async () => {
    try {
      const data = await getQuota();
      if (data.quota) setQuota(data.quota);
    } catch {
      // ignore until migration applied
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
      setModelJob(null);
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
    refreshQuota();
  }, [refreshSessions, refreshQuota]);


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
      if (data.quota) setQuota(data.quota);
      setModelJob(null);
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
      if (data.quota) setQuota(data.quota);
      shouldScrollRef.current = true;
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-gen-${Date.now()}`,
          role: "assistant",
          message:
            "Your booth concept has been regenerated. See the updated analysis below.",
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

  const runConvertTo3D = useCallback(
    async (auth) => {
      const imageUrl = generationResult?.generated_image?.image_url;
      const imageId = generationResult?.generated_image?.id;
      if (!sessionId || !imageUrl) return;

      setConverting3d(true);
      setError("");
      setModelJob(null);
      try {
        const data = await createModel3D(sessionId, {
          source_image_url: imageUrl,
          source_image_id: imageId,
          auth_user_id: auth?.auth_user_id || undefined,
          process_now: true,
        });
        let job = data.job;
        setModelJob(job);

        if (job?.status === "FAILED") {
          setError(job.error || "3D conversion failed.");
          return;
        }

        // Poll if still pending/processing
        let tries = 0;
        while (
          job &&
          ["PENDING", "PROCESSING"].includes(job.status) &&
          tries < 40
        ) {
          await new Promise((r) => setTimeout(r, 2000));
          if (String(job.id).startsWith("local-")) break;
          const polled = await getModel3DJob(job.id);
          job = polled.job;
          setModelJob(job);
          tries += 1;
        }

        if (job?.status === "FAILED") {
          setError(job.error || "3D conversion failed.");
        }
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to convert to 3D.");
      } finally {
        setConverting3d(false);
      }
    },
    [sessionId, generationResult]
  );

  const handleConvertTo3D = useCallback(() => {
    const auth = authUser || getStoredAuth();
    if (!auth?.auth_user_id) {
      setAuthIntent("convert");
      setAuthOpen(true);
      return;
    }
    runConvertTo3D(auth);
  }, [authUser, runConvertTo3D]);

  const handleSignIn = useCallback(() => {
    setAuthIntent("signin");
    setAuthOpen(true);
  }, []);

  const handleDownloadImage = useCallback(async () => {
    const imageUrl = generationResult?.generated_image?.image_url;
    if (!imageUrl) return;

    try {
      const response = await fetch(imageUrl);
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "booth-concept.jpg";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch {
      window.open(imageUrl, "_blank", "noopener,noreferrer");
    }
  }, [generationResult]);

  const handleExportModel = useCallback(async () => {
    const modelUrl = modelJob?.model_url;
    if (!modelUrl) return;

    const resolvedUrl = modelUrl.startsWith("http")
      ? modelUrl
      : `${window.location.origin}${modelUrl.startsWith("/") ? "" : "/"}${modelUrl}`;

    try {
      const response = await fetch(resolvedUrl);
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "booth-model.glb";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch {
      window.open(resolvedUrl, "_blank", "noopener,noreferrer");
    }
  }, [modelJob]);

  const handleSignOut = useCallback(async () => {
    clearStoredAuth();
    setAuthUser(null);
    setHistoryLocked(true);
    setSessions([]);
    setModelJob(null);
    try {
      const supabase = await getSupabaseClient();
      await supabase.auth.signOut();
    } catch {
      // ignore
    }
  }, []);

  // Complete Google OAuth after redirect back from Google / Supabase.
  useEffect(() => {
    const hasOAuthReturn =
      window.location.search.includes("code=") ||
      window.location.hash.includes("access_token");
    const pendingSessionId = getPendingAuthSession();
    if (!hasOAuthReturn && !pendingSessionId) return undefined;

    let cancelled = false;

    async function finishGoogleAuth() {
      try {
        const supabase = await getSupabaseClient();
        // Give supabase-js a moment to exchange the OAuth code if present.
        if (hasOAuthReturn) {
          await new Promise((r) => setTimeout(r, 300));
        }

        const { data } = await supabase.auth.getSession();
        const session = data?.session;
        if (!session?.access_token || cancelled) return;

        const claimSessionId =
          pendingSessionId || sessionId || routeSessionId || undefined;
        const result = await completeOAuth({
          access_token: session.access_token,
          session_id: claimSessionId,
        });

        if (cancelled) return;

        const auth = {
          auth_user_id: result.auth?.auth_user_id,
          access_token: result.auth?.access_token || session.access_token,
          email: result.auth?.email || session.user?.email,
          name: result.auth?.name || null,
        };
        setStoredAuth(auth);
        setAuthUser(auth);
        setAuthOpen(false);
        setHistoryLocked(false);
        await refreshSessions();

        // Clean OAuth params from the URL without a full reload.
        if (hasOAuthReturn) {
          const clean = claimSessionId
            ? `/chat/${claimSessionId}`
            : "/chat";
          window.history.replaceState({}, "", clean);
        }

        const shouldConvert = consumePendingConvert();
        if (shouldConvert) {
          setTimeout(() => {
            if (!cancelled) runConvertTo3D(auth);
          }, 500);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              err.message ||
              "Google sign-in failed."
          );
        }
      }
    }

    finishGoogleAuth();
    return () => {
      cancelled = true;
    };
  }, [routeSessionId, sessionId, runConvertTo3D, refreshSessions]);

  const submitMessage = useCallback(
    async (rawText) => {
      const userText = (rawText || "").trim();
      if (!userText || loading) return;

      let activeId = sessionId;
      const signedIn = Boolean(
        (authUser || getStoredAuth())?.auth_user_id
      );

      if (!activeId) {
        try {
          const data = await createSession();
          activeId = data.session.id;
          setSessionId(activeId);
          navigate(`/chat/${activeId}`, { replace: true });
          if (signedIn && data.session) {
            setSessions((prev) => [data.session, ...prev]);
            setHistoryLocked(false);
          }
          if (data.quota) setQuota(data.quota);
        } catch (err) {
          setError(err.response?.data?.detail || "Failed to create session.");
          return;
        }
      }

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
        if (data.quota) setQuota(data.quota);

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
    [loading, sessionId, navigate, closeSidebar, authUser]
  );

  const handleSend = useCallback(
    async (event) => {
      event.preventDefault();
      await submitMessage(input);
    },
    [input, submitMessage]
  );

  const fillComposer = useCallback((text) => {
    setInput(text);
    requestAnimationFrame(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      textarea.focus();
      const end = text.length;
      textarea.setSelectionRange(end, end);
    });
  }, []);

  const handleQuickReply = useCallback(
    (label) => {
      fillComposer(label);
    },
    [fillComposer]
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
  const firstName =
    authUser?.name?.split?.(" ")?.[0] ||
    authUser?.email?.split?.("@")?.[0] ||
    null;
  const quickReplies = useMemo(
    () => (showWelcome ? [] : getQuickReplies(requirements)),
    [showWelcome, requirements]
  );
  const quotaUnlimited = Boolean(quota?.unlimited) || quota?.max >= 999;
  // Always hide history when signed out — do not rely on API alone.
  const historyHidden = !authUser?.auth_user_id || historyLocked;

  return (
    <div
      className={`app-shell studio-layout${sidebarOpen ? " sidebar-open" : ""}${
        detailsOpen ? " details-open" : ""
      }`}
    >
      <SessionSidebar
        sessions={historyHidden ? [] : sessions}
        activeSessionId={sessionId}
        loading={sessionsLoading}
        historyLocked={historyHidden}
        theme={theme}
        onToggleTheme={toggleTheme}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        onSignIn={handleSignIn}
      />

      <div className="studio-main">
        <header className="chat-topbar studio-topbar">
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
            <h1>{activeSession?.title || "Booth studio"}</h1>
            <p>
              {firstName
                ? quotaUnlimited
                  ? `Hi ${firstName}`
                  : `Hi ${firstName} · ${quota.remaining} of ${quota.max} free generations left`
                : quotaUnlimited
                  ? "Chat freely · image generation unlocked"
                  : `${quota.remaining} of ${quota.max} free generations remaining`}
            </p>
          </div>

          <div className="topbar-actions">
            {authUser?.email ? (
              <button
                type="button"
                className="topbar-auth-btn pressable"
                onClick={handleSignOut}
              >
                Sign out
              </button>
            ) : (
              <button
                type="button"
                className="topbar-auth-btn primary pressable"
                onClick={handleSignIn}
              >
                Sign in
              </button>
            )}
            <button
              type="button"
              className={`details-toggle pressable${detailsOpen ? " active" : ""}`}
              onClick={toggleDetails}
              aria-expanded={detailsOpen}
            >
              Details
            </button>
          </div>
        </header>

        <div className="studio-split">
          <div className="chat-shell studio-chat">
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
                  <div className="welcome-screen compact">
                    <h2>
                      {firstName
                        ? `${firstName}, design your exhibition booth`
                        : "Design your exhibition booth"}
                    </h2>
                    <p>
                      Tell me about your event — I&apos;ll collect the brief on the
                      left while your booth takes shape on the right.
                    </p>
                    <div className="welcome-suggestions">
                      {[
                        "Design a 6x6 fashion booth",
                        "Design a corner booth for a tech brand",
                        "Design a big open booth with two floors",
                        "Design a booth for a car brand",
                        "Design a small booth for a food stand",
                        "Design a fancy jewelry booth",
                        "Design a booth for a government brand",
                      ].map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          className="suggestion-chip pressable"
                          onClick={() => fillComposer(suggestion)}
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
                  bottomRef={bottomRef}
                />
              </div>
            </main>

            {error && (
              <div className="chat-error-banner">
                <p>{error}</p>
                {(String(error).toLowerCase().includes("limit") ||
                  (quota.remaining <= 0 && !authUser)) && (
                  <button type="button" onClick={handleSignIn}>
                    Sign in with Google
                  </button>
                )}
                {requirementsComplete && sessionId && quota.remaining > 0 && (
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
              {quickReplies.length > 0 && (
                <div className="quick-replies" aria-label="Suggested answers">
                  {quickReplies.map((item) => (
                    <button
                      key={`${item.field}-${item.label}`}
                      type="button"
                      className="quick-reply-chip pressable"
                      disabled={loading}
                      onClick={() => handleQuickReply(item.label)}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              )}
              <form className="composer-form" onSubmit={handleSend}>
                <div className="composer-box">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      firstName
                        ? `Message your booth consultant, ${firstName}...`
                        : "Message Booth AI..."
                    }
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
              </form>
            </footer>
          </div>

          <BoothWorkspace
            requirements={requirements}
            imageUrl={generationImageUrl}
            modelUrl={modelJob?.model_url || null}
            modelStatus={modelJob?.status || null}
            modelError={modelJob?.status === "FAILED" ? modelJob?.error : null}
            loading={loading}
            regenerating={regenerating}
            converting3d={converting3d}
            quotaUnlimited={quotaUnlimited}
            authUser={authUser}
            onSignIn={handleSignIn}
            onSignOut={handleSignOut}
            onConvertTo3D={handleConvertTo3D}
            onRegenerate={handleRegenerate}
            onDownloadImage={handleDownloadImage}
            onExportModel={modelJob?.model_url ? handleExportModel : null}
          />
        </div>
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
        onConvertTo3D={generationImageUrl ? handleConvertTo3D : null}
        converting3d={converting3d}
        onDownloadImage={generationImageUrl ? handleDownloadImage : null}
        quota={quota}
      />

      <AuthModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        sessionId={sessionId}
        intent={authIntent}
      />
    </div>
  );
}
