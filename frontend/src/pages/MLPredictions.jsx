import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import '../styles/Intelligence.css';

export default function MLPredictions() {
  const [predictions, setPredictions] = useState({});
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('all'); // all, wasp_high, sustainability_high
  const [sortBy, setSortBy] = useState('wasp_probability'); // wasp_probability, sustainability, company_name

  useEffect(() => {
    loadPredictions();
    loadStats();
  }, []);

  async function loadPredictions() {
    try {
      const res = await fetch('/ships/api/ml/predictions');
      const data = await res.json();
      setPredictions(data.predictions || {});
    } catch (err) {
      console.error('Error loading predictions:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      const res = await fetch('/ships/api/ml/stats');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  }

  async function trainModels() {
    if (!confirm('This will train ML models. This may take a few minutes. Continue?')) {
      return;
    }

    try {
      const res = await fetch('/ships/api/ml/train', { method: 'POST' });
      const data = await res.json();
      
      if (data.status === 'success') {
        alert(`✅ Models trained successfully!\n${data.models_trained.length} models\n${data.total_companies} companies`);
        loadPredictions();
        loadStats();
      } else {
        alert(`❌ Error: ${data.message}`);
      }
    } catch (err) {
      alert(`❌ Error training models: ${err.message}`);
    }
  }

  // Filter and sort predictions
  const filteredAndSorted = React.useMemo(() => {
    let filtered = Object.entries(predictions);

    // Apply filters
    if (filter === 'wasp_high') {
      filtered = filtered.filter(([_, pred]) => 
        pred.wasp_adoption?.prediction === true && 
        pred.wasp_adoption?.confidence === 'high'
      );
    } else if (filter === 'sustainability_high') {
      filtered = filtered.filter(([_, pred]) => 
        pred.sustainability_focus?.prediction === 'high'
      );
    }

    // Sort
    filtered.sort(([nameA, predA], [nameB, predB]) => {
      if (sortBy === 'wasp_probability') {
        const probA = predA.wasp_adoption?.probability || 0;
        const probB = predB.wasp_adoption?.probability || 0;
        return probB - probA;
      } else if (sortBy === 'sustainability') {
        const sustA = predA.sustainability_focus?.prediction || 'low';
        const sustB = predB.sustainability_focus?.prediction || 'low';
        const order = { 'high': 3, 'medium': 2, 'low': 1 };
        return (order[sustB] || 0) - (order[sustA] || 0);
      } else {
        return nameA.localeCompare(nameB);
      }
    });

    return filtered;
  }, [predictions, filter, sortBy]);

  if (loading) {
    return (
      <div className="intel-page">
        <div className="loading">Loading predictions...</div>
      </div>
    );
  }

  return (
    <div className="intel-page">
      <header className="intel-header">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          🤖 ML Predictions Dashboard
        </motion.h1>
        <p className="intel-subtitle">
          AI-powered predictions for WASP adoption, sustainability focus, and company classification
        </p>
      </header>

      <div className="intel-container">
        {/* Stats Cards */}
        <div className="intel-stats-grid">
          <motion.div
            className="intel-stat-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h3>Total Companies</h3>
            <div className="intel-stat-value">{Object.keys(predictions).length}</div>
            <div className="intel-stat-label">With predictions</div>
          </motion.div>

          <motion.div
            className="intel-stat-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h3>WASP Candidates</h3>
            <div className="intel-stat-value">
              {Object.values(predictions).filter(p => p.wasp_adoption?.prediction).length}
            </div>
            <div className="intel-stat-label">High probability</div>
          </motion.div>

          <motion.div
            className="intel-stat-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <h3>Sustainability Focus</h3>
            <div className="intel-stat-value">
              {Object.values(predictions).filter(p => p.sustainability_focus?.prediction === 'high').length}
            </div>
            <div className="intel-stat-label">High focus</div>
          </motion.div>

          <motion.div
            className="intel-stat-card"
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h3>Models Status</h3>
            <div className="intel-stat-value">
              {stats?.models_available ? '✅' : '❌'}
            </div>
            <div className="intel-stat-label">
              {stats?.models_available ? 'Trained' : 'Not trained'}
            </div>
          </motion.div>
        </div>

        {/* Controls */}
        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="intel-section-title">🔧 Controls</div>
          
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px' }}>
            <div>
              <label>Filter:</label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                style={{ marginLeft: '10px', padding: '8px' }}
              >
                <option value="all">All Companies</option>
                <option value="wasp_high">High WASP Probability</option>
                <option value="sustainability_high">High Sustainability Focus</option>
              </select>
            </div>

            <div>
              <label>Sort By:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                style={{ marginLeft: '10px', padding: '8px' }}
              >
                <option value="wasp_probability">WASP Probability</option>
                <option value="sustainability">Sustainability Level</option>
                <option value="company_name">Company Name</option>
              </select>
            </div>

            <button
              onClick={trainModels}
              style={{
                padding: '10px 20px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              🚀 Train Models
            </button>
          </div>
        </motion.div>

        {/* Predictions Table */}
        <motion.div
          className="intel-section"
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="intel-section-title">
            📊 Company Predictions ({filteredAndSorted.length} companies)
          </div>

          {filteredAndSorted.length === 0 ? (
            <div className="empty-state">
              {Object.keys(predictions).length === 0 
                ? 'No predictions available. Train models first.' 
                : 'No companies match the current filter.'}
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'rgba(0,0,0,0.05)' }}>
                    <th style={{ padding: '12px', textAlign: 'left' }}>Company</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>WASP Adoption</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Sustainability</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Company Type</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Key Features</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAndSorted.map(([companyName, pred], i) => (
                    <motion.tr
                      key={companyName}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.02 }}
                      style={{
                        borderBottom: '1px solid rgba(0,0,0,0.1)',
                        background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.02)'
                      }}
                    >
                      <td style={{ padding: '12px', fontWeight: 'bold' }}>
                        {companyName}
                      </td>
                      
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        {pred.wasp_adoption ? (
                          <div>
                            <div style={{
                              display: 'inline-block',
                              padding: '4px 12px',
                              borderRadius: '12px',
                              background: pred.wasp_adoption.prediction 
                                ? 'rgba(34, 197, 94, 0.2)' 
                                : 'rgba(239, 68, 68, 0.2)',
                              color: pred.wasp_adoption.prediction ? '#22c55e' : '#ef4444',
                              fontWeight: 'bold',
                              fontSize: '12px'
                            }}>
                              {pred.wasp_adoption.prediction ? '✅ YES' : '❌ NO'}
                            </div>
                            <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.7 }}>
                              {(pred.wasp_adoption.probability * 100).toFixed(0)}% ({pred.wasp_adoption.confidence})
                            </div>
                          </div>
                        ) : (
                          <span style={{ opacity: 0.5 }}>N/A</span>
                        )}
                      </td>

                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        {pred.sustainability_focus ? (
                          <div>
                            <div style={{
                              display: 'inline-block',
                              padding: '4px 12px',
                              borderRadius: '12px',
                              background: 
                                pred.sustainability_focus.prediction === 'high' ? 'rgba(34, 197, 94, 0.2)' :
                                pred.sustainability_focus.prediction === 'medium' ? 'rgba(251, 191, 36, 0.2)' :
                                'rgba(156, 163, 175, 0.2)',
                              color: 
                                pred.sustainability_focus.prediction === 'high' ? '#22c55e' :
                                pred.sustainability_focus.prediction === 'medium' ? '#fbbf24' :
                                '#9ca3af',
                              fontWeight: 'bold',
                              fontSize: '12px',
                              textTransform: 'uppercase'
                            }}>
                              {pred.sustainability_focus.prediction}
                            </div>
                            <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.7 }}>
                              {(pred.sustainability_focus.probability * 100).toFixed(0)}%
                            </div>
                          </div>
                        ) : (
                          <span style={{ opacity: 0.5 }}>N/A</span>
                        )}
                      </td>

                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        {pred.company_type ? (
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: '6px',
                            background: 'rgba(99, 102, 241, 0.1)',
                            color: '#6366f1',
                            fontSize: '12px',
                            textTransform: 'capitalize'
                          }}>
                            {pred.company_type.prediction.replace('_', ' ')}
                          </span>
                        ) : (
                          <span style={{ opacity: 0.5 }}>N/A</span>
                        )}
                      </td>

                      <td style={{ padding: '12px', fontSize: '11px' }}>
                        {pred.features && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {pred.features.vessel_count > 0 && (
                              <span>🚢 {pred.features.vessel_count} vessels</span>
                            )}
                            {pred.features.grants_count > 0 && (
                              <span>💰 {pred.features.grants_count} grants</span>
                            )}
                            {pred.features.sustainability_count > 0 && (
                              <span>🌱 {pred.features.sustainability_count} sustainability news</span>
                            )}
                            {pred.features.has_wind_keywords && (
                              <span>🌬️ Wind keywords found</span>
                            )}
                          </div>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

