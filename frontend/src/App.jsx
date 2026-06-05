import React, { useState, useEffect } from 'react';
import AdminChart from './components/AdminChart';
import DailyStats from './components/DailyStats';
import AddTimeModal from './components/AddTimeModal';
import { LayoutDashboard, TrendingUp, Brain, Target, GitCommit, FileCode, Activity } from 'lucide-react';
import './item.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

function App() {
  const [allStats, setAllStats] = useState([]);
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(12);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v2/stats/weekly?limit=1000`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const chartData = data.map(row => ({
              name: row.period,
              pi: Math.round(row.avg_productivity_index * 10) / 10,
              cl: Math.round(row.avg_cognitive_load * 100) / 100,
              missions: row.missions_closed,
              weighted: Math.round(row.weighted_commits * 10) / 10,
              lines_net: row.lines_net,
              files: row.files_touched,
            }));
            setAllStats(chartData);
            setStats(chartData.slice(-12));
          }
        }
      } catch (error) {
        console.error("Failed to fetch stats:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Anni disponibili dai dati (period = "YYYY-Www") — M-OS3-083: filtro per-anno sulla storia 2023→oggi
  const years = [...new Set(allStats.map(s => String(s.name).slice(0, 4)))].sort();

  const handleTimeRange = (weeks) => {
    setTimeRange(weeks);
    if (weeks === 'all') {
      setStats(allStats);
    } else if (typeof weeks === 'string' && /^\d{4}$/.test(weeks)) {
      // filtro per anno: tutte le settimane di quell'anno
      setStats(allStats.filter(s => String(s.name).startsWith(weeks)));
    } else {
      setStats(allStats.slice(-weeks));
    }
  };

  return (
    <div className="dashboard-container">
      <header className="glass-header">
        <div className="logo-section">
          <div className="logo-icon"><LayoutDashboard color="white" /></div>
          <h1>EGI Analytics <span className="version">v2.0</span></h1>
        </div>
        <div className="status-badge">
          <span className="dot online"></span> Mission-Driven Stats
        </div>
      </header>

      <main className="main-content">
        <AddTimeModal />

        <div className="section-divider" style={{ margin: '40px 0', borderBottom: '1px solid #333' }}></div>

        <DailyStats active={true} />

        <div className="section-divider" style={{ margin: '40px 0', borderBottom: '1px solid #333' }}></div>

        <div className="filter-bar">
          <button className={`filter-btn ${timeRange === 6 ? 'active' : ''}`} onClick={() => handleTimeRange(6)}>
            6 Settimane
          </button>
          <button className={`filter-btn ${timeRange === 12 ? 'active' : ''}`} onClick={() => handleTimeRange(12)}>
            12 Settimane
          </button>
          <button className={`filter-btn ${timeRange === 'all' ? 'active' : ''}`} onClick={() => handleTimeRange('all')}>
            Tutte
          </button>
          {years.map(y => (
            <button key={y} className={`filter-btn ${timeRange === y ? 'active' : ''}`} onClick={() => handleTimeRange(y)}>
              {y}
            </button>
          ))}
        </div>

        <div className="metrics-grid">
          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box primary"><TrendingUp /></div>
              <h2>Indice Produttività</h2>
            </div>
            <AdminChart data={stats} dataKey="pi" yLabel="PI" color="#000000" scrollable={true} />
          </div>

          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box secondary"><Brain /></div>
              <h2>Carico Cognitivo Medio</h2>
            </div>
            <AdminChart data={stats} dataKey="cl" yLabel="CL" color="#000000" scrollable={true} />
          </div>

          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box accent"><Target /></div>
              <h2>Mission Chiuse</h2>
            </div>
            <AdminChart data={stats} dataKey="missions" yLabel="N" color="#000000" scrollable={true} />
          </div>

          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box primary"><GitCommit /></div>
              <h2>Commit Pesati</h2>
            </div>
            <AdminChart data={stats} dataKey="weighted" yLabel="W" color="#000000" scrollable={true} />
          </div>

          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box secondary"><FileCode /></div>
              <h2>Righe Nette</h2>
            </div>
            <AdminChart data={stats} dataKey="lines_net" yLabel="Net" color="#000000" scrollable={true} />
          </div>

          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box accent"><Activity /></div>
              <h2>File Toccati</h2>
            </div>
            <AdminChart data={stats} dataKey="files" yLabel="Files" color="#000000" scrollable={true} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
