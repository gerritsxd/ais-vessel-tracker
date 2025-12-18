import React, { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import "../styles/Intelligence.css";

export default function Intelligence() {
  // ----------------------------
  // Placeholder-safe state
  // ----------------------------
  const [stats, setStats] = useState({
    total_companies: 0,
    total_findings: 0,
    avg_findings_per_company: 0,
    categories: {},
    top_companies: []
  });

  const [datasets, setDatasets] = useState([]);
  const [profileScope, setProfileScope] = useState(""); // "", "wasp", "non_wasp"
  const [profilesSummary, setProfilesSummary] = useState({
    file: null,
    intelligence_file: null,
    total: 0,
    companies: []
  });
  const [profilesError, setProfilesError] = useState("");
  const [scraperStatus, setScraperStatus] = useState({
    intelligence: {
      running: false,
      current_company: "-",
      companies_processed: 0,
      total_companies: 0,
      findings_count: 0,
      progress: 0
    },
    profiler: {
      running: false,
      current_company: "-",
      companies_processed: 0,
      total_companies: 0,
      profiles_count: 0,
      progress: 0
    }
  });

  const CATEGORY_NAMES = {
    grants_subsidies: "🇩🇪 Grants & Subsidies",
    legal_violations: "⚖️ Legal Violations",
    sustainability_news: "📰 Sustainability News",
    reputation: "🏆 Reputation & Rankings",
    financial_pressure: "💰 Financial Pressure"
  };

  // ----------------------------
  // Backend calls (with fallback placeholders)
  // ----------------------------

  async function loadStats() {
    try {
      const res = await fetch("/ships/api/intelligence/stats");
      if (!res.ok) throw new Error("Backend not ready");
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.log("Stats endpoint not available, using placeholders");
      setStats(prev => ({
        ...prev,
        total_companies: 0,
        total_findings: 0,
        avg_findings_per_company: 0,
        categories: {},
        top_companies: []
      }));
    }
  }

  async function loadDatasets() {
    try {
      const res = await fetch("/ships/api/intelligence/datasets");
      if (!res.ok) throw new Error("Backend not ready");
      const data = await res.json();
      setDatasets(data.datasets || []);
    } catch (err) {
      console.log("Dataset endpoint offline");
      setDatasets([]);
    }
  }

  async function loadProfilesSummary() {
    try {
      const qs = new URLSearchParams();
      qs.set("limit", "24");
      if (profileScope) qs.set("scope", profileScope);
      const res = await fetch(`/ships/api/intelligence/company-profiles/summary?${qs.toString()}`);
      if (!res.ok) throw new Error("Profiles endpoint not ready");
      const data = await res.json();
      setProfilesSummary(data);
      setProfilesError("");
    } catch (err) {
      setProfilesError("No profile summary available yet.");
      setProfilesSummary({
        file: null,
        intelligence_file: null,
        total: 0,
        companies: []
      });
    }
  }

  async function loadScraperStatus() {
    try {
      const res = await fetch("/ships/api/scrapers/status");
      if (!res.ok) throw new Error("Backend not ready");
      const data = await res.json();
      setScraperStatus(data);
    } catch (err) {
      console.log("Scraper status not available");
      // Keep placeholders
    }
  }

  async function loadPage() {
    await Promise.all([loadStats(), loadDatasets(), loadScraperStatus(), loadProfilesSummary()]);
  }

  // ----------------------------
  // Auto-refresh timers
  // ----------------------------
  useEffect(() => {
    loadPage();
    const refreshStats = setInterval(loadPage, 30000);
    const refreshScraper = setInterval(loadScraperStatus, 5000);

    return () => {
      clearInterval(refreshStats);
      clearInterval(refreshScraper);
    };
  }, []);

  // Refresh profiles when scope changes
  useEffect(() => {
    loadProfilesSummary();
  }, [profileScope]);

  return (
    <div className="intel-page">
      {/* ---------- HEADER ---------- */}
      <header className="intel-header">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          🕵️ Company Intelligence Dashboard
        </motion.h1>
        <p className="intel-subtitle">
          High-level intelligence insights based on scraped company data.
        </p>
      </header>

      <div className="intel-container">

        {/* ---------- COMPANY PROFILES + SENTIMENT (TOP) ---------- */}
        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="intel-section-title">🧾 Company Profiles + Website Sentiment</div>

          <div className="profiles-toolbar">
            <div className="profiles-meta">
              <div className="profiles-meta-row">
                <span className="profiles-meta-label">Profile dataset:</span>
                <span className="profiles-meta-value">
                  {profilesSummary.file || "-"}
                </span>
              </div>
              <div className="profiles-meta-row">
                <span className="profiles-meta-label">Intel dataset:</span>
                <span className="profiles-meta-value">
                  {profilesSummary.intelligence_file || "-"}
                </span>
              </div>
            </div>

            <div className="profiles-controls">
              <label className="profiles-select-label">
                Scope
                <select
                  className="profiles-select"
                  value={profileScope}
                  onChange={(e) => setProfileScope(e.target.value)}
                >
                  <option value="">Latest</option>
                  <option value="wasp">WASP</option>
                  <option value="non_wasp">Non‑WASP</option>
                </select>
              </label>
              <button className="profiles-refresh" onClick={loadProfilesSummary}>
                Refresh
              </button>
            </div>
          </div>

          {profilesError ? (
            <div className="empty-state">{profilesError}</div>
          ) : (
            <div className="profiles-grid">
              <div className="profiles-plot-card">
                <div className="profiles-plot-title">Normalized sentiment scatter</div>
                <SentimentScatter companies={profilesSummary.companies || []} />
                <div className="profiles-plot-caption">
                  x = polarity (z), y = subjectivity (z), bubble ~ log(1+text_len)
                </div>
              </div>

              <div className="profiles-cards">
                {(profilesSummary.companies || []).length === 0 ? (
                  <div className="empty-state">No company profiles loaded yet</div>
                ) : (
                  (profilesSummary.companies || []).map((c) => (
                    <div className="profile-card" key={c.company_name}>
                      <div className="profile-card-title">
                        {c.company_name}
                        <span className="profile-chip">
                          {c.attributes?.vessel_count ?? 0} vessels
                        </span>
                      </div>

                      <div className="profile-card-row">
                        <span className="profile-k">text_len</span>
                        <span className="profile-v">{c.sentiment?.text_len ?? 0}</span>
                        <span className="profile-k">pages</span>
                        <span className="profile-v">{c.sentiment?.num_pages_total ?? 0}</span>
                      </div>

                      <div className="profile-card-row">
                        <span className="profile-k">polarity</span>
                        <span className="profile-v">{(c.sentiment?.polarity ?? 0).toFixed(3)}</span>
                        <span className="profile-k">subjectivity</span>
                        <span className="profile-v">{(c.sentiment?.subjectivity ?? 0).toFixed(3)}</span>
                      </div>

                      <div className="profile-card-row">
                        <span className="profile-k">intel findings</span>
                        <span className="profile-v">{c.intelligence?.total_findings ?? 0}</span>
                        <span className="profile-k">WASP fit</span>
                        <span className="profile-v">{c.attributes?.avg_wasp_fit_score ?? "-"}</span>
                      </div>

                      {(c.attributes?.primary_ship_types || []).length > 0 ? (
                        <div className="profile-tags">
                          {(c.attributes.primary_ship_types || []).slice(0, 3).map((t) => (
                            <span className="profile-tag" key={t}>{t}</span>
                          ))}
                        </div>
                      ) : null}

                      {c.wikipedia?.summary ? (
                        <div className="profile-summary">
                          {c.wikipedia.summary}
                        </div>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </motion.div>

        {/* ---------- STATS CARDS ---------- */}

        <div className="intel-stats-grid">
          {[
            {
              label: "Total Companies",
              value: stats.total_companies,
              sub: "With intelligence data"
            },
            {
              label: "Total Findings",
              value: stats.total_findings,
              sub: "Across all categories"
            },
            {
              label: "Avg per Company",
              value: stats.avg_findings_per_company,
              sub: "Intelligence findings"
            },
            {
              label: "Datasets",
              value: datasets.length,
              sub: "Available downloads"
            }
          ].map((card, i) => (
            <motion.div
              key={i}
              className="intel-stat-card"
              initial={{ opacity: 0, y: 25 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: i * 0.08 }}
              whileHover={{
                y: -4,
                boxShadow: "0 20px 45px rgba(15,23,42,0.12)"
              }}
            >
              <h3>{card.label}</h3>
              <div className="intel-stat-value">{card.value}</div>
              <div className="intel-stat-label">{card.sub}</div>
            </motion.div>
          ))}
        </div>

        {/* ---------- SCRAPER STATUS ---------- */}

        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="intel-section-title">🚀 Live Scraper Status</div>

          <div className="intel-scraper-grid">

            {/* Intelligence scraper */}
            <motion.div
              className="scraper-box"
              whileHover={{ y: -4, boxShadow: "0 16px 40px rgba(15,23,42,0.12)" }}
              transition={{ duration: 0.2 }}
            >
              <div className="scraper-header">
                <h3>🕵️ Intelligence Scraper</h3>
                <span
                  className={
                    "scraper-status " +
                    (scraperStatus.intelligence.running ? "running" : "idle")
                  }
                >
                  ●
                </span>
              </div>

              <div className="scraper-body">
                <div className="scraper-info">
                  <span>Current Company:</span>
                  <span>{scraperStatus.intelligence.current_company || "-"}</span>
                </div>

                <div className="scraper-info">
                  <span>Progress:</span>
                  <span>
                    {scraperStatus.intelligence.companies_processed} /{" "}
                    {scraperStatus.intelligence.total_companies}
                  </span>
                </div>

                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${scraperStatus.intelligence.progress || 0}%`
                    }}
                  ></div>
                </div>

                <div className="scraper-info">
                  <span>Findings:</span>
                  <span>{scraperStatus.intelligence.findings_count || 0}</span>
                </div>
              </div>
            </motion.div>

            {/* Profiler scraper */}
            <motion.div
              className="scraper-box"
              whileHover={{ y: -4, boxShadow: "0 16px 40px rgba(15,23,42,0.12)" }}
              transition={{ duration: 0.2 }}
            >
              <div className="scraper-header">
                <h3>📊 Company Profiler</h3>
                <span
                  className={
                    "scraper-status " +
                    (scraperStatus.profiler.running ? "running" : "idle")
                  }
                >
                  ●
                </span>
              </div>

              <div className="scraper-body">
                <div className="scraper-info">
                  <span>Current Company:</span>
                  <span>{scraperStatus.profiler.current_company || "-"}</span>
                </div>

                <div className="scraper-info">
                  <span>Progress:</span>
                  <span>
                    {scraperStatus.profiler.companies_processed} /{" "}
                    {scraperStatus.profiler.total_companies}
                  </span>
                </div>

                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${scraperStatus.profiler.progress || 0}%`
                    }}
                  ></div>
                </div>

                <div className="scraper-info">
                  <span>Profiles:</span>
                  <span>{scraperStatus.profiler.profiles_count || 0}</span>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* ---------- CATEGORIES ---------- */}

        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="intel-section-title">📊 Intelligence by Category</div>

          {stats.total_findings === 0 ? (
            <div className="empty-state">📭 No intelligence data</div>
          ) : (
            Object.entries(stats.categories).map(([key, count]) => {
              const pct = stats.total_findings
                ? ((count / stats.total_findings) * 100).toFixed(1)
                : 0;

              return (
                <motion.div
                  className="category-bar"
                  key={key}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4 }}
                >
                  <div className="category-label">
                    {CATEGORY_NAMES[key] || key}
                  </div>

                  <div className="category-progress">
                    <div
                      className="category-fill"
                      style={{ width: `${pct}%` }}
                    >
                      <span className="category-count">{count}</span>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </motion.div>

        {/* ---------- TOP COMPANIES ---------- */}

        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="intel-section-title">🏆 Top Companies</div>

          {stats.top_companies.length === 0 ? (
            <div className="empty-state">No companies available</div>
          ) : (
            stats.top_companies.map((company, i) => (
              <motion.div
                className="company-row"
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
              >
                <div>
                  <span className="company-rank">{i + 1}.</span>
                  <span className="company-name">{company.name}</span>
                  <span className="fleet-size">
                    ({company.fleet_size} vessels)
                  </span>
                </div>
                <span className="company-findings">
                  {company.findings} findings
                </span>
              </motion.div>
            ))
          )}
        </motion.div>

        {/* ---------- DATASETS ---------- */}

        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="intel-section-title">📥 Available Datasets</div>

          {datasets.length === 0 ? (
            <div className="empty-state">📂 No datasets available</div>
          ) : (
            datasets.map((d, i) => (
              <motion.div
                key={i}
                className="dataset-item"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: i * 0.05 }}
                whileHover={{ scale: 1.015, y: -2 }}
              >
                <div className="dataset-info">
                  <h4>{d.filename}</h4>
                  <div className="dataset-meta">
                    <span>📅 {new Date(d.modified).toLocaleString()}</span>
                    <span>💾 {d.size_mb} MB</span>
                    <span>🏢 {d.companies} companies</span>
                    <span>🔍 {d.findings} findings</span>
                  </div>
                </div>

                <button
                  className="download-btn"
                  onClick={() =>
                    (window.location.href = `/ships/api/intelligence/download/${d.filename}`)
                  }
                >
                  📥 Download
                </button>
              </motion.div>
            ))
          )}
        </motion.div>

      </div>
    </div>
  );
}

function zscore(values) {
  const arr = values.map((v) => (Number.isFinite(v) ? v : 0));
  const mean = arr.reduce((a, b) => a + b, 0) / (arr.length || 1);
  const variance =
    arr.reduce((a, b) => a + (b - mean) * (b - mean), 0) / (arr.length || 1);
  const std = Math.sqrt(variance);
  if (!std) return arr.map(() => 0);
  return arr.map((v) => (v - mean) / std);
}

function SentimentScatter({ companies }) {
  const pts = (companies || [])
    .filter((c) => (c?.sentiment?.text_len || 0) > 0)
    .slice(0, 40);

  if (pts.length === 0) {
    return <div className="empty-state">No scraped website text yet</div>;
  }

  const pol = pts.map((c) => Number(c.sentiment?.polarity ?? 0));
  const sub = pts.map((c) => Number(c.sentiment?.subjectivity ?? 0));
  const tl = pts.map((c) => Math.log1p(Number(c.sentiment?.text_len ?? 0)));

  const polZ = zscore(pol);
  const subZ = zscore(sub);
  const tlZ = zscore(tl);

  const W = 420;
  const H = 260;
  const pad = 26;

  const xMin = -3, xMax = 3;
  const yMin = -3, yMax = 3;

  const xScale = (x) => pad + ((x - xMin) / (xMax - xMin)) * (W - pad * 2);
  const yScale = (y) => H - pad - ((y - yMin) / (yMax - yMin)) * (H - pad * 2);

  return (
    <svg className="sentiment-scatter" width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      {/* axes */}
      <line x1={pad} y1={H / 2} x2={W - pad} y2={H / 2} stroke="#cbd5e1" />
      <line x1={W / 2} y1={pad} x2={W / 2} y2={H - pad} stroke="#cbd5e1" />
      {pts.map((c, i) => {
        const r = 5 + Math.max(0, tlZ[i]) * 4;
        const cx = xScale(polZ[i]);
        const cy = yScale(subZ[i]);
        return (
          <g key={c.company_name}>
            <circle cx={cx} cy={cy} r={r} fill="#0ea5e9" opacity="0.75" />
            <title>
              {`${c.company_name}\npolarity_z=${polZ[i].toFixed(2)} subjectivity_z=${subZ[i].toFixed(2)} text_len=${c.sentiment?.text_len ?? 0}`}
            </title>
          </g>
        );
      })}
    </svg>
  );
}
