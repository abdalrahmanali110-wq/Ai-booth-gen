import { useEffect, useState } from "react";

export default function InlineQuestionCard({
  question,
  loading,
  onAnswer,
}) {
  const [custom, setCustom] = useState("");

  useEffect(() => {
    setCustom("");
  }, [question?.field]);

  if (!question) return null;

  function submitCustom(event) {
    event.preventDefault();
    const value = custom.trim();
    if (!value || loading) return;
    onAnswer(value);
    setCustom("");
  }

  return (
    <div className="message assistant inline-question-message">
      <div className="message-avatar" aria-hidden="true">
        AI
      </div>
      <div className="message-content">
        <div className="inline-question-card" role="group" aria-label="Booth detail question">
          <p className="inline-question-ask">{question.ask}</p>

          {question.options?.length > 0 && (
            <div className="inline-question-options">
              {question.options.map((option) => (
                <button
                  key={option}
                  type="button"
                  className="inline-question-chip pressable"
                  disabled={loading}
                  onClick={() => onAnswer(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          )}

          <form className="inline-question-form" onSubmit={submitCustom}>
            <input
              type="text"
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              placeholder="Type your answer..."
              disabled={loading}
            />
            <button
              type="submit"
              className="inline-question-send pressable"
              disabled={!custom.trim() || loading}
              aria-label="Send answer"
            >
              →
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
