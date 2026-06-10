import ConsultationReport from "./ConsultationReport";

const REQUIREMENT_LABELS = {
  industry: "Industry",
  event_name: "Event",
  booth_size: "Booth size",
  budget: "Budget (AED)",
  theme: "Theme",
  location: "Location",
  special_requirements: "Special requirements",
};

function formatValue(key, value) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "None";
  }
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (key === "budget" && typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}

export default function RequirementsPanel({
  open,
  onClose,
  requirements,
  generationResult,
  onRegenerate,
  regenerating,
  regenerateError,
}) {
  const hasRequirements = Object.values(requirements || {}).some(
    (value) => value !== null && value !== undefined && value !== ""
  );

  return (
    <>
      <button
        type="button"
        className={`panel-backdrop${open ? " visible" : ""}`}
        onClick={onClose}
        aria-label="Close details"
        tabIndex={open ? 0 : -1}
      />
      <aside
        className={`details-panel${open ? " open" : ""}`}
        aria-hidden={!open}
      >
        <header className="details-panel-header">
          <h2>Project details</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M18 6L6 18M6 6l12 12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </header>

        <div className="details-panel-body">
          {!hasRequirements ? (
            <p className="details-empty">
              Requirements will appear here as you chat with the consultant.
            </p>
          ) : (
            <dl className="details-list">
              {Object.entries(REQUIREMENT_LABELS).map(([key, label]) => (
                <div key={key} className="details-row">
                  <dt>{label}</dt>
                  <dd>{formatValue(key, requirements[key])}</dd>
                </div>
              ))}
            </dl>
          )}

          {generationResult?.generated_image?.image_url && (
            <div className="details-image">
              <h3>Generated booth</h3>
              <img
                src={generationResult.generated_image.image_url}
                alt="Generated booth concept"
                loading="lazy"
                decoding="async"
              />
              {generationResult.budget && (
                <p className="details-budget">
                  Estimated budget:{" "}
                  {generationResult.budget.grand_total?.toLocaleString()} AED
                </p>
              )}
            </div>
          )}

          {generationResult?.consultation_report && (
            <div className="details-consultation">
              <h3>UAE contractor analysis</h3>
              <ConsultationReport report={generationResult.consultation_report} />
            </div>
          )}
        </div>

        {hasRequirements && (
          <div className="details-panel-footer">
            {regenerateError && (
              <p className="details-regenerate-error" role="alert">
                {regenerateError}
              </p>
            )}
            <button
              type="button"
              className="regenerate-btn pressable"
              onClick={(event) => {
                event.stopPropagation();
                onRegenerate();
              }}
              disabled={regenerating}
            >
              {regenerating ? "Generating booth image..." : "Regenerate booth image"}
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
