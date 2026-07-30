import ConsultationReport from "./ConsultationReport";

const REQUIREMENT_LABELS = {
  brand_name: "Brand",
  industry: "Industry",
  slogan: "Slogan",
  event_name: "Event",
  location: "Location",
  event_date: "Event date",
  booth_size: "Booth size",
  open_sides: "Open sides",
  theme: "Design direction",
  brand_colors: "Brand colors",
  budget: "Budget (AED)",
  special_requirements: "Inside the booth",
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
  onConvertTo3D,
  converting3d,
  quota,
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
          {quota && (
            <p className="details-quota">
              {quota.remaining} of {quota.max} free image generations remaining
            </p>
          )}

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
              disabled={regenerating || (quota && quota.remaining <= 0)}
            >
              {regenerating ? "Generating booth image..." : "Regenerate booth image"}
            </button>
            {onConvertTo3D && generationResult?.generated_image?.image_url && (
              <button
                type="button"
                className="convert-3d-btn pressable"
                onClick={(event) => {
                  event.stopPropagation();
                  onConvertTo3D();
                }}
                disabled={converting3d}
              >
                {converting3d ? "Converting to 3D..." : "Convert to 3D"}
              </button>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
