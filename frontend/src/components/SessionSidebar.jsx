import { memo, useEffect, useRef, useState } from "react";

function formatSessionDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function SessionItem({
  session,
  active,
  onSelect,
  onRename,
  onDelete,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draftTitle, setDraftTitle] = useState(session.title || "");
  const inputRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    setDraftTitle(session.title || "Booth consultation");
  }, [session.title]);

  useEffect(() => {
    if (renaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [renaming]);

  useEffect(() => {
    if (!menuOpen) return;

    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  async function commitRename() {
    const title = draftTitle.trim();
    if (!title) {
      setDraftTitle(session.title || "Booth consultation");
      setRenaming(false);
      return;
    }

    await onRename(session.id, title);
    setRenaming(false);
  }

  function handleRenameKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      commitRename();
    }
    if (event.key === "Escape") {
      setDraftTitle(session.title || "Booth consultation");
      setRenaming(false);
    }
  }

  return (
    <li className={`session-list-item${active ? " active" : ""}`}>
      {renaming ? (
        <input
          ref={inputRef}
          className="session-rename-input"
          value={draftTitle}
          onChange={(e) => setDraftTitle(e.target.value)}
          onBlur={commitRename}
          onKeyDown={handleRenameKeyDown}
        />
      ) : (
        <>
          <button
            type="button"
            className="session-item"
            onClick={() => onSelect(session.id)}
          >
            <span className="session-item-title">
              {session.title || "Booth consultation"}
            </span>
            <span className="session-item-date">
              {formatSessionDate(session.created_at)}
            </span>
          </button>

          <div className="session-actions" ref={menuRef}>
            <button
              type="button"
              className="session-menu-btn"
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen((open) => !open);
              }}
              aria-label="Session options"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="5" r="1.5" fill="currentColor" />
                <circle cx="12" cy="12" r="1.5" fill="currentColor" />
                <circle cx="12" cy="19" r="1.5" fill="currentColor" />
              </svg>
            </button>

            {menuOpen && (
              <div className="session-menu">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    setRenaming(true);
                  }}
                >
                  Rename
                </button>
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    setMenuOpen(false);
                    onDelete(session.id);
                  }}
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </li>
  );
}

function SessionSidebar({
  sessions,
  activeSessionId,
  loading,
  theme,
  onToggleTheme,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
}) {
  return (
    <aside className="session-sidebar">
      <div className="sidebar-top">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">Booth AI</span>
        </div>
        <button type="button" className="new-chat-btn pressable" onClick={onNewChat}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 5v14M5 12h14"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          New chat
        </button>
      </div>

      <div className="session-list-wrap">
        <p className="session-list-label">History</p>
        {loading ? (
          <p className="session-empty">Loading sessions...</p>
        ) : sessions.length === 0 ? (
          <p className="session-empty">No conversations yet</p>
        ) : (
          <ul className="session-list">
            {sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                active={session.id === activeSessionId}
                onSelect={onSelectSession}
                onRename={onRenameSession}
                onDelete={onDeleteSession}
              />
            ))}
          </ul>
        )}
      </div>

      <div className="sidebar-footer">
        <button
          type="button"
          className="theme-toggle pressable"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
              <path
                d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
          <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
        </button>
      </div>
    </aside>
  );
}

export default memo(SessionSidebar);
