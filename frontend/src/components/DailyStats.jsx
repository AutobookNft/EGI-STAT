import React, { useState, useEffect } from 'react';

export default function DailyStats({ active }) {
    // Default to today
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (selectedDate) {
            fetchData(selectedDate);
        }
    }, [selectedDate]);

    const fetchData = async (date) => {
        setLoading(true);
        try {
            const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/stats/daily_detail?date=${date}`);
            const json = await res.json();
            if (res.ok) {
                setData(json);
            } else {
                console.error("Failed to fetch daily stats", json);
                setData(null);
            }
        } catch (e) {
            console.error("Network error", e);
            setData(null);
        } finally {
            setLoading(false);
        }
    };

    if (!active) return null;

    return (
        <div className="daily-stats-container" style={{ padding: '20px', color: '#fff' }}>
            <div className="header-controls" style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '15px' }}>
                <h2 style={{ margin: 0 }}>📅 Daily Snapshot</h2>
                <input
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    style={{
                        background: '#1a1a1a',
                        border: '1px solid #333',
                        color: 'white',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        fontSize: '1rem',
                        fontFamily: 'inherit'
                    }}
                />
            </div>

            {loading && <div>Loading data...</div>}

            {!loading && !data && <div>No data found for this date.</div>}

            {!loading && data && data.summary && (
                <div className="stats-grid" style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '20px',
                    marginBottom: '30px'
                }}>
                    <StatCard
                        label="Tipo Giornata"
                        value={data.summary.day_type}
                        icon={data.summary.day_type_icon}
                        type={data.summary.day_type}
                        color="#a29bfe"
                    />
                    <StatCard
                        label="Righe Nette (Saldo)"
                        value={data.summary.net_lines > 0 ? `+${data.summary.net_lines}` : data.summary.net_lines}
                        unit="righe"
                        color="#2ecc71"
                        icon="📉"
                    />
                    <StatCard
                        label="Indice Produttività (Output)"
                        value={data.summary.productivity_score.toFixed(2)}
                        unit="pti"
                        color="#00cec9"
                    />
                    <StatCard
                        label="Carico Cognitivo (Complessità)"
                        value={data.summary.cognitive_load.toFixed(2)}
                        unit="/ 3.5"
                        color="#ff7675"
                    />
                    <StatCard
                        label="File Toccati (Volume)"
                        value={data.summary.files_touched}
                        icon="📂"
                        color="#fab1a0"
                    />
                    <StatCard
                        label="Ore Coding Stimate"
                        value={data.summary.coding_hours.toFixed(2)}
                        unit="h"
                        color="#fdcb6e"
                    />
                    <StatCard
                        label="Commit Pesati (Impatto)"
                        value={data.summary.weighted_commits.toFixed(2)}
                        icon="⚖️"
                        color="#dfe6e9"
                    />
                </div>
            )}

            {/* Repo Breakdown Table */}
            {!loading && data && data.repositories && data.repositories.length > 0 && (
                <div className="repo-breakdown" style={{ background: '#1e1e1e', padding: '20px', borderRadius: '12px' }}>
                    <h3 style={{ marginTop: 0 }}>Dettaglio Repository</h3>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid #333', color: '#888' }}>
                                <th style={{ padding: '10px' }}>Repo</th>
                                <th style={{ padding: '10px' }}>Tipo</th>
                                <th style={{ padding: '10px' }}>File</th>
                                <th style={{ padding: '10px' }}>Complessità (Load)</th>
                                <th style={{ padding: '10px' }}>Produttività (Score)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.repositories.map(repo => {
                                // Inline fallback logic since we are not in StatCard component
                                let displayIcon = repo.day_type_icon;
                                if (!displayIcon || displayIcon.includes('')) {
                                    switch (repo.day_type) {
                                        case 'FEATURE_DEV': displayIcon = '✨'; break;
                                        case 'BUG_FIXING': displayIcon = '🐞'; break;
                                        case 'REFACTOR': displayIcon = '🛠️'; break;
                                        case 'CHORE': displayIcon = '🧹'; break;
                                        case 'DOCS': displayIcon = '📝'; break;
                                        case 'MIXED': displayIcon = '🔀'; break;
                                        default: if (!displayIcon) displayIcon = '📊';
                                    }
                                }
                                return (
                                    <tr key={repo.repo_name} style={{ borderBottom: '1px solid #2a2a2a' }}>
                                        <td style={{ padding: '10px' }}>{repo.repo_name.replace('AutobookNft/', '')}</td>
                                        <td style={{ padding: '10px' }}>{displayIcon} {repo.day_type || 'N/A'}</td>
                                        <td style={{ padding: '10px' }}>{repo.files_touched}</td>
                                        <td style={{ padding: '10px' }}>{repo.cognitive_load.toFixed(2)}</td>
                                        <td style={{ padding: '10px', fontWeight: 'bold', color: '#00cec9' }}>{repo.productivity_score.toFixed(2)}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Metric Explanations (Legend) */}
            <div className="metrics-legend" style={{
                marginTop: '30px',
                background: 'rgba(255, 255, 255, 0.05)',
                padding: '20px',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
                <h3 style={{ marginTop: 0, marginBottom: '15px', color: '#ccc', fontSize: '1rem', textTransform: 'uppercase' }}>📖 Guida alle Metriche (Cosa significano?)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>

                    <div>
                        <strong style={{ color: '#00cec9' }}>Indice Produttività (Output)</strong>
                        <p style={{ margin: '5px 0', fontSize: '0.9rem', color: '#aaa' }}>
                            È un punteggio sintetico che combina il <strong>Volume</strong> (righe scritte) e l'<strong>Impatto</strong> (valore dei commit).
                            <br /><em>Esempio: Una feature completa vale più di 10 correzioni di typo.</em>
                        </p>
                    </div>

                    <div>
                        <strong style={{ color: '#ff7675' }}>Carico Cognitivo (Complessità)</strong>
                        <p style={{ margin: '5px 0', fontSize: '0.9rem', color: '#aaa' }}>
                            Misura lo <strong>sforzo mentale</strong> richiesto (scala 0 - 3.5). Calcolato in base a quanti file, moduli e righe hai dovuto gestire contemporaneamente.
                            <br /><em>Valori alti (&gt;2.5) indicano compiti difficili che richiedono molta concentrazione.</em>
                        </p>
                    </div>

                    <div>
                        <strong style={{ color: '#2ecc71' }}>Righe Nette (Saldo)</strong>
                        <p style={{ margin: '5px 0', fontSize: '0.9rem', color: '#aaa' }}>
                            La differenza tra righe aggiunte e rimosse. Un valore negativo è spesso positivo (Refactoring/Pulizia).
                        </p>
                    </div>

                </div>
            </div>

        </div>
    );
}

function StatCard({ label, value, icon, unit, color, type }) {
    // Fallback icon logic
    let displayIcon = icon;
    if (!displayIcon || displayIcon.includes('')) {
        switch (type) {
            case 'FEATURE_DEV': displayIcon = '✨'; break;
            case 'BUG_FIXING': displayIcon = '🐞'; break;
            case 'REFACTOR': displayIcon = '🛠️'; break;
            case 'CHORE': displayIcon = '🧹'; break;
            case 'DOCS': displayIcon = '📝'; break;
            case 'MIXED': displayIcon = '🔀'; break;
            default: if (!displayIcon) displayIcon = '📊';
        }
    }

    return (
        <div style={{
            background: '#1e1e1e',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
            borderTop: `4px solid ${color || '#fff'}`
        }}>
            <div style={{ fontSize: '2rem', marginBottom: '10px' }}>{displayIcon}</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: color || '#fff' }}>
                {value} <span style={{ fontSize: '1rem', color: '#888' }}>{unit}</span>
            </div>
            <div style={{ color: '#aaa', fontSize: '0.9rem', marginTop: '5px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                {label}
            </div>
        </div>
    );
}
