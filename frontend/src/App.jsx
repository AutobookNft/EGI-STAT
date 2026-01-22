import React, { useState, useEffect } from 'react';
import AdminChart from './components/AdminChart';
import DailyStats from './components/DailyStats';
import { LayoutDashboard, RefreshCcw, Calendar, GitCommit } from 'lucide-react';
import './item.css';

function App() {
  const [allStats, setAllStats] = useState([]);
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(12); // Default: 12 weeks

  // Fetch data from Python Backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/stats/weekly');
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const chartData = data.map(row => ({
              name: `W${row.week}-${row.year}`,
              pi: row.productivity_score,
              weighted: row.metrics?.weighted_commits || 0,
              lines: row.metrics?.lines_touched || 0,
              total: row.metrics?.total_commits || 0
            }));
            const sorted = chartData.reverse(); // Chronological
            setAllStats(sorted);
            setStats(sorted.slice(-12)); // Default 12 weeks
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

  // Handle time range change
  const handleTimeRange = (weeks) => {
    setTimeRange(weeks);
    if (weeks === 'all') {
      setStats(allStats);
    } else {
      setStats(allStats.slice(-weeks));
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="glass-header">
        <div className="logo-section">
          <div className="logo-icon"><LayoutDashboard color="white" /></div>
          <h1>EGI Analytics <span className="version">v8.0</span></h1>
        </div>
        <div className="status-badge">
          <span className="dot online"></span> System Active
        </div>
      </header>

      <main className="main-content">
        {/* Daily Stats Overview (New) */}
        <DailyStats active={true} />

        <div className="section-divider" style={{ margin: '40px 0', borderBottom: '1px solid #333' }}></div>
        {/* Time Range Filter */}
        <div className="filter-bar">
          <button
            className={`filter-btn ${timeRange === 6 ? 'active' : ''}`}
            onClick={() => handleTimeRange(6)}
          >
            6 Settimane
          </button>
          <button
            className={`filter-btn ${timeRange === 12 ? 'active' : ''}`}
            onClick={() => handleTimeRange(12)}
          >
            12 Settimane
          </button>
          <button
            className={`filter-btn ${timeRange === 'all' ? 'active' : ''}`}
            onClick={() => handleTimeRange('all')}
          >
            Tutte
          </button>
        </div>

        <div className="metrics-grid">
          {/* Card 1: Productivity Index */}
          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box primary"><GitCommit /></div>
              <h2>Productivity Index (Settimanale)</h2>
            </div>
            <AdminChart
              data={stats}
              dataKey="pi"
              title=""
              yLabel="Score"
              color="#000000"
              scrollable={true}
            />
          </div>

          {/* Card 2: Weighted Commits */}
          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box secondary"><Calendar /></div>
              <h2>Commits Pesati</h2>
            </div>
            <AdminChart
              data={stats}
              dataKey="weighted"
              title=""
              yLabel="Weighted"
              color="#000000"
              scrollable={true}
            />
          </div>

          {/* Card 3: Lines Touched */}
          <div className="chart-card glass-panel">
            <div className="card-header">
              <div className="icon-box accent"><RefreshCcw /></div>
              <h2>Righe Toccate (Volume)</h2>
            </div>
            <AdminChart
              data={stats}
              dataKey="lines"
              title=""
              yLabel="Lines"
              color="#000000"
              scrollable={true}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
