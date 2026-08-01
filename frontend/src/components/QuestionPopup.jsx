import { useEffect, useState } from "react";

export default function QuestionPopup({
  open,
  question,
  loading,
  onAnswer,
  onDismiss,
}) {
  const [custom, setCustom] = useState("");

  useEffect(() => {
    setCustom("");
  }, [question?.field]);

  if (!open || !question) return null;

  function submitCustom(event) {
    event.preventDefault();
    const value = custom.trim();
    if (!value || loading) return;
    onAnswer(value);
    setCustom("");
  }

  return (
    <div className="question-popup-backdrop" role="presentation">
      <div
        className="question-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="question-popup-title"
      >
        <header className="question-popup-header">
          <p className="question-popup-kicker">Consultant question</p>
          <button
            type="button"
            className="icon-btn"
            onClick={onDismiss}
            aria-label="Dismiss question"
          >
            ×
          </button>
        </header>
        <h3 id="question-popup-title">{question.ask}</h3>

        {question.options?.length > 0 && (
          <div className="question-popup-options" aria-label="Suggested answers">
            {question.options.map((option) => (
              <button
                key={option}
                type="button"
                className="question-popup-chip pressable"
                disabled={loading}
                onClick={() => onAnswer(option)}
              >
                {option}
              </button>
            ))}
          </div>
        )}

        <form className="question-popup-form" onSubmit={submitCustom}>
          <input
            type="text"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="Or type your own answer..."
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            className="question-popup-send pressable"
            disabled={!custom.trim() || loading}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
