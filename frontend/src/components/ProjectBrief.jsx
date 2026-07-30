function formatBudget(value) {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(num)) return `${num.toLocaleString()} AED`;
  return String(value);
}

function budgetTier(value) {
  const num = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(num)) return "Custom";
  if (num < 40000) return "Essential Tier";
  if (num < 90000) return "Standard Tier";
  if (num < 180000) return "Premium Tier";
  return "Bespoke Tier";
}

function layoutFromSides(openSides) {
  const text = String(openSides || "").toLowerCase();
  if (text.includes("all") || text.includes("4")) return "Island";
  if (text.includes("3")) return "Peninsula";
  if (text.includes("2") || text.includes("corner")) return "Corner";
  if (text.includes("1")) return "Inline";
  return openSides || "—";
}

function pillsFromRequirements(requirements) {
  const pills = [];
  if (requirements.theme) pills.push(String(requirements.theme));
  if (requirements.brand_colors) pills.push(String(requirements.brand_colors));
  const features = requirements.special_requirements;
  if (Array.isArray(features)) {
    features.slice(0, 4).forEach((item) => {
      if (item) pills.push(String(item));
    });
  }
  return pills;
}

export default function ProjectBrief({ requirements = {}, onEdit }) {
  const size = requirements.booth_size || "—";
  const brand = requirements.brand_name || "Your brand";
  const industry = requirements.industry || "—";
  const eventName = requirements.event_name || "—";
  const location = requirements.location || "—";
  const pills = pillsFromRequirements(requirements);

  return (
    <section className="project-brief" aria-label="Project brief">
      <header className="project-brief-header">
        <div>
          <h3>Project Brief</h3>
          <p>Review the booth parameters before we generate the design.</p>
        </div>
        {onEdit && (
          <button type="button" className="project-brief-edit pressable" onClick={onEdit}>
            Edit requirements
          </button>
        )}
      </header>

      <div className="project-brief-card">
        <div className="project-brief-row">
          <div className="project-brief-cell">
            <span className="project-brief-label">Brand</span>
            <strong>{brand}</strong>
            <span className="project-brief-sub">{industry}</span>
          </div>
          <div className="project-brief-divider" aria-hidden="true" />
          <div className="project-brief-cell">
            <span className="project-brief-label">Event</span>
            <strong>{eventName}</strong>
            <span className="project-brief-sub">{location}</span>
          </div>
        </div>

        <div className="project-brief-row">
          <div className="project-brief-cell">
            <span className="project-brief-label">Dimensions</span>
            <strong>{size}m</strong>
            <span className="project-brief-sub">
              Open sides: {requirements.open_sides || "—"}
            </span>
          </div>
          <div className="project-brief-divider" aria-hidden="true" />
          <div className="project-brief-cell">
            <span className="project-brief-label">Layout type</span>
            <strong>{layoutFromSides(requirements.open_sides)}</strong>
            <span className="project-brief-sub">Exhibition hall</span>
          </div>
        </div>

        <div className="project-brief-row">
          <div className="project-brief-cell">
            <span className="project-brief-label">Est. budget</span>
            <strong className="project-brief-budget">
              {formatBudget(requirements.budget)}
            </strong>
            <span className="project-brief-sub">{budgetTier(requirements.budget)}</span>
          </div>
        </div>

        <div className="project-brief-aesthetic">
          <span className="project-brief-label">Aesthetic direction</span>
          <div className="project-brief-pills">
            {pills.length ? (
              pills.map((pill) => (
                <span key={pill} className="project-brief-pill">
                  {pill}
                </span>
              ))
            ) : (
              <span className="project-brief-sub">Add style and features in chat</span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
