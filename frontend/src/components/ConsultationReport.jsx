function CompanyList({ companies, emptyMessage }) {
  if (!companies?.length) {
    return emptyMessage ? <p className="consultation-company-note">{emptyMessage}</p> : null;
  }

  return (
    <ul className="consultation-company-list">
      {companies.map((company) => (
        <li key={`${company.name}-${company.url}`}>
          <div className="consultation-company-name">
            {company.url ? (
              <a href={company.url} target="_blank" rel="noopener noreferrer">
                {company.name}
              </a>
            ) : (
              company.name
            )}
            {company.estimated_range && (
              <span className="consultation-company-range">
                {company.estimated_range}
              </span>
            )}
          </div>
          {company.why_recommended && (
            <p className="consultation-company-why">{company.why_recommended}</p>
          )}
          {company.url && (
            <a
              className="consultation-company-link"
              href={company.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {company.url.replace(/^https?:\/\/(www\.)?/, "")}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function ConsultationReport({ report }) {
  if (!report) return null;

  const analysis = report.budget_analysis;
  const webCompanies = report.web_companies || [];
  const stretchCompanies = report.stretch_companies || [];

  return (
    <div className="consultation-report">
      {analysis && (
        <div
          className={`consultation-budget-box${
            analysis.fits_budget === false ? " consultation-budget-box--warn" : ""
          }`}
        >
          <h4>Budget fit</h4>
          <p>{analysis.summary}</p>
          {analysis.user_budget > 0 && (
            <dl className="consultation-budget-stats">
              <div>
                <dt>Your budget</dt>
                <dd>AED {analysis.user_budget.toLocaleString()}</dd>
              </div>
              <div>
                <dt>Realistic build range</dt>
                <dd>
                  AED {analysis.market_range_low.toLocaleString()} –{" "}
                  {analysis.market_range_high.toLocaleString()}
                </dd>
              </div>
            </dl>
          )}
        </div>
      )}

      <p className="consultation-intro">{report.intro}</p>

      <ul className="consultation-features">
        {report.features?.map((feature) => (
          <li key={feature}>{feature}</li>
        ))}
      </ul>

      <p className="consultation-size-note">{report.size_note}</p>

      <h4 className="consultation-section-title">Estimated Cost in Dubai/UAE</h4>
      <div className="consultation-table-wrap">
        <table className="consultation-table">
          <thead>
            <tr>
              <th>Booth Size</th>
              <th>Standard Quality</th>
              <th>Premium Quality</th>
              <th>Luxury / High-End</th>
            </tr>
          </thead>
          <tbody>
            {report.cost_table?.map((row) => (
              <tr key={row.size}>
                <td>{row.size}</td>
                <td>{row.standard}</td>
                <td>{row.premium}</td>
                <td>{row.luxury}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="consultation-budget-note">{report.budget_recommendation}</p>

      {report.cost_saving_tips?.length > 0 && (
        <div className="consultation-tips">
          <h4 className="consultation-section-title">Ways to stay within budget</h4>
          <ul>
            {report.cost_saving_tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      <h4 className="consultation-section-title">
        Recommended for your budget ({report.location || "UAE"})
      </h4>
      <p className="consultation-company-note">
        Found via web search — verify pricing directly with each contractor.
      </p>
      <CompanyList
        companies={webCompanies}
        emptyMessage="No web results found. Try regenerating or widening your budget."
      />

      {stretchCompanies.length > 0 && (
        <div className="consultation-company-group">
          <h5>If you can increase budget</h5>
          <CompanyList companies={stretchCompanies} />
        </div>
      )}
    </div>
  );
}
