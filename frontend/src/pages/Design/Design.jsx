import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  createDesignSession,
  generateDesign,
  getDesignSession,
  getQuestions,
  regenerateDesign,
  saveAnswers,
  submitLead,
} from "../../services/designService";
import { useTheme } from "../../hooks/useTheme";

const STEPS = {
  LANDING: "landing",
  QUESTIONS: "questions",
  REVIEW: "review",
  GENERATING: "generating",
  RESULT: "result",
  LEAD: "lead",
};

function emptyAnswer() {
  return { value: null, other_text: "" };
}

function answerLabel(question, answer) {
  if (!answer || answer.value == null || answer.value === "") return "—";

  if (question.type === "multi") {
    const values = Array.isArray(answer.value) ? answer.value : [answer.value];
    const labels = values
      .filter((id) => id !== "other")
      .map((id) => question.options.find((o) => o.id === id)?.label || id);
    if (values.includes("other") && answer.other_text) {
      labels.push(answer.other_text);
    }
    return labels.length ? labels.join(", ") : "—";
  }

  if (answer.value === "other") {
    return answer.other_text || "Other";
  }

  return question.options.find((o) => o.id === answer.value)?.label || answer.value;
}

function isAnswerComplete(question, answer, otherMax) {
  if (!answer || answer.value == null || answer.value === "") {
    return !question.required;
  }

  const other = (answer.other_text || "").trim();
  if (other.length > otherMax) return false;

  if (question.type === "multi") {
    const values = Array.isArray(answer.value) ? answer.value : [answer.value];
    const selected = values.filter(Boolean);
    if (selected.includes("other") && !other) return false;

    const count =
      selected.filter((v) => v !== "other").length + (other ? 1 : 0);
    const min = question.min_selections ?? 1;
    const max = question.max_selections ?? 4;
    return count >= min && count <= max;
  }

  if (answer.value === "other") {
    return Boolean(other);
  }

  return true;
}

export default function Design() {
  const { sessionId: routeSessionId } = useParams();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [step, setStep] = useState(STEPS.LANDING);
  const [questions, setQuestions] = useState([]);
  const [otherMax, setOtherMax] = useState(60);
  const [maxRegen, setMaxRegen] = useState(3);
  const [sessionId, setSessionId] = useState(null);
  const [answers, setAnswers] = useState({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [imageUrl, setImageUrl] = useState(null);
  const [regenCount, setRegenCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lead, setLead] = useState({ name: "", email: "", phone: "" });
  const [leadSaved, setLeadSaved] = useState(false);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        const data = await getQuestions();
        if (cancelled) return;
        setQuestions(data.questions || []);
        setOtherMax(data.other_text_max_length || 60);
        setMaxRegen(data.max_regenerations || 3);

        if (routeSessionId) {
          const sessionData = await getDesignSession(routeSessionId);
          if (cancelled) return;
          const session = sessionData.session;
          setSessionId(session.id);
          setAnswers(session.answers || {});
          setImageUrl(session.image_url || null);
          setRegenCount(session.regenerate_count || 0);
          if (session.contact) {
            setLead({
              name: session.contact.name || "",
              email: session.contact.email || "",
              phone: session.contact.phone || "",
            });
            setLeadSaved(true);
          } else {
            setLeadSaved(false);
          }

          // Existing session URL should never bounce back to the landing CTA.
          if (session.image_url) {
            setStep(STEPS.RESULT);
          } else {
            setQuestionIndex(0);
            setStep(STEPS.QUESTIONS);
          }
        } else {
          setSessionId(null);
          setAnswers({});
          setImageUrl(null);
          setRegenCount(0);
          setLeadSaved(false);
          setQuestionIndex(0);
          setStep(STEPS.LANDING);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "Failed to load questionnaire. Is the backend running?"
          );
        }
      } finally {
        if (!cancelled) setBooting(false);
      }
    }

    boot();
    return () => {
      cancelled = true;
    };
  }, [routeSessionId]);

  const currentQuestion = questions[questionIndex];
  const progress = questions.length
    ? Math.round(((questionIndex + 1) / questions.length) * 100)
    : 0;

  const currentAnswer = useMemo(() => {
    if (!currentQuestion) return emptyAnswer();
    return answers[currentQuestion.id] || emptyAnswer();
  }, [answers, currentQuestion]);

  const canContinue = currentQuestion
    ? isAnswerComplete(currentQuestion, currentAnswer, otherMax)
    : false;

  const allComplete = questions.every((q) =>
    isAnswerComplete(q, answers[q.id] || emptyAnswer(), otherMax)
  );

  async function ensureSession() {
    if (sessionId) return sessionId;
    const data = await createDesignSession();
    const id = data.session.id;
    setSessionId(id);
    navigate(`/design/${id}`, { replace: true });
    return id;
  }

  async function persistAnswers(nextAnswers) {
    const id = await ensureSession();
    await saveAnswers(id, nextAnswers);
    return id;
  }

  function updateAnswer(question, patch) {
    setAnswers((prev) => {
      const existing = prev[question.id] || emptyAnswer();
      return {
        ...prev,
        [question.id]: { ...existing, ...patch },
      };
    });
    setError("");
  }

  function selectSingle(question, optionId) {
    updateAnswer(question, {
      value: optionId,
      other_text: optionId === "other" ? currentAnswer.other_text || "" : "",
    });
  }

  function toggleMulti(question, optionId) {
    const existing = Array.isArray(currentAnswer.value)
      ? [...currentAnswer.value]
      : currentAnswer.value
        ? [currentAnswer.value]
        : [];

    let next;
    if (existing.includes(optionId)) {
      next = existing.filter((id) => id !== optionId);
    } else {
      next = [...existing, optionId];
      const max = question.max_selections ?? 4;
      const count =
        next.filter((id) => id !== "other").length +
        (next.includes("other") ? 1 : 0);
      if (count > max) {
        setError(`Select up to ${max} features.`);
        return;
      }
    }

    updateAnswer(question, {
      value: next,
      other_text: next.includes("other") ? currentAnswer.other_text || "" : "",
    });
  }

  async function handleStart() {
    setError("");
    setLoading(true);
    try {
      // Move to questions immediately so the CTA never feels like a no-op.
      setQuestionIndex(0);
      setStep(STEPS.QUESTIONS);
      await ensureSession();
    } catch (err) {
      setStep(STEPS.LANDING);
      setError(
        err.response?.data?.detail ||
          "Failed to start. Run migration 007_booth_designs.sql in Supabase."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleNext() {
    if (!canContinue || !currentQuestion) return;
    setLoading(true);
    setError("");
    try {
      await persistAnswers({
        [currentQuestion.id]: answers[currentQuestion.id],
      });
      if (questionIndex >= questions.length - 1) {
        setStep(STEPS.REVIEW);
      } else {
        setQuestionIndex((i) => i + 1);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save answer.");
    } finally {
      setLoading(false);
    }
  }

  function handleBack() {
    setError("");
    if (step === STEPS.REVIEW) {
      setStep(STEPS.QUESTIONS);
      setQuestionIndex(questions.length - 1);
      return;
    }
    if (questionIndex > 0) {
      setQuestionIndex((i) => i - 1);
    } else {
      setStep(STEPS.LANDING);
    }
  }

  async function handleGenerate() {
    if (!allComplete) {
      setError("Please complete all required questions first.");
      return;
    }

    setError("");
    setStep(STEPS.GENERATING);
    setLoading(true);

    try {
      const id = await persistAnswers(answers);
      const result = await generateDesign(id);
      setImageUrl(result.image_url);
      setRegenCount(result.session?.regenerate_count || 0);
      setStep(STEPS.RESULT);
    } catch (err) {
      setError(err.response?.data?.detail || "Image generation failed.");
      setStep(STEPS.REVIEW);
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    if (!sessionId || loading) return;
    if (regenCount >= maxRegen) {
      setError(`Regeneration limit reached (${maxRegen}).`);
      return;
    }

    setError("");
    setLoading(true);
    setStep(STEPS.GENERATING);

    try {
      const result = await regenerateDesign(sessionId);
      setImageUrl(result.image_url);
      setRegenCount(result.regenerate_count || regenCount + 1);
      setStep(STEPS.RESULT);
    } catch (err) {
      setError(err.response?.data?.detail || "Regeneration failed.");
      setStep(STEPS.RESULT);
    } finally {
      setLoading(false);
    }
  }

  async function handleLeadSubmit(event) {
    event.preventDefault();
    if (!sessionId) return;
    setLoading(true);
    setError("");
    try {
      await submitLead(sessionId, lead);
      setLeadSaved(true);
      setStep(STEPS.RESULT);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save contact details.");
    } finally {
      setLoading(false);
    }
  }

  function editQuestion(index) {
    setQuestionIndex(index);
    setStep(STEPS.QUESTIONS);
  }

  if (booting) {
    return (
      <div className="design-shell">
        <div className="design-loading-card">
          <div className="typing-indicator">
            <span />
            <span />
            <span />
          </div>
          <p>Loading booth designer...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="design-shell">
      <header className="design-topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">Booth AI</span>
        </div>
        <div className="design-topbar-actions">
          <button
            type="button"
            className="theme-toggle pressable"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <main className="design-main">
        {step === STEPS.LANDING && (
          <section className="design-hero reveal-on-scroll is-visible">
            <p className="design-eyebrow">AI Booth Designer</p>
            <h1>Design your exhibition booth in minutes</h1>
            <p className="design-hero-copy">
              Answer a short set of guided questions. We turn your choices into a
              photorealistic booth concept — no chat required.
            </p>
            <button
              type="button"
              className="design-primary-btn pressable"
              onClick={handleStart}
              disabled={loading}
            >
              Design Your Booth
            </button>
          </section>
        )}

        {step === STEPS.QUESTIONS && currentQuestion && (
          <section className="design-question-stage">
            <div className="design-progress">
              <div className="design-progress-meta">
                <span>
                  Question {questionIndex + 1} of {questions.length}
                </span>
                <span>{progress}%</span>
              </div>
              <div className="design-progress-track">
                <div
                  className="design-progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            <div className="design-question-card">
              <h2>{currentQuestion.prompt}</h2>
              {currentQuestion.type === "multi" && (
                <p className="design-hint">
                  Select {currentQuestion.min_selections ?? 1}–
                  {currentQuestion.max_selections ?? 4} options
                </p>
              )}

              <div className="option-grid">
                {currentQuestion.options.map((option) => {
                  const selected =
                    currentQuestion.type === "multi"
                      ? Array.isArray(currentAnswer.value) &&
                        currentAnswer.value.includes(option.id)
                      : currentAnswer.value === option.id;

                  return (
                    <button
                      key={option.id}
                      type="button"
                      className={`option-card pressable${selected ? " selected" : ""}`}
                      onClick={() =>
                        currentQuestion.type === "multi"
                          ? toggleMulti(currentQuestion, option.id)
                          : selectSingle(currentQuestion, option.id)
                      }
                    >
                      <span className="option-card-label">{option.label}</span>
                    </button>
                  );
                })}
              </div>

              {((currentQuestion.type === "single" &&
                currentAnswer.value === "other") ||
                (currentQuestion.type === "multi" &&
                  Array.isArray(currentAnswer.value) &&
                  currentAnswer.value.includes("other"))) && (
                <div className="other-input-wrap">
                  <label htmlFor="other-text">Tell us more</label>
                  <input
                    id="other-text"
                    type="text"
                    maxLength={otherMax}
                    value={currentAnswer.other_text || ""}
                    onChange={(e) =>
                      updateAnswer(currentQuestion, {
                        other_text: e.target.value,
                      })
                    }
                    placeholder="Type your answer..."
                    autoFocus
                  />
                  <span className="other-count">
                    {(currentAnswer.other_text || "").length}/{otherMax}
                  </span>
                </div>
              )}

              <div className="design-nav-row">
                <button
                  type="button"
                  className="design-secondary-btn pressable"
                  onClick={handleBack}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="design-primary-btn pressable"
                  onClick={handleNext}
                  disabled={!canContinue || loading}
                >
                  {questionIndex >= questions.length - 1 ? "Review" : "Continue"}
                </button>
              </div>
            </div>
          </section>
        )}

        {step === STEPS.REVIEW && (
          <section className="design-review">
            <h2>Review your booth brief</h2>
            <p className="design-hero-copy">
              Confirm your answers before we generate the concept.
            </p>
            <ul className="review-list">
              {questions.map((question, index) => (
                <li key={question.id} className="review-item">
                  <div>
                    <span className="review-label">{question.prompt}</span>
                    <strong>{answerLabel(question, answers[question.id])}</strong>
                  </div>
                  <button
                    type="button"
                    className="review-edit"
                    onClick={() => editQuestion(index)}
                  >
                    Edit
                  </button>
                </li>
              ))}
            </ul>
            <div className="design-nav-row">
              <button
                type="button"
                className="design-secondary-btn pressable"
                onClick={handleBack}
              >
                Back
              </button>
              <button
                type="button"
                className="design-primary-btn pressable"
                onClick={handleGenerate}
                disabled={!allComplete || loading}
              >
                Generate Booth Concept
              </button>
            </div>
          </section>
        )}

        {step === STEPS.GENERATING && (
          <section className="design-loading-card">
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
            <h2>Creating your booth concept</h2>
            <p>This usually takes under a minute.</p>
          </section>
        )}

        {step === STEPS.RESULT && (
          <section className="design-result">
            <div className="result-copy">
              <p className="design-eyebrow">Your concept</p>
              <h2>Booth visualization ready</h2>
              <p className="design-hero-copy">
                Regenerations used: {regenCount}/{maxRegen}
              </p>
            </div>

            {imageUrl && (
              <div className="result-image-wrap">
                <img src={imageUrl} alt="Generated booth concept" />
              </div>
            )}

            <div className="result-actions">
              <button
                type="button"
                className="design-secondary-btn pressable"
                onClick={handleRegenerate}
                disabled={loading || regenCount >= maxRegen}
              >
                Regenerate
              </button>
              {imageUrl && (
                <a
                  className="design-secondary-btn pressable"
                  href={imageUrl}
                  download="booth-concept.jpg"
                  target="_blank"
                  rel="noreferrer"
                >
                  Download
                </a>
              )}
              <button
                type="button"
                className="design-primary-btn pressable"
                onClick={() => setStep(STEPS.LEAD)}
              >
                {leadSaved ? "Update Quote Details" : "Get a Quote for This Design"}
              </button>
            </div>

            <button
              type="button"
              className="text-link"
              onClick={() => {
                setStep(STEPS.LANDING);
                setAnswers({});
                setImageUrl(null);
                setSessionId(null);
                setLeadSaved(false);
                navigate("/design");
              }}
            >
              Start a new design
            </button>
          </section>
        )}

        {step === STEPS.LEAD && (
          <section className="design-lead">
            <h2>Get a quote for this design</h2>
            <p className="design-hero-copy">
              Leave your details and our team will follow up with pricing and next
              steps.
            </p>
            <form className="lead-form" onSubmit={handleLeadSubmit}>
              <label>
                Name
                <input
                  required
                  value={lead.name}
                  onChange={(e) => setLead((p) => ({ ...p, name: e.target.value }))}
                />
              </label>
              <label>
                Email
                <input
                  required
                  type="email"
                  value={lead.email}
                  onChange={(e) =>
                    setLead((p) => ({ ...p, email: e.target.value }))
                  }
                />
              </label>
              <label>
                Phone
                <input
                  value={lead.phone}
                  onChange={(e) =>
                    setLead((p) => ({ ...p, phone: e.target.value }))
                  }
                />
              </label>
              <div className="design-nav-row">
                <button
                  type="button"
                  className="design-secondary-btn pressable"
                  onClick={() => setStep(STEPS.RESULT)}
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="design-primary-btn pressable"
                  disabled={loading}
                >
                  Submit
                </button>
              </div>
            </form>
          </section>
        )}

        {error && <p className="design-error">{error}</p>}
      </main>
    </div>
  );
}
