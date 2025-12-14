import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { loadCSV } from "../utils/loadCSV";
import "../styles/MLInsights.css";

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

export default function MLInsights() {
  const [data, setData] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [compareCompany, setCompareCompany] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [viewMode, setViewMode] = useState("list"); // "list" or "grid"

  useEffect(() => {
    loadCSV("/data/score_breakdown_normalized.csv")
      .then(raw => {
        console.log("Raw CSV data:", raw[0]); // Debug log
        const parsed = raw.map(row => {
          // More robust parsing - handle different possible column names
          const total = Number(row.total || row.WAPS_score_normalized || 0);
          const topic = Number(row.topic_signal || row.topic_weighted || 0);
          const sentiment = Number(row.sentiment_signal || row.sentiment_weighted || 0);
          const tag = Number(row.tag_signal || row.tag_weighted || 0);
          const technical = Number(row.technical_fit || row.technical_weighted || 0);
          
          return {
            company_name: row.company_name,
            total: isNaN(total) ? 0 : Math.max(-2, Math.min(2, total)), // Clamp to reasonable range
            topic_signal: isNaN(topic) ? 0 : Math.max(-1, Math.min(1, topic)),
            sentiment_signal: isNaN(sentiment) ? 0 : Math.max(-1, Math.min(1, sentiment)),
            tag_signal: isNaN(tag) ? 0 : Math.max(-1, Math.min(1, tag)),
            technical_fit: isNaN(technical) ? 0 : Math.max(-1, Math.min(1, technical)),
          };
        });
        console.log("Parsed data:", parsed[0]); // Debug log
        const sorted = parsed.sort((a, b) => b.total - a.total);
        setData(sorted);
        if (sorted.length > 0) {
          setSelectedCompany(sorted[0]);
        }
      })
      .catch(err => {
        console.error("CSV load error:", err);
      });
  }, []);

  function SignalBar({ label, value, showLabel = true }) {
    const percentage = Math.min(Math.max((value + 1) * 50, 0), 100);
    const color = getSignalColor(value);

    return (
      <div className="ml-bar">
        {showLabel && (
          <div className="ml-bar-header">
            <span>{label}</span>
            <span className="ml-bar-value" style={{ color }}>{value.toFixed(2)}</span>
          </div>
        )}
        <div className="ml-bar-track">
          <div
            className="ml-bar-fill"
            style={{ 
              width: `${percentage}%`,
              background: `linear-gradient(90deg, ${color}, ${color}dd)`
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
          A prototype model that translates social-science theory into
          interpretable signals for technology adoption.
        </motion.p>

        <div className="ml-proof-row">
          <span>80 companies analyzed</span>
          <span>·</span>
          <span>Social-practice-based tags</span>
          <span>·</span>
          <span>Prototype ML pipeline</span>
          <span>·</span>
          <span>Public company text</span>
        </div>
      </section>

      {/* BRIDGE */}
      <section className="ml-bridge container">
        <div className="ml-bridge-content glass">
          <p>
            Rather than predicting behavior from abstract metrics,
            this model is grounded in qualitative research and
            social-practice theory, designed to support
            strategic decision-making rather than automated judgment.
          </p>
        </div>
      </section>

      {/* LEGITIMACY - MOVED UP */}
      <section className="ml-legitimacy container">
        <div className="ml-legitimacy-box glass">
          <h2 className="ml-section-title">How to read this data</h2>

          <p>
            The adoption alignment score is not a prediction of future behavior.
            It is a composite indicator derived from qualitative research,
            social-science theory, and interpretable machine-learning techniques.
          </p>

          <div className="ml-legitimacy-points">
            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Scores are relative</strong>
                <p>Values are normalized to enable comparison across companies, not absolute ranking.</p>
              </div>
            </div>

            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Signals are interpretive</strong>
                <p>Topic, sentiment, and tag signals reflect discourse and orientation, not internal decision-making.</p>
              </div>
            </div>

            <div className="ml-legitimacy-point">
              <div className="ml-legitimacy-icon">→</div>
              <div>
                <strong>Prototype scope</strong>
                <p>Analysis is based on publicly available company texts and a limited sample of firms.</p>
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
                {data.filter(c => c.total > 0.5).length}
              </div>
              <div className="ml-stat-detail">Score &gt; 0.5</div>
            </motion.div>

            <motion.div 
              className="ml-stat-card glass"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              whileHover={{ y: -6 }}
            >
              <div className="ml-stat-label">Avg sentiment signal</div>
              <div className="ml-stat-value">
                {(data.reduce((sum, c) => sum + c.sentiment_signal, 0) / data.length).toFixed(2)}
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
              <div className="ml-stat-label">Avg technical fit</div>
              <div className="ml-stat-value">
                {(data.reduce((sum, c) => sum + c.technical_fit, 0) / data.length).toFixed(2)}
              </div>
              <div className="ml-stat-detail">Fleet compatibility</div>
            </motion.div>
          </div>

          {/* SIGNAL DISTRIBUTION BARS */}
          <div className="ml-stats-distribution glass">
            <h3>Signal strength distribution</h3>
            {[
              { key: "topic_signal", label: "Topic alignment" },
              { key: "sentiment_signal", label: "Sentiment" },
              { key: "tag_signal", label: "Practice tags" },
              { key: "technical_fit", label: "Technical fit" },
            ].map((signal) => {
              const positive = data.filter(c => c[signal.key] > 0.2).length;
              const neutral = data.filter(c => c[signal.key] >= -0.2 && c[signal.key] <= 0.2).length;
              const negative = data.filter(c => c[signal.key] < -0.2).length;
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
        <h2 className="ml-section-title">Where does the data come from?</h2>
        
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
              Ethnographies and systems analysis were used to understand
              how shipping companies frame sustainability, innovation,
              and operational risk.
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
            <h3>Translation into tags</h3>
            <p>
              Social Practice Theory informed the construction of
              interpretable tags capturing meanings, competences,
              orientations, and barriers.
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
            <h3>NLP & interpretation</h3>
            <p>
              Publicly available company texts were analyzed using NLP
              and sentiment analysis, producing normalized, comparative
              indicators rather than absolute scores.
            </p>
          </motion.div>
        </div>
      </section>

      {/* RANKING */}
      <section className="ml-data container">
        <div className="ml-data-header">
          <h2 className="ml-section-title">
            Companies most aligned with wind propulsion adoption
          </h2>
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
                <span className="ml-rank-name">{company.company_name}</span>
                <span className="ml-rank-score">{company.total.toFixed(2)}</span>
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
                <div className="ml-grid-name">{company.company_name}</div>
                <div className="ml-grid-score" style={{ color: getSignalColor(company.total) }}>
                  {company.total.toFixed(2)}
                </div>
                <div className="ml-grid-bars">
                  <div className="ml-grid-mini-bar">
                    <div 
                      className="ml-grid-mini-fill" 
                      style={{ 
                        width: `${Math.min(Math.max((company.topic_signal + 1) * 50, 0), 100)}%`,
                        background: getSignalColor(company.topic_signal)
                      }}
                    />
                  </div>
                  <div className="ml-grid-mini-bar">
                    <div 
                      className="ml-grid-mini-fill" 
                      style={{ 
                        width: `${Math.min(Math.max((company.sentiment_signal + 1) * 50, 0), 100)}%`,
                        background: getSignalColor(company.sentiment_signal)
                      }}
                    />
                  </div>
                  <div className="ml-grid-mini-bar">
                    <div 
                      className="ml-grid-mini-fill" 
                      style={{ 
                        width: `${Math.min(Math.max((company.tag_signal + 1) * 50, 0), 100)}%`,
                        background: getSignalColor(company.tag_signal)
                      }}
                    />
                  </div>
                  <div className="ml-grid-mini-bar">
                    <div 
                      className="ml-grid-mini-fill" 
                      style={{ 
                        width: `${Math.min(Math.max((company.technical_fit + 1) * 50, 0), 100)}%`,
                        background: getSignalColor(company.technical_fit)
                      }}
                    />
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
          <h2 className="ml-section-title">
            Detailed breakdown: {selectedCompany.company_name}
          </h2>

          <div className="ml-breakdown-grid">
            {[
              { label: "Topic signal", value: selectedCompany.topic_signal },
              { label: "Sentiment signal", value: selectedCompany.sentiment_signal },
              { label: "Tag signal", value: selectedCompany.tag_signal },
              { label: "Technical fit", value: selectedCompany.technical_fit },
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
            <SignalBar label="Topic alignment" value={selectedCompany.topic_signal} />
            <SignalBar label="Sentiment" value={selectedCompany.sentiment_signal} />
            <SignalBar label="Social-practice tags" value={selectedCompany.tag_signal} />
            <SignalBar label="Technical fit" value={selectedCompany.technical_fit} />
          </div>

          {/* DISTRIBUTION CHART */}
          <div className="ml-chart glass">
            <h3>Signal distribution across all companies</h3>
            <div className="ml-chart-content">
              {["topic_signal", "sentiment_signal", "tag_signal", "technical_fit"].map((signal, idx) => {
                const signalLabel = signal.replace(/_/g, " ").replace(/^\w/, c => c.toUpperCase());
                const values = data.map(c => c[signal]).filter(v => !isNaN(v));
                const avg = values.reduce((a, b) => a + b, 0) / values.length;
                const currentValue = selectedCompany[signal];
                
                return (
                  <div key={signal} className="ml-chart-row">
                    <div className="ml-chart-label">{signalLabel}</div>
                    <div className="ml-chart-bar-container">
                      <div className="ml-chart-bar">
                        {/* Show distribution range */}
                        <div className="ml-chart-range" style={{ 
                          left: "25%", 
                          width: "50%",
                          background: "rgba(125,211,252,0.1)"
                        }} />
                        {/* Average marker */}
                        <div 
                          className="ml-chart-avg" 
                          style={{ left: `${(avg + 1) * 50}%` }}
                          title={`Average: ${avg.toFixed(2)}`}
                        />
                        {/* Current company marker */}
                        <div 
                          className="ml-chart-marker" 
                          style={{ 
                            left: `${(currentValue + 1) * 50}%`,
                            background: getSignalColor(currentValue)
                          }}
                        >
                          <span>{currentValue.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="ml-chart-axis">
                        <span>-1.0</span>
                        <span>0</span>
                        <span>1.0</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* SCATTER PLOT - SIGNAL CORRELATION */}
      {data.length > 0 && (
        <section className="ml-scatter container">
          <h2 className="ml-section-title">Signal relationships</h2>
          <p className="ml-scatter-subtitle">
            Explore how different signals correlate. Each point represents a company.
            Click to select or compare.
          </p>
          <div className="ml-scatter-grid">
            <div className="ml-scatter-chart glass">
              <h3>Technical fit vs. Total score</h3>
              <div className="ml-scatter-plot">
                <div className="ml-scatter-axis-y">
                  <span>2.0</span>
                  <span>1.0</span>
                  <span>0</span>
                  <span>-1.0</span>
                </div>
                <div className="ml-scatter-content">
                  {data.map((company, i) => {
                    const x = ((company.technical_fit + 1) / 2) * 100;
                    const y = 100 - ((company.total + 2) / 4) * 100;
                    const isSelected = selectedCompany?.company_name === company.company_name;
                    const isCompare = compareCompany?.company_name === company.company_name;
                    
                    return (
                      <div
                        key={company.company_name}
                        className={`ml-scatter-point ${isSelected ? "selected" : ""} ${isCompare ? "compare" : ""}`}
                        style={{ 
                          left: `${x}%`, 
                          top: `${y}%`,
                          background: getSignalColor(company.total),
                          opacity: isSelected || isCompare ? 1 : 0.6
                        }}
                        onClick={() => handleCompanyClick(company)}
                        title={`${company.company_name}: ${company.total.toFixed(2)}`}
                      />
                    );
                  })}
                  {/* Grid lines */}
                  <div className="ml-scatter-grid-line" style={{ left: "50%", height: "100%" }} />
                  <div className="ml-scatter-grid-line" style={{ top: "50%", width: "100%" }} />
                </div>
                <div className="ml-scatter-axis-x">
                  <span>-1.0</span>
                  <span>Technical fit</span>
                  <span>1.0</span>
                </div>
              </div>
            </div>

            <div className="ml-scatter-chart glass">
              <h3>Sentiment vs. Tag signal</h3>
              <div className="ml-scatter-plot">
                <div className="ml-scatter-axis-y">
                  <span>1.0</span>
                  <span>0.5</span>
                  <span>0</span>
                  <span>-0.5</span>
                </div>
                <div className="ml-scatter-content">
                  {data.map((company, i) => {
                    const x = ((company.sentiment_signal + 1) / 2) * 100;
                    const y = 100 - ((company.tag_signal + 1) / 2) * 100;
                    const isSelected = selectedCompany?.company_name === company.company_name;
                    const isCompare = compareCompany?.company_name === company.company_name;
                    
                    return (
                      <div
                        key={company.company_name}
                        className={`ml-scatter-point ${isSelected ? "selected" : ""} ${isCompare ? "compare" : ""}`}
                        style={{ 
                          left: `${x}%`, 
                          top: `${y}%`,
                          background: getSignalColor(company.total),
                          opacity: isSelected || isCompare ? 1 : 0.6
                        }}
                        onClick={() => handleCompanyClick(company)}
                        title={`${company.company_name}: ${company.total.toFixed(2)}`}
                      />
                    );
                  })}
                  <div className="ml-scatter-grid-line" style={{ left: "50%", height: "100%" }} />
                  <div className="ml-scatter-grid-line" style={{ top: "50%", width: "100%" }} />
                </div>
                <div className="ml-scatter-axis-x">
                  <span>-1.0</span>
                  <span>Sentiment</span>
                  <span>1.0</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {selectedCompany && compareCompany && (
        <section className="ml-compare container">
          <h2 className="ml-section-title">Side-by-side comparison</h2>

          <div className="ml-compare-grid">
            <div className="ml-compare-col glass">
              <div className="ml-compare-header">
                <h3>{selectedCompany.company_name}</h3>
                <div className="ml-compare-total">
                  Total: <span style={{ color: getSignalColor(selectedCompany.total) }}>
                    {selectedCompany.total.toFixed(2)}
                  </span>
                </div>
              </div>
              <div className="ml-compare-bars">
                <SignalBar label="Topic" value={selectedCompany.topic_signal} />
                <SignalBar label="Sentiment" value={selectedCompany.sentiment_signal} />
                <SignalBar label="Tags" value={selectedCompany.tag_signal} />
                <SignalBar label="Technical" value={selectedCompany.technical_fit} />
              </div>
            </div>

            <div className="ml-compare-col glass">
              <div className="ml-compare-header">
                <h3>{compareCompany.company_name}</h3>
                <div className="ml-compare-total">
                  Total: <span style={{ color: getSignalColor(compareCompany.total) }}>
                    {compareCompany.total.toFixed(2)}
                  </span>
                </div>
              </div>
              <div className="ml-compare-bars">
                <SignalBar label="Topic" value={compareCompany.topic_signal} />
                <SignalBar label="Sentiment" value={compareCompany.sentiment_signal} />
                <SignalBar label="Tags" value={compareCompany.tag_signal} />
                <SignalBar label="Technical" value={compareCompany.technical_fit} />
              </div>
            </div>
          </div>
        </section>
      )}

      {/* SCATTER PLOT - SIGNAL CORRELATION */}
      {data.length > 0 && (
        <section className="ml-scatter container">
          <h2 className="ml-section-title">Signal relationships</h2>
          <p className="ml-scatter-subtitle">
            Explore how different signals correlate. Each point represents a company.
            Click to select or compare.
          </p>
          <div className="ml-scatter-grid">
            <div className="ml-scatter-chart glass">
              <h3>Technical fit vs. Total score</h3>
              <div className="ml-scatter-plot">
                <div className="ml-scatter-axis-y">
                  <span>2.0</span>
                  <span>1.0</span>
                  <span>0</span>
                  <span>-1.0</span>
                </div>
                <div className="ml-scatter-content">
                  {data.map((company, i) => {
                    const x = ((company.technical_fit + 1) / 2) * 100;
                    const y = 100 - ((company.total + 2) / 4) * 100;
                    const isSelected = selectedCompany?.company_name === company.company_name;
                    const isCompare = compareCompany?.company_name === company.company_name;
                    
                    return (
                      <div
                        key={company.company_name}
                        className={`ml-scatter-point ${isSelected ? "selected" : ""} ${isCompare ? "compare" : ""}`}
                        style={{ 
                          left: `${x}%`, 
                          top: `${y}%`,
                          background: getSignalColor(company.total),
                          opacity: isSelected || isCompare ? 1 : 0.6
                        }}
                        onClick={() => handleCompanyClick(company)}
                        title={`${company.company_name}: ${company.total.toFixed(2)}`}
                      />
                    );
                  })}
                  {/* Grid lines */}
                  <div className="ml-scatter-grid-line" style={{ left: "50%", height: "100%" }} />
                  <div className="ml-scatter-grid-line" style={{ top: "50%", width: "100%" }} />
                </div>
                <div className="ml-scatter-axis-x">
                  <span>-1.0</span>
                  <span>Technical fit</span>
                  <span>1.0</span>
                </div>
              </div>
            </div>

            <div className="ml-scatter-chart glass">
              <h3>Sentiment vs. Tag signal</h3>
              <div className="ml-scatter-plot">
                <div className="ml-scatter-axis-y">
                  <span>1.0</span>
                  <span>0.5</span>
                  <span>0</span>
                  <span>-0.5</span>
                </div>
                <div className="ml-scatter-content">
                  {data.map((company, i) => {
                    const x = ((company.sentiment_signal + 1) / 2) * 100;
                    const y = 100 - ((company.tag_signal + 1) / 2) * 100;
                    const isSelected = selectedCompany?.company_name === company.company_name;
                    const isCompare = compareCompany?.company_name === company.company_name;
                    
                    return (
                      <div
                        key={company.company_name}
                        className={`ml-scatter-point ${isSelected ? "selected" : ""} ${isCompare ? "compare" : ""}`}
                        style={{ 
                          left: `${x}%`, 
                          top: `${y}%`,
                          background: getSignalColor(company.total),
                          opacity: isSelected || isCompare ? 1 : 0.6
                        }}
                        onClick={() => handleCompanyClick(company)}
                        title={`${company.company_name}: ${company.total.toFixed(2)}`}
                      />
                    );
                  })}
                  <div className="ml-scatter-grid-line" style={{ left: "50%", height: "100%" }} />
                  <div className="ml-scatter-grid-line" style={{ top: "50%", width: "100%" }} />
                </div>
                <div className="ml-scatter-axis-x">
                  <span>-1.0</span>
                  <span>Sentiment</span>
                  <span>1.0</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}