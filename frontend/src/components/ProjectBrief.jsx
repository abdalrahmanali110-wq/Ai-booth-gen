import { useEffect, useMemo, useState } from "react";
import {
  FIELD_LABELS,
  FIELD_ORDER,
  FIELD_QUESTIONS,
  formatRequirementValue,
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

export default function ProjectBrief({
  requirements = {},
  onSave,
  saving = false,
}) {
  const filledEntries = useMemo(
    () =>
      FIELD_ORDER.map((field) => ({
        field,
        question: FIELD_QUESTIONS[field] || FIELD_LABELS[field],
        label: FIELD_LABELS[field] || field,
        value: formatRequirementValue(field, requirements[field]),
        raw: requirements[field],
      })).filter((row) => row.value),
    [requirements]
  );

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({});

  useEffect(() => {
    if (!editing) return;
    const next = {};
    FIELD_ORDER.forEach((field) => {
      next[field] = toEditableValue(field, requirements[field]);
    });
    setDraft(next);
  }, [editing, requirements]);

  async function handleSave() {
    if (!onSave) {
      setEditing(false);
      return;
    }
    const payload = {};
    FIELD_ORDER.forEach((field) => {
      payload[field] = fromEditableValue(field, draft[field]);
    });
    await onSave(payload);
    setEditing(false);
  }

  if (!filledEntries.length && !editing) {
    return null;
  }

  return (
    <section className="project-brief" aria-label="Project summary">
      <header className="project-brief-header">
        <div>
          <h3>Project summary</h3>
          <p>Questions and answers collected so far — edit anytime.</p>
        </div>
        {onSave && (
          <button
            type="button"
            className="project-brief-edit pressable"
            onClick={() => (editing ? handleSave() : setEditing(true))}
            disabled={saving}
          >
            {editing ? (saving ? "Saving..." : "Save changes") : "Customize answers"}
          </button>
        )}
      </header>

      {editing ? (
        <div className="project-brief-qa editing">
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
                placeholder="Not set yet"
              />
            </label>
          ))}
          <div className="project-brief-edit-actions">
            <button
              type="button"
              className="workspace-secondary-btn pressable"
              onClick={() => setEditing(false)}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="workspace-primary-btn pressable"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save answers"}
            </button>
          </div>
        </div>
      ) : (
        <ul className="project-brief-qa">
          {filledEntries.map((row) => (
            <li key={row.field} className="project-brief-qa-row">
              <span className="project-brief-qa-question">{row.question}</span>
              <strong className="project-brief-qa-answer">{row.value}</strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
