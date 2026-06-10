import { memo } from "react";
import ConsultationReport from "./ConsultationReport";

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
  generationImageUrl,
  consultationReport,
  bottomRef,
}) {
  return (
    <>
      {messages.map((msg) => (
        <Message key={msg.id} role={msg.role} message={msg.message} />
      ))}

      {loading && (
        <div className="message assistant message-loading">
          <div className="message-avatar" aria-hidden="true">AI</div>
          <div className="message-content">
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
            <p className="loading-label">
              {requirementsComplete
                ? "Generating booth image and searching UAE contractors — this may take a minute"
                : "Thinking"}
            </p>
          </div>
        </div>
      )}

      {generationImageUrl && (
        <div className="message assistant">
          <div className="message-avatar" aria-hidden="true">AI</div>
          <div className="message-content">
            <div className="inline-image-card">
              <img
                src={generationImageUrl}
                alt="Generated booth concept"
                loading="lazy"
                decoding="async"
              />
            </div>
          </div>
        </div>
      )}

      {consultationReport && (
        <div className="message assistant">
          <div className="message-avatar" aria-hidden="true">AI</div>
          <div className="message-content">
            <ConsultationReport report={consultationReport} />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </>
  );
});
