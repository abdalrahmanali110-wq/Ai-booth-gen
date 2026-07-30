import { memo } from "react";

const Message = memo(function Message({ role, message }) {
  return (
    <div className={`message ${role}`}>
      <div className="message-avatar" aria-hidden="true">
        {role === "user" ? "Y" : "AI"}
      </div>
      <div className="message-content">
        <p>{message}</p>
      </div>
    </div>
  );
});

export default memo(function MessageList({
  messages,
  loading,
  requirementsComplete,
  bottomRef,
}) {
  return (
    <>
      {messages.map((msg) => (
        <Message key={msg.id} role={msg.role} message={msg.message} />
      ))}

      {loading && (
        <div className="message assistant message-loading">
          <div className="message-avatar" aria-hidden="true">
            AI
          </div>
          <div className="message-content">
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
            <p className="loading-label">
              {requirementsComplete
                ? "Generating your booth concept..."
                : "Thinking"}
            </p>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </>
  );
});
