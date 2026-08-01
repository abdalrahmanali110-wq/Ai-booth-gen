import { useEffect, useState } from "react";
import {
  FIELD_LABELS,
  FIELD_ORDER,
  FIELD_QUESTIONS,
} from "../utils/intake";

function toEditableValue(key, value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function fromEditableValue(key, raw) {
  const text = (raw || "").trim();
  if (!text) return null;
  if (key === "special_requirements") {
    if (/^none$/i.test(text)) return [];
    return text.split(",").map((part) => part.trim()).filter(Boolean);
  }
  if (key === "budget") {
    const digits = text.replace(/[^\d.]/g, "");
    const num = Number(digits);
    if (Number.isFinite(num) && digits) return num;
  }
  return text;
}

const FADE_MS = 280;

export default function SummaryConfirmPopup({
  open,
  requirements = {},
  generating = false,
  saving = false,
  onGenerate,
  onDismiss,
}) {
  const [draft, setDraft] = useState({});
  const [mounted, setMounted] = useState(open);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    if (open) {
      setMounted(true);
      setExiting(false);
      return undefined;
    }
    if (!mounted) return undefined;
    setExiting(true);
    const timer = setTimeout(() => {
      setMounted(false);
      setExiting(false);
    }, FADE_MS);
    return () => clearTimeout(timer);
  }, [open, mounted]);

  useEffect(() => {
    if (!open) return;
    const next = {};
    FIELD_ORDER.forEach((field) => {
      next[field] = toEditableValue(field, requirements[field]);
    });
    setDraft(next);
  }, [open, requirements]);

  if (!mounted) return null;

  const busy = generating || saving;

  function handleGenerate(event) {
    event.preventDefault();
    if (busy) return;
    const payload = {};
    FIELD_ORDER.forEach((field) => {
      payload[field] = fromEditableValue(field, draft[field]);
    });
    onGenerate(payload);
  }

  return (
    <div
      className={`question-popup-backdrop${exiting ? " is-exiting" : ""}`}
      role="presentation"
    >
      <div
        className={`question-popup summary-confirm-popup${
          exiting ? " is-exiting" : ""
        }`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="summary-confirm-title"
      >
        <header className="question-popup-header">
          <p className="question-popup-kicker">Project summary</p>
          <button
            type="button"
            className="icon-btn"
            onClick={onDismiss}
            aria-label="Close summary"
            disabled={busy}
          >
            ×
          </button>
        </header>

        <h3 id="summary-confirm-title">Review your booth brief</h3>
        <p className="summary-confirm-copy">
          Edit any answer below, then start generating your booth concept.
        </p>

        <form className="summary-confirm-form" onSubmit={handleGenerate}>
          <div className="summary-confirm-list">
            {FIELD_ORDER.map((field) => (
              <label key={field} className="project-brief-qa-row">
                <span className="project-brief-qa-question">
                  {FIELD_QUESTIONS[field] || FIELD_LABELS[field]}
                </span>
                <input
                  type="text"
                  value={draft[field] || ""}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, [field]: e.target.value }))
                  }
                  placeholder="Not set"
                  disabled={busy}
                />
              </label>
            ))}
          </div>

          <div className="summary-confirm-actions">
            <button
              type="button"
              className="workspace-secondary-btn pressable"
              onClick={onDismiss}
              disabled={busy}
            >
              Keep chatting
            </button>
            <button
              type="submit"
              className="workspace-primary-btn pressable summary-generate-btn"
              disabled={busy}
            >
              Generate concept
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
