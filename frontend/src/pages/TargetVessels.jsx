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



export default function TargetVessels() {
//api call
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
      const mlRows = await loadCSV("/data/company_adoption_scores.csv");

      // 3. Build company → social score map
      const companyScoreMap = Object.fromEntries(
        mlRows.map(row => [
          row.Company?.trim(),
          Number(row["Adoption Score"]),
        ])
      );

      // 4. Combine vessel + company scores
      const combinedVessels = techRows.map(row => {
        const company = row.Company?.trim() || null;

        return {
          mmsi: row.MMSI,
          name: row.Name,
          length: row.Length ? Number(row.Length) : null,
          flag_state: row.Flag,
          signatory_company: company,
          co2: row.CO2 ? Number(row.CO2) : null,
          technical_fit_score: row["Technical Fit"]
            ? Number(row["Technical Fit"])
            : null,
          company_adoption_score: company
            ? companyScoreMap[company] ?? null
            : null,
        };
      });

      setVessels(combinedVessels);
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

        <section className="tv-shell container">
            <div className="tv-panel glass">
                <h2 className="tv-section-title">Ranked target vessels</h2>

                <div className="tv-table">
                <div className="tv-row tv-header">
                    <span>#</span>
                    <span>Vessel</span>
                    <span>Company</span>
                    <span>Combined</span>
                    <span>Social</span>
                    <span>Technical</span>
                </div>

                {loading ? (
                    <div className="tv-placeholder">
                        <div className="tv-skeleton-row" />
                        <div className="tv-skeleton-row" />
                        <div className="tv-skeleton-row" />
                    </div>
                    ) : error ? (
                    <p className="tv-note">Failed to load vessels: {error}</p>
                    ) : rankedVessels.length === 0 ? (
                    <p className="tv-note">
                        No vessels available in the current environment.
                        <br />
                        <span className="tv-note-subtle">
                        This table will populate automatically when the production database is connected.
                        </span>
                    </p>
                    ) : (
                    rankedVessels.map((vessel, i) => (
                        <div key={vessel.mmsi ?? `${vessel.name}-${i}`} className={`tv-row ${i < 3 ? "top" : ""}`}>
                        <span className="tv-rank">#{i + 1}</span>

                        <span className="tv-vessel">
                            <strong>{vessel.name}</strong>
                            <small>
                            {vessel.length && ` · ${vessel.length} m`}
                            {vessel.flag_state && ` · ${vessel.flag_state}`}
                            </small>
                        </span>

                        <span className="tv-company">
                            {vessel.signatory_company ?? <em>Unknown</em>}
                        </span>

                        <span className="tv-score primary">
                            {vessel.combined_score == null ? "—" : vessel.combined_score.toFixed(1)}
                        </span>

                        <span className="tv-score">
                            {vessel.company_adoption_score == null
                            ? "—"
                            : vessel.company_adoption_score.toFixed(1)}
                        </span>

                        <span className="tv-score muted">
                            {vessel.technical_fit_score == null ? "—" : vessel.technical_fit_score.toFixed(1)}
                        </span>
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
