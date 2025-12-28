import { motion } from "framer-motion";
import "../styles/TargetVessels.css";
import { useEffect, useState } from "react";

import { loadCSV } from "../utils/loadCSV";


function computeCombinedScore(companyScore, techScore) {
  if (companyScore == null && techScore == null) return null;
  if (techScore == null) return companyScore * 0.6;
  if (companyScore == null) return techScore * 0.6;
  return 0.5 * companyScore + 0.5 * techScore;
}

function normalizeCompany(name) {
  if (!name) return null;
  return name
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .replace(/\b(ltd|inc|ag|sa|nv|bv|plc)\b/g, "")
    .trim();
}



export default function TargetVessels() {
const [vessels, setVessels] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  async function loadData() {
    try {
      setLoading(true);

      // 1. Load technical-fit vessels
      const techRows = await loadCSV("/data/technical_fit_ships.csv");

      // 2. Load ML company adoption scores
      const mlRows = await loadCSV("/data/companies_with_waps_score.csv");

      // 3. Build company → social score map
      const companyScoreMap = Object.fromEntries(
        mlRows
          .filter(row => row.company_name)
          .map(row => [
            normalizeCompany(row.company_name),
            {
              socialScore: Number(row.waps_score_percentile),
              isAdopter:
                row.waps_adopted === "1" ||
                row.waps_adopted === 1,
            },
          ])
      );

      console.log("Company score keys:", Object.keys(companyScoreMap).slice(0, 10));




      // 4. Combine vessel + company scores
      const combinedVessels = techRows.map(row => {
        const companyRaw =
          row.Company && row.Company.trim() !== "" ? row.Company.trim() : null;

        const company = normalizeCompany(companyRaw);

        return {
          mmsi: row.MMSI,
          name: row.Name,
          ship_type: row.Type, // now a STRING like "Cargo"
          length: row.Length ? Number(row.Length) : null,
          flag_state: row.Flag || null,
          signatory_company: companyRaw,
          co2: row.CO2 ? Number(row.CO2) : null,
          technical_fit_score:
            row["Technical Fit"] !== undefined && row["Technical Fit"] !== ""
              ? Number(row["Technical Fit"])
              : null,
          company_adoption_score:
            company && companyScoreMap[company]
              ? companyScoreMap[company].socialScore
              : null,
          waps_adopted:
            company && companyScoreMap[company]
              ? companyScoreMap[company].isAdopter
              : false,
        };
      });

          const mlCoveredVessels = combinedVessels.filter(
      v => v.company_adoption_score != null
    );

    setVessels(mlCoveredVessels);

      console.table(
  combinedVessels.slice(0, 5).map(v => ({
    name: v.name,
    company: v.signatory_company,
    social: v.company_adoption_score,
    technical: v.technical_fit_score,
  }))
);

    } catch (err) {
      console.error(err);
      setError("Failed to load vessel data");
    } finally {
      setLoading(false);
    }
  }

  loadData();
}, []);


const rankedVessels = vessels
  .map(v => ({
    ...v,
    combined_score: computeCombinedScore(
      v.company_adoption_score,
      v.technical_fit_score
    ),
  }))
  .sort((a, b) => (b.combined_score ?? -1) - (a.combined_score ?? -1));





  return (
    <div className="tv-page">
      <section className="tv-hero container">
        <motion.h1
          className="tv-title"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          Customer identification:{" "}
          <span className="accent-text">target vessels</span>
        </motion.h1>

        <motion.p
          className="tv-subtitle"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.7 }}
        >
          This page will combine company-level adoption readiness (social ML) with
          vessel-level technical fit to rank the highest-potential candidates.
        </motion.p>

        <section className="tv-shell tv-wide">
            <div className="tv-panel glass">
                <h2 className="tv-section-title">Ranked target vessels</h2>

              <div className="tv-cards">
                {loading ? (
                  <div className="tv-placeholder">
                    <div className="tv-skeleton-card" />
                    <div className="tv-skeleton-card" />
                    <div className="tv-skeleton-card" />
                  </div>
                ) : error ? (
                  <p className="tv-note">Failed to load vessels: {error}</p>
                ) : rankedVessels.length === 0 ? (
                  <p className="tv-note">
                    No vessels match the current ML coverage.
                    <br />
                    <span className="tv-note-subtle">
                      This view only displays ships belonging to companies included in the social adoption analysis.
                    </span>
                  </p>
                ) : (
                  rankedVessels.map((vessel, i) => (
                    <div key={vessel.mmsi ?? `${vessel.name}-${i}`} className={`tv-card ${i < 3 ? "top" : ""}`}>
                      <div className="tv-card-left">
                        <div className="tv-card-title">
                          <span className="tv-rank-pill">#{i + 1}</span>
                          <span className="tv-vessel-name">{vessel.name}</span>
                        </div>

                        <div className="tv-card-meta">
                          <span className="tv-meta-item">{vessel.ship_type ?? "Unknown type"}</span>
                          {vessel.length && <span className="tv-meta-item">{vessel.length} m</span>}
                          {vessel.flag_state && <span className="tv-meta-item">{vessel.flag_state}</span>}
                          <span className="tv-meta-item">MMSI {vessel.mmsi}</span>
                        </div>

                        <div className="tv-card-company">
                          <span className="tv-company-label">Company</span>
                          <span className="tv-company-name">{vessel.signatory_company}</span>

                          {vessel.waps_adopted ? (
                            <span
                              className="tv-tag adopted"
                              title="Company has adopted wind-assisted propulsion (WAPS). This does not mean this specific vessel has sails."
                            >
                              Company adopted WAPS
                            </span>
                          ) : (
                            <span
                              className="tv-tag candidate"
                              title="Company has not adopted wind-assisted propulsion (WAPS) yet."
                            >
                              Company not adopted
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="tv-card-right">
                        <div className="tv-score-block">
                          <span className="tv-score-label">Combined</span>
                          <span className="tv-score-value primary">
                            {vessel.combined_score == null ? "—" : vessel.combined_score.toFixed(1)}
                          </span>
                        </div>

                        <div className="tv-score-split">
                          <div className="tv-score-block">
                            <span className="tv-score-label">Social</span>
                            <span className="tv-score-value">
                              {vessel.company_adoption_score == null ? "—" : vessel.company_adoption_score.toFixed(1)}
                            </span>
                          </div>

                          <div className="tv-score-block">
                            <span className="tv-score-label">Technical</span>
                            <span className="tv-score-value muted">
                              {vessel.technical_fit_score == null ? "—" : vessel.technical_fit_score.toFixed(1)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

            </div>
            </section>

      </section>
    </div>
  );
}
