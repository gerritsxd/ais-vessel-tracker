import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { loadCSV } from "../utils/loadCSV";
import "../styles/MLinsights.css";
import {
  FileText,
  ScanSearch,
  Scale,
  BarChart3
} from "lucide-react";


function interpretSignal(value) {
  if (value > 0.6) return "Strongly positive";
  if (value > 0.2) return "Moderately positive";
  if (value > -0.2) return "Neutral / mixed";
  if (value > -0.6) return "Moderately negative";
  return "Strongly negative";
}

function getSignalColor(value) {
  if (value > 0.6) return "#7dd3fc";
  if (value > 0.2) return "#60a5fa";
  if (value > -0.2) return "#94a3b8";
  if (value > -0.6) return "#f97316";
  return "#ef4444";
}

function getPresenceColor01(v01) {
  const v = Math.max(0, Math.min(1, v01));
  // map 0..1 → -0.2..+1 so 0 stays neutral-ish (grey), not negative/red
  // tweak -0.2 if you want 0 to be perfectly neutral
  const mapped = -0.2 + v * 1.2;
  return getSignalColor(mapped);
}


export default function MLInsights() {
  const [data, setData] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [compareCompany, setCompareCompany] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [viewMode, setViewMode] = useState("list"); // "list" or "grid"
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  function AdoptionTag({ adopted }) {
  return (
    <span className={`ml-adoption-tag ${adopted ? "adopted" : "not-adopted"}`}>
      {adopted ? "WAPS adopter" : "Not adopted"}
    </span>
  );
}

function percent01(value) {
  // expects 0..1-ish
  return clamp01(value) * 100;
}


  useEffect(() => {
    loadCSV("/data/companies_with_waps_score.csv")
      .then(raw => {
        console.log("Raw CSV data:", raw[0]); // Debug log
        const parsed = raw.map(row => {
        const num = (v, fallback = 0) => {
          const n = Number(v);
          return Number.isFinite(n) ? n : fallback;
        };

        // Core identifiers
        const company_name = row.company_name;

        // Adoption score outputs
        const adoption_percentile = num(row.waps_score_percentile, 0);
        const adoption_score = num(row.waps_adoption_score, 0);
        const waps_rank = num(row.waps_rank, 0);
        const waps_adopted = num(row.waps_adopted, 0); // 1 or 0

        // Normalized feature scores (0–1-ish, depending on your pipeline)
        const sustainability = num(row.sustainability_orientation_score, 0);
        const innovation = num(row.innovation_orientation_score, 0);
        const economic = num(row.economic_orientation_score, 0);

        const operational_barriers = num(row.operational_barriers_score, 0);
        const financial_barriers = num(row.financial_barriers_score, 0);
        const knowledge_gap = num(row.knowledge_gap_score, 0);

        const high_engagement = num(row.high_engagement_score, 0);
        const medium_engagement = num(row.medium_engagement_score, 0);
        const low_engagement = num(row.low_engagement_score, 0);

        // Sentiment
        const finbert_compound = num(row.finbert_compound, 0);
        const sentiment_risk = num(row.sentiment_risk, 0);
        const sentiment_cost = num(row.sentiment_cost, 0);
        const sentiment_sustainability = num(row.sentiment_sustainability, 0);
        const sentiment_innovation = num(row.sentiment_innovation, 0);

        // Metadata
        const n_chunks = num(row.n_chunks, 0);
        const avg_nonzero_tags_per_chunk = num(row.avg_nonzero_tags_per_chunk, 0);

        // Z features used in your logistic regression score (important for methodology section later)
        const z = {
          sustainability: num(row.sustainability_orientation_score_z, 0),
          innovation: num(row.innovation_orientation_score_z, 0),
          economic: num(row.economic_orientation_score_z, 0),
          high_engagement: num(row.high_engagement_score_z, 0),
          operational_barriers: num(row.operational_barriers_score_z, 0),
          sentiment_risk: num(row.sentiment_risk_z, 0),
        };

        return {
          company_name,

          // what we rank by on THIS page (we can change later, but this is clean)
          adoption_percentile,
          adoption_score,
          waps_rank,
          waps_adopted,

          // signals for the page
          sustainability,
          innovation,
          economic,

          operational_barriers,
          financial_barriers,
          knowledge_gap,

          high_engagement,
          medium_engagement,
          low_engagement,

          finbert_compound,
          sentiment_risk,
          sentiment_cost,
          sentiment_sustainability,
          sentiment_innovation,

          n_chunks,
          avg_nonzero_tags_per_chunk,

          // keep z features for transparency/tooltips later
          z,
        };
      });

        console.log("Parsed data:", parsed[0]); // Debug log
        const sorted = parsed.sort((a, b) => b.adoption_percentile - a.adoption_percentile);
        setData(sorted);
        if (sorted.length > 0) setSelectedCompany(sorted[0]);

        setData(sorted);
        if (sorted.length > 0) {
          setSelectedCompany(sorted[0]);
        }
      })
      .catch(err => {
        console.error("CSV load error:", err);
      });
  }, []);

  function SignalBar({ label, value, mode = "pm1" }) {
  let left, width, color;

  if (mode === "01") {
    // Presence scale: 0 = neutral, 1 = strong presence
    const v = clamp01(value);

    left = "50%";               // always start from neutral
    width = `${v * 50}%`;       // grow to the right only
    color = getSignalColor(v);  // color by intensity, not polarity

  } else {
    // Bipolar sentiment scale: -1 .. +1
    const normalized = Math.max(-1, Math.min(1, value));
    const magnitude = Math.abs(normalized);

    left =
      normalized >= 0
        ? "50%"
        : `${50 - magnitude * 50}%`;

    width = `${magnitude * 50}%`;
    color = getSignalColor(normalized);

  }

  return (
    <div className="ml-bar">
      <div className="ml-bar-header">
        <span>{label}</span>
        <span className="ml-bar-value" style={{ color }}>
          {value.toFixed(2)}
        </span>
      </div>
      <div className="ml-bar-track">
        <div className="ml-bar-neutral-line" />

        <div
          className="ml-bar-fill"
          style={{
            left,
            width,
            background: color,
          }}
        />
      </div>


    </div>
  );
}


  const handleCompanyClick = (company) => {
    if (compareMode) {
      setCompareCompany(company);
      setCompareMode(false);
    } else {
      setSelectedCompany(company);
    }
  };

  return (
    <div className="ml-page">
      {/* HERO */}
      <section className="ml-hero container">
        <motion.h1
          className="ml-title"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          Socially-informed machine learning for{" "}
          <span className="accent-text">wind propulsion adoption</span>
        </motion.h1>

        <motion.p
          className="ml-subtitle"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.7 }}
        >
           Scores reflect relative alignment with known adopter patterns, not linear progress toward adoption.
        </motion.p>

        <div className="ml-proof-row">
          <span>52 companies analyzed</span>
          <span>·</span>
          <span>Social-practice-based tags</span>
          <span>·</span>
          <span>Prototype ML pipeline</span>
          <span>·</span>
          <span>Public company text</span>
        </div>
      </section>

      {/* LEGITIMACY */}
      <section className="ml-legitimacy container">
        <div className="ml-legitimacy-box glass">
          <h2 className="ml-section-title">How to read this data</h2>

          <p>
            The adoption readiness score shown on this page is not a prediction of
            future behavior. It is a comparative indicator derived from qualitative
            research, social-science theory, and interpretable machine-learning methods.
          </p>

          <div className="ml-legitimacy-points">
            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Scores are relative and comparative</strong>
                <p>
                  Values are normalized to enable comparison across companies.
                  A higher score reflects stronger alignment with known adoption patterns,
                  not a higher likelihood of adoption.
                </p>
              </div>
            </div>

            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Signals are derived from public discourse</strong>
                <p>
                  The model analyzes how companies publicly frame sustainability,
                  innovation, engagement, and barriers in relation to wind-assisted
                  propulsion. It does not assess internal strategy or technical readiness.
                </p>
              </div>
            </div>

            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Zero values are meaningful</strong>
                <p>
                  A score of 0 does not indicate missing data, but an absence of
                  adoption-relevant discourse in public-facing materials.
                </p>
              </div>
            </div>

            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Prototype and exploratory scope</strong>
                <p>
                  Results are based on a limited sample of companies and publicly
                  available texts. The model is intended for exploration and
                  prioritization, not automated decision-making.
                </p>
              </div>
            </div>
          </div>

          <p className="ml-legitimacy-note">
            This prototype is designed to support strategic targeting,
            stakeholder engagement, and hypothesis generation — not automated judgment.
          </p>
        </div>
      </section>


      {/* STATS OVERVIEW */}
      {data.length > 0 && (
        <section className="ml-stats container">
          <h2 className="ml-section-title">Dataset overview</h2>
          
          <div className="ml-stats-grid">
            <motion.div 
              className="ml-stat-card glass"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              whileHover={{ y: -6 }}
            >
              <div className="ml-stat-label">Companies analyzed</div>
              <div className="ml-stat-value">{data.length}</div>
            </motion.div>

            <motion.div 
              className="ml-stat-card glass"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              whileHover={{ y: -6 }}
            >
              <div className="ml-stat-label">High adoption potential</div>
              <div className="ml-stat-value">
                {data.filter(c => c.adoption_percentile >= 75).length}
              </div>
              <div className="ml-stat-detail">Score ≥ 75</div>
            </motion.div>

            <motion.div 
              className="ml-stat-card glass"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              whileHover={{ y: -6 }}
            >
              <div className="ml-stat-label">Avg sustainability framing sentiment</div>
              <div className="ml-stat-value">
                {(
                  data.reduce((sum, c) => sum + c.finbert_compound, 0) / data.length
                ).toFixed(2)
                }
              </div>
              <div className="ml-stat-detail">Across all companies</div>
            </motion.div>

            <motion.div 
              className="ml-stat-card glass"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
              whileHover={{ y: -6 }}
            >
              <div className="ml-stat-label">Economic prevalence</div>
              <div className="ml-stat-value">
                {(
                  data.reduce((sum, c) => sum + c.economic, 0) / data.length
                ).toFixed(2)
                }
              </div>
              <div className="ml-stat-detail">Importance of economic factors</div>
            </motion.div>
          </div>

          {/* SIGNAL DISTRIBUTION BARS */}

          <div className="ml-stats-distribution glass">
            <h2 className="ml-section-title">Signals the model detects</h2>
              <p>
                The model does not assess technical readiness or internal strategy.
                It analyzes how companies publicly frame sustainability, innovation,
                engagement, and barriers in relation to wind-assisted propulsion.
              </p>
              <p className="ml-note">
                Low or zero scores indicate limited public discourse — not opposition
                or lack of internal activity. Counts reflect how often strong adoption-aligned signals appear in public company texts.
              </p>

            {[
              { key: "sustainability", label: "Sustainability orientation" },
              { key: "innovation", label: "Innovation orientation" },
              { key: "economic", label: "Economic orientation" },
              { key: "high_engagement", label: "High engagement" },
            ]
            .map((signal) => {
              const positive = data.filter(c => c[signal.key] >= 0.6).length;
              const neutral = data.filter(c => c[signal.key] >= 0.3 && c[signal.key] < 0.6).length;
              const negative = data.filter(c => c[signal.key] < 0.3).length;
              const total = data.length;



              return (
                <div key={signal.key} className="ml-dist-row">
                  <div className="ml-dist-label">{signal.label}</div>
                  <div className="ml-dist-bar">
                    <div 
                      className="ml-dist-segment positive"
                      style={{ width: `${(positive / total) * 100}%` }}
                    >
                      {positive > 0 && <span>{positive}</span>}
                    </div>
                    <div 
                      className="ml-dist-segment neutral"
                      style={{ width: `${(neutral / total) * 100}%` }}
                    >
                      {neutral > 0 && <span>{neutral}</span>}
                    </div>
                    <div 
                      className="ml-dist-segment negative"
                      style={{ width: `${(negative / total) * 100}%` }}
                    >
                      {negative > 0 && <span>{negative}</span>}
                    </div>
                  </div>
                  <div className="ml-dist-legend">
                    <span className="positive">{positive} positive</span>
                    <span className="neutral">{neutral} neutral</span>
                    <span className="negative">{negative} negative</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* METHOD */}
      <section className="ml-method container">
        <h2 className="ml-section-title">How were these signals constructed?</h2>
        <p className="ml-method-description">This pipeline prioritizes interpretability over predictive accuracy in order to support strategic reasoning and intervention design.</p>

        <div className="ml-method-grid">
          <motion.div
            className="ml-method-card glass"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
          >
            <div className="ml-method-number">1</div>
            <h3>Social foundations</h3>
            <p>
              Qualitative research, digital ethnography, and systems analysis were used
              to understand how shipping companies frame sustainability, innovation,
              economic considerations, and operational risk in relation to new technologies.
            </p>
          </motion.div>

          <motion.div
            className="ml-method-card glass"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            <div className="ml-method-number">2</div>
            <h3>Text processing and signal extraction</h3>
            <p>
              Publicly available company texts were collected and split into smaller
              chunks to capture variation within companies and avoid dominance by
              long documents. Each chunk was analyzed using social-practice-based
              tags and contextual sentiment analysis to extract interpretable signals.
            </p>
          </motion.div>

          <motion.div
            className="ml-method-card glass"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <div className="ml-method-number">3</div>
            <h3>Aggregation and interpretable modeling</h3>
            <p>
              Chunk-level signals were aggregated to the company level and standardized.
              An interpretable logistic regression model was then used to identify which
              combinations of signals are associated with confirmed WAPS adoption.
              The resulting coefficients were used to construct a continuous,
              explainable adoption readiness score.
            </p>
          </motion.div>
        </div>
      </section>
{/* WORKFLOW VISUAL */}
<section className="ml-workflow container ml-section-block">
  <h2 className="ml-section-title">
    From public discourse to adoption readiness
  </h2>

  <div className="ml-workflow-steps">
    <div className="ml-workflow-step">
      <div className="ml-workflow-icon">
        <FileText size={26} />
      </div>
      <h4>Public company texts</h4>
      <p>
        Websites, reports, and press releases form the empirical basis
        of the analysis.
      </p>
    </div>

    <div className="ml-workflow-arrow" aria-hidden />

    <div className="ml-workflow-step">
      <div className="ml-workflow-icon">
        <ScanSearch size={26} />
      </div>
      <h4>Chunking & signal extraction</h4>
      <p>
        Texts are split into smaller units and analyzed using
        social-practice-based tags and contextual sentiment.
      </p>
    </div>

    <div className="ml-workflow-arrow" aria-hidden />

    <div className="ml-workflow-step">
      <div className="ml-workflow-icon">
        <Scale size={26} />
      </div>
      <h4>Interpretable modeling</h4>
      <p>
        Signals are aggregated, standardized, and combined using
        logistic regression to identify adoption-aligned patterns.
      </p>
    </div>

    <div className="ml-workflow-arrow" aria-hidden />

    <div className="ml-workflow-step highlight">
      <div className="ml-workflow-icon">
        <BarChart3 size={26} />
      </div>
      <h4>Adoption readiness indicator</h4>
      <p>
        A continuous, explainable indicator used to compare and
        explore companies.
      </p>
    </div>
  </div>
</section>



      {/* RANKING */}
      <section className="ml-data container">
        <div className="ml-data-header">
          <h2 className="ml-section-title">
            Exploring adoption readiness across companies
          </h2>
          <p className="ml-data-subtitle">
            Scores reflect relative alignment with known adopter discourse patterns,
            not linear progress toward adoption.
          </p>
          <div className="ml-view-toggle">
            <button   
              className={`btn-view ${viewMode === "list" ? "active" : ""}`}
              onClick={() => setViewMode("list")}
            >
              Top 10
            </button>
            <button 
              className={`btn-view ${viewMode === "grid" ? "active" : ""}`}
              onClick={() => setViewMode("grid")}
            >
              All Companies
            </button>
          </div>
        </div>

        {viewMode === "list" ? (
          <div className="ml-ranking">
            {data.slice(0, 10).map((company, i) => (
              <motion.button
                key={company.company_name}
                className={`ml-rank-row glass ${
                  selectedCompany?.company_name === company.company_name
                    ? "selected"
                    : compareCompany?.company_name === company.company_name
                    ? "compare"
                    : ""
                }`}
                onClick={() => handleCompanyClick(company)}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                whileHover={{ x: 4 }}
              >
                <span className="ml-rank-index">#{i + 1}</span>
                <span className="ml-rank-name">
                  {company.company_name}
                  <AdoptionTag adopted={company.waps_adopted === 1} />
                </span>

                <span className="ml-rank-score">{company.adoption_percentile.toFixed(1)}</span>
              </motion.button>
            ))}
          </div>
        ) : (
          <div className="ml-grid-view">
            {data.map((company, i) => (
              <motion.button
                key={company.company_name}
                className={`ml-grid-card glass ${
                  selectedCompany?.company_name === company.company_name
                    ? "selected"
                    : compareCompany?.company_name === company.company_name
                    ? "compare"
                    : ""
                }`}
                onClick={() => handleCompanyClick(company)}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ delay: Math.min(i * 0.02, 0.5) }}
                whileHover={{ y: -4, scale: 1.02 }}
              >
                <div className="ml-grid-rank">#{i + 1}</div>
                <div className="ml-grid-name">
                  {company.company_name}
                  <AdoptionTag adopted={company.waps_adopted === 1} />
                </div>

                <div className="ml-grid-score-wrapper">
                  <div
                    className="ml-grid-score"
                    style={{ color: getSignalColor((company.adoption_percentile / 100 - 0.5) * 2) }}
                  >
                    {company.adoption_percentile.toFixed(1)}
                  </div>

                  <div className="ml-score-axis">
                    <span>Low</span>
                    <span className="neutral">Neutral</span>
                    <span>High</span>
                  </div>
                </div>

                <div className="ml-grid-bars">
                  <div className="ml-grid-bars">
                  {[
                    company.sustainability,
                    company.innovation,
                    company.high_engagement,
                    company.operational_barriers,
                  ].map((v, idx) => (
                    <div className="ml-grid-mini-bar centered">
                      <div
                        className="ml-grid-mini-fill"
                        style={{
                          left: `${50 + (clamp01(v) - 0.5) * 50}%`,
                          width: `${Math.abs((clamp01(v) - 0.5) * 100)}%`,
                          background: getSignalColor((clamp01(v) - 0.5) * 2),
                        }}
                      />
                    </div>
                  ))}
                </div>
                </div>
              </motion.button>
            ))}
          </div>
        )}

        {selectedCompany && (
          <div className="ml-compare-toggle">
            <button
              className={`btn glass btn-secondary ${compareMode ? "active" : ""}`}
              onClick={() => setCompareMode(!compareMode)}
            >
              {compareMode ? "Select company to compare" : "Compare with another"}
            </button>
            {compareCompany && !compareMode && (
              <button
                className="btn glass btn-secondary"
                onClick={() => setCompareCompany(null)}
              >
                Clear comparison
              </button>
            )}
          </div>
        )}
      </section>

      {/* BREAKDOWN OR COMPARISON */}
      {selectedCompany && !compareCompany && (
        <section className="ml-breakdown container">
        <div className="ml-breakdown-header">
          <h2 className="ml-section-title">
            Detailed breakdown: {selectedCompany.company_name}
          </h2>
          <AdoptionTag adopted={selectedCompany.waps_adopted === 1} />
        </div>


          <div className="ml-breakdown-grid">
            {[
              { label: "Sustainability orientation", value: selectedCompany.sustainability, mode: "01" },
              { label: "Innovation orientation", value: selectedCompany.innovation, mode: "01" },
              { label: "Economic orientation", value: selectedCompany.economic, mode: "01" },
              { label: "High engagement", value: selectedCompany.high_engagement, mode: "01" },
              { label: "Operational barriers", value: selectedCompany.operational_barriers, mode: "01" },
              { label: "Risk sentiment", value: selectedCompany.sentiment_risk, mode: "pm1" },
            ].map((item, i) => (
              <motion.div
                key={item.label}
                className="ml-break-item glass"
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <span className="ml-break-label">{item.label}</span>
                <strong 
                  className="ml-break-value"
                  style={{ color: getSignalColor(item.value) }}
                >
                  {item.value.toFixed(2)}
                </strong>
                <span className="ml-break-interpretation">
                  {interpretSignal(item.value)}
                </span>
              </motion.div>
            ))}
          </div>

          <div className="ml-bars glass">
            <h3>Signal visualization</h3>
            <SignalBar label="Sustainability orientation" value={selectedCompany.sustainability} mode="01" />
            <SignalBar label="Innovation orientation" value={selectedCompany.innovation} mode="01" />
            <SignalBar label="Economic orientation" value={selectedCompany.economic} mode="01" />
            <SignalBar label="Risk sentiment" value={selectedCompany.sentiment_risk} mode="pm1" />

          </div>
        </section>
      )}
      {selectedCompany && compareCompany && (
  <section className="ml-compare container">
    <div className="ml-compare-header">
      <h2 className="ml-section-title">
        Comparing adoption-relevant signals
      </h2>

      <div className="ml-compare-companies">
        <div className="ml-compare-company">
          <strong>{selectedCompany.company_name}</strong>
          <AdoptionTag adopted={selectedCompany.waps_adopted === 1} />
          <div className="ml-compare-score">
            Readiness: {selectedCompany.adoption_percentile.toFixed(1)}
          </div>
        </div>

        <div className="ml-compare-vs">vs</div>

        <div className="ml-compare-company">
          <strong>{compareCompany.company_name}</strong>
          <AdoptionTag adopted={compareCompany.waps_adopted === 1} />
          <div className="ml-compare-score">
            Readiness: {compareCompany.adoption_percentile.toFixed(1)}
          </div>
        </div>
      </div>
    </div>

    <div className="ml-compare-grid glass">
      {[
        { key: "sustainability", label: "Sustainability orientation", mode: "01" },
        { key: "innovation", label: "Innovation orientation", mode: "01" },
        { key: "economic", label: "Economic orientation", mode: "01" },
        { key: "sentiment_risk", label: "Risk sentiment", mode: "pm1" },
      ].map((signal) => {
        const a = selectedCompany[signal.key];
        const b = compareCompany[signal.key];
        const diff = a - b;

        return (
          <div key={signal.key} className="ml-compare-row">
            <div className="ml-compare-label">{signal.label}</div>

            <div className="ml-compare-bars">
              <SignalBar
                label={selectedCompany.company_name}
                value={a}
                mode={signal.mode}
              />
              <SignalBar
                label={compareCompany.company_name}
                value={b}
                mode={signal.mode}
              />
            </div>

            <div className="ml-compare-diff">
              Difference:{" "}
              <span
                style={{ color: getSignalColor(diff) }}
              >
                {diff > 0 ? "+" : ""}
                {diff.toFixed(2)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  </section>
)}

    </div>
  );
}