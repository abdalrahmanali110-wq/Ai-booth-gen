import { memo } from "react";
import ConsultationReport from "./ConsultationReport";
import ModelViewer from "./ModelViewer";

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
  onConvertTo3D,
  converting3d,
  modelUrl,
  modelStatus,
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
                ? "Generating booth image — this may take a minute"
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
            {onConvertTo3D && (
              <div className="convert-3d-row">
                <button
                  type="button"
                  className="convert-3d-btn pressable"
                  onClick={onConvertTo3D}
                  disabled={converting3d || modelStatus === "PROCESSING"}
                >
                  {converting3d || modelStatus === "PROCESSING"
                    ? "Converting to 3D..."
                    : modelUrl
                      ? "Regenerate 3D model"
                      : "Convert to 3D"}
                </button>
                {modelStatus === "FAILED" && (
                  <p className="convert-3d-error">3D conversion failed. Try again.</p>
                )}
              </div>
            )}
            {modelUrl && <ModelViewer modelUrl={modelUrl} />}
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
