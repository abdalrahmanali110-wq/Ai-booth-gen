import ModelViewer from "./ModelViewer";
import ProjectBrief from "./ProjectBrief";
import { isBriefReady } from "../utils/intake";

const BUILD_STEPS = [
  { key: "brand_name", label: "Brand", hint: "Brand name" },
  { key: "industry", label: "Industry", hint: "Industry not set yet" },
  { key: "event_name", label: "Event", hint: "Event name" },
  { key: "location", label: "Location", hint: "City or venue" },
  { key: "booth_size", label: "Size", hint: "Booth footprint" },
  { key: "open_sides", label: "Open sides", hint: "1 / 2 / 3 / all" },
  { key: "theme", label: "Direction", hint: "Design feel" },
  { key: "brand_colors", label: "Colors", hint: "Brand colors" },
  { key: "budget", label: "Budget", hint: "Budget in AED" },
];

function formatStepValue(key, value) {
  if (value === null || value === undefined || value === "") return null;
  if (Array.isArray(value)) return value.length ? value.join(", ") : null;
  if (key === "budget" && typeof value === "number") {
    return `${value.toLocaleString()} AED`;
  }
  return String(value);
}

export default function BoothWorkspace({
  requirements = {},
  imageUrl,
  modelUrl,
  modelStatus,
  modelError,
  loading,
  regenerating,
  converting3d,
  quotaUnlimited,
  authUser,
  onSignIn,
  onSignOut,
  onConvertTo3D,
  onRegenerate,
}) {
  const filled = BUILD_STEPS.filter((step) =>
    formatStepValue(step.key, requirements[step.key])
  );
  const progress = Math.round((filled.length / BUILD_STEPS.length) * 100);
  const busy =
    loading || regenerating || converting3d || modelStatus === "PROCESSING";
  const busyLabel =
    converting3d || modelStatus === "PROCESSING"
      ? "Building your 3D model..."
      : regenerating
        ? "Refining your booth concept..."
        : loading
          ? "Updating your brief..."
          : "";
  const briefReady = isBriefReady(requirements) || Boolean(imageUrl);

  const greetingName =
    authUser?.name?.split?.(" ")?.[0] ||
    authUser?.email?.split?.("@")?.[0] ||
    null;

  const eventName = requirements.event_name;
  const headline = imageUrl
    ? eventName
      ? `Your ${eventName} booth`
      : "Your booth concept"
    : eventName
      ? `Building your ${eventName} booth`
      : greetingName
        ? `${greetingName}, let's build your booth`
        : "Your booth is taking shape";

  return (
    <section className="booth-workspace" aria-label="Booth workspace">
      <header className="workspace-header">
        <div>
          <p className="workspace-kicker">Live build</p>
          <h2>{headline}</h2>
        </div>
        <div className="workspace-auth">
          {authUser?.email ? (
            <>
              <span className="workspace-user" title={authUser.email}>
                {greetingName || authUser.email}
              </span>
              <button
                type="button"
                className="workspace-ghost-btn pressable"
                onClick={onSignOut}
              >
                Sign out
              </button>
            </>
          ) : (
            <button
              type="button"
              className="workspace-signin-btn pressable"
              onClick={onSignIn}
            >
              Sign in
            </button>
          )}
        </div>
      </header>

      <div className="workspace-progress-block">
        <div className="workspace-progress-meta">
          <span>{progress}% brief complete</span>
          <span>
            {quotaUnlimited
              ? "Testing mode · unlimited images"
              : "Free images available"}
          </span>
        </div>
        <div
          className="workspace-progress-track"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={busy ? Math.min(92, Math.max(progress, 18)) : progress}
        >
          <div
            className={`workspace-progress-fill${busy ? " pulsing" : ""}`}
            style={{
              width: `${busy ? Math.min(92, Math.max(progress, 18)) : progress}%`,
            }}
          />
        </div>
        {busy && <p className="workspace-busy-label">{busyLabel}</p>}
      </div>

      {!imageUrl && (
        <div className={`workspace-stage${busy ? " building" : ""}`}>
          <div className="booth-skeleton" aria-hidden="true">
            <div className={`skel-floor${filled.length >= 1 ? " on" : ""}`} />
            <div className={`skel-wall left${filled.length >= 2 ? " on" : ""}`} />
            <div className={`skel-wall right${filled.length >= 3 ? " on" : ""}`} />
            <div className={`skel-counter${filled.length >= 4 ? " on" : ""}`} />
            <div className={`skel-screen${filled.length >= 5 ? " on" : ""}`} />
            <div className={`skel-light${filled.length >= 6 ? " on" : ""}`} />
            {busy && <div className="skel-scan" />}
          </div>
          {filled.length === 0 && !busy && (
            <div className="workspace-empty">
              <p>
                Chat with the consultant — this side builds your booth as you
                answer.
              </p>
            </div>
          )}
        </div>
      )}

      {imageUrl && (
        <figure className="workspace-photo">
          <img src={imageUrl} alt="Generated booth concept" />
          <figcaption>
            <a href={imageUrl} target="_blank" rel="noreferrer">
              Open full image
            </a>
          </figcaption>
        </figure>
      )}

      {imageUrl && (
        <div className="workspace-actions sticky-actions">
          <button
            type="button"
            className="workspace-secondary-btn pressable"
            onClick={onRegenerate}
            disabled={regenerating}
          >
            {regenerating ? "Regenerating..." : "Regenerate image"}
          </button>
          <button
            type="button"
            className="workspace-primary-btn pressable"
            onClick={onConvertTo3D}
            disabled={converting3d || modelStatus === "PROCESSING"}
          >
            {converting3d || modelStatus === "PROCESSING"
              ? "Converting to 3D..."
              : modelUrl
                ? "Rebuild 3D model"
                : authUser?.auth_user_id || quotaUnlimited
                  ? "Generate 3D model"
                  : "Sign in to generate 3D"}
          </button>
        </div>
      )}

      {modelError && (
        <p className="workspace-model-error" role="alert">
          {modelError}
        </p>
      )}

      {modelUrl && (
        <div className="workspace-model-wrap">
          <ModelViewer modelUrl={modelUrl} />
        </div>
      )}

      {briefReady ? (
        <ProjectBrief requirements={requirements} />
      ) : (
        <ul className="workspace-steps">
          {BUILD_STEPS.map((step) => {
            const value = formatStepValue(step.key, requirements[step.key]);
            return (
              <li key={step.key} className={value ? "done" : ""}>
                <span className="step-dot" aria-hidden="true" />
                <div>
                  <strong>{step.label}</strong>
                  <p>{value || step.hint}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
