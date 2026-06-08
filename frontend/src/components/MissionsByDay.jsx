/**
 * @package   EGI-STAT/frontend/components
 * @author    Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
 * @version   1.0.0 (FlorenceEGI — EGI-STAT, M-245)
 * @date      2026-06-08
 * @purpose   Vista mission giorno-per-giorno: grafico giornaliero filtrabile per
 *            MESE + tabella giorno × ORGANO. Mostra TUTTA la produzione di tutti
 *            gli organi (os3-matrix, FORTINO, oracode/Fucina, ...) attribuita al
 *            giorno di chiusura. Risolve il "vedo solo l'aggregato settimanale":
 *            qui si legge il dettaglio per giorno e per organo.
 *            Sorgente: /api/v2/stats/missions_by_day.
 */
import React, { useState, useEffect, useMemo } from 'react';
import AdminChart from './AdminChart';
import { CalendarDays } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
const MONTHS_IT = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'];

function monthLabel(ym) {
  const [y, m] = ym.split('-');
  return `${MONTHS_IT[parseInt(m, 10) - 1]} ${y}`;
}

export default function MissionsByDay() {
  const [data, setData] = useState(null);
  const [month, setMonth] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v2/stats/missions_by_day`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && d.days) setData(d); })
      .catch((e) => console.error('missions_by_day fetch failed', e));
  }, []);

  const months = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.days.map((d) => d.date.slice(0, 7)))].sort().reverse();
  }, [data]);

  if (!data) return null;

  // Mese selezionato: stato esplicito, con fallback al più recente (no setState-in-effect).
  const selectedMonth = month || months[0] || '';
  const monthDays = data.days.filter((d) => d.date.startsWith(selectedMonth));
  // Grafico: giorni del mese in ordine crescente; X = giorno del mese.
  const chartData = [...monthDays]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({ name: d.date.slice(8, 10), total: d.total }));
  // Colonne = organi con almeno una mission nel mese (ordine globale per totale).
  const organsInMonth = data.organs.filter((o) => monthDays.some((d) => d.by_organ[o]?.length));
  const organTotals = {};
  organsInMonth.forEach((o) => {
    organTotals[o] = monthDays.reduce((s, d) => s + (d.by_organ[o]?.length || 0), 0);
  });
  const monthTotal = monthDays.reduce((s, d) => s + d.total, 0);

  const th = { padding: '8px 10px', textAlign: 'center', whiteSpace: 'nowrap' };
  const stick = { position: 'sticky', left: 0, background: '#1a1a1a' };

  return (
    <div className="chart-card glass-panel" style={{ gridColumn: '1 / -1' }}>
      <div className="card-header">
        <div className="icon-box accent"><CalendarDays /></div>
        <h2>Mission per Giorno — {selectedMonth ? monthLabel(selectedMonth) : ''}</h2>
        <select
          aria-label="Seleziona mese"
          value={selectedMonth}
          onChange={(e) => setMonth(e.target.value)}
          style={{ marginLeft: 'auto', background: '#1e1e1e', color: '#fff', border: '1px solid #444', borderRadius: 6, padding: '6px 10px' }}
        >
          {months.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
        </select>
      </div>

      <AdminChart data={chartData} dataKey="total" yLabel="Mission" color="#000000" scrollable={true} />

      <div style={{ overflowX: 'auto', marginTop: 20 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #444' }}>
              <th style={{ ...th, ...stick, textAlign: 'left' }}>Giorno</th>
              {organsInMonth.map((o) => <th key={o} style={th}>{o}</th>)}
              <th style={{ ...th, fontWeight: 'bold' }}>Tot</th>
            </tr>
          </thead>
          <tbody>
            {monthDays.map((d) => (
              <tr key={d.date} style={{ borderBottom: '1px solid #2a2a2a' }}>
                <td style={{ ...th, ...stick, textAlign: 'left' }}>{d.date}</td>
                {organsInMonth.map((o) => {
                  const ids = d.by_organ[o] || [];
                  return (
                    <td key={o} style={{ ...th, color: ids.length ? '#00cec9' : '#444' }} title={ids.join(', ')}>
                      {ids.length || '·'}
                    </td>
                  );
                })}
                <td style={{ ...th, fontWeight: 'bold' }}>{d.total}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ borderTop: '2px solid #444', fontWeight: 'bold' }}>
              <td style={{ ...th, ...stick, textAlign: 'left' }}>Totale</td>
              {organsInMonth.map((o) => <td key={o} style={th}>{organTotals[o]}</td>)}
              <td style={th}>{monthTotal}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
