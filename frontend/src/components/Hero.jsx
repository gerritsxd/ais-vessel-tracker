// Hero.jsx
import { motion } from "framer-motion";
import "../styles/Hero.css";
import { useNavigate } from "react-router-dom";


export default function Hero() {
  const navigate = useNavigate();

  return (
    
  <section className="hero">


  {/* WIND BACKGROUND LAYER */}
  <div className="hero-wind-lines">
    <svg viewBox="0 0 1200 600" preserveAspectRatio="none">
      <path d="M0 120 C 300 100, 500 200, 900 160" />
      <path d="M0 220 C 320 240, 520 160, 920 200" />
      <path d="M0 320 C 280 300, 480 380, 900 340" />
    </svg>
  </div>

  {/* CONTENT LAYER */}
  <div className="container hero-inner">
    <div className="hero-layout">

      {/* LEFT */}
      <div>
        <motion.h1
          className="hero-title"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        >
          Turning wind into{" "}
          <span className="accent-text">measurable carbon reduction</span>
        </motion.h1>

        <motion.p
          className="hero-subtitle"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          AI-powered customer identification and emissions intelligence for
          wind-assisted shipping.
        </motion.p>

        <div className="hero-actions">
        <button
          className="btn btn-primary motion"
          onClick={() => navigate("/target-vessels")}
        >
          Explore platform
        </button>

        <button
          className="btn glass btn-secondary motion"
          onClick={() => navigate("/ML-insights")}
        >
          View methodology
        </button>
      </div>

        <p className="hero-proof">
          Built on live AIS data · Trained on global vessel activity
        </p>
      </div>

      {/* RIGHT */}
      <div className="hero-kpis">
        {[
          ["12,327", "Vessels tracked"],
          ["145M", "CO₂ modelled (t)"],
          ["5,784", "Matched prospects"],
          ["0.84", "Avg ML confidence"],
        ].map(([value, label], index) => (
          <motion.div
            key={label}
            className="glass motion hero-kpi"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ y: -6 }}
            transition={{
              delay: index * 0.15 + 0.4,
              duration: 0.7,
              ease: "easeOut",
            }}
          >
            <div className="hero-kpi-value">{value}</div>
            <div className="hero-kpi-label">{label}</div>
          </motion.div>
        ))}
      </div>
    </div>

  </div>
</section>

  );
}
