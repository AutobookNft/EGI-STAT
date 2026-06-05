import React, { useState, useEffect, useCallback } from 'react';

/*
 * AddTimeModal.jsx — Pannello "Ore per progetto" + modale "Aggiungi tempo" — M-237
 *
 * @author Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
 * Lato-scrittura dell'asse ORE: mostra GET /api/v2/stats/hours e, via modale,
 * POSTa una voce manuale a POST /api/v2/stats/time_entries. On-success ricarica
 * le ore (refresh dashboard). Project = select sulla whitelist (i nomi noti
 * arrivano dalle ore esistenti; fallback alla lista nota se vuota). Durata in
 * ore+minuti -> minutes totali (int>0). Validazione client + il backend e la
 * fonte di verita (whitelist + atomicita).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// Fallback whitelist (allineata a ~/oracode-engine/projects.json). Usata solo se
// l'endpoint /hours non ha ancora restituito progetti.
const FALLBACK_PROJECTS = ['Capasso', 'LeVespe', 'DeepDebug', 'FlorenceEGI', 'oracode'];

function todayISO() {
  return new Date().toISOString().split('T')[0];
}

export default function AddTimeModal() {
  const [hours, setHours] = useState([]);
  const [open, setOpen] = useState(false);

  const loadHours = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/stats/hours`);
      if (res.ok) {
        const json = await res.json();
        if (Array.isArray(json)) setHours(json);
      }
    } catch (e) {
      console.error('Failed to fetch hours', e);
    }
  }, []);

  useEffect(() => { loadHours(); }, [loadHours]);

  const knownProjects = hours.length
    ? hours.map((h) => h.project).filter(Boolean)
    : FALLBACK_PROJECTS;

  const onSaved = () => {
    setOpen(false);
    loadHours(); // ricarica le ore dopo il salvataggio (refresh dashboard)
  };

  return (
    <div className="hours-panel glass-panel" style={{ padding: '20px', borderRadius: '12px', background: '#1e1e1e', color: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h2 style={{ margin: 0 }}>⏱️ Ore per Progetto</h2>
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Aggiungi tempo"
          style={{
            background: '#00cec9', color: '#000', border: 'none', borderRadius: '6px',
            padding: '8px 16px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.95rem',
          }}
        >
          + Aggiungi tempo
        </button>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333', color: '#888' }}>
            <th style={{ padding: '8px' }}>Progetto</th>
            <th style={{ padding: '8px' }}>Ore</th>
            <th style={{ padding: '8px' }}>Min. manuali</th>
            <th style={{ padding: '8px' }}>Min. stima-commit</th>
            <th style={{ padding: '8px' }}>Righe nette</th>
          </tr>
        </thead>
        <tbody>
          {hours.map((h) => (
            <tr key={h.project} style={{ borderBottom: '1px solid #2a2a2a' }}>
              <td style={{ padding: '8px' }}>{h.project}</td>
              <td style={{ padding: '8px', fontWeight: 'bold', color: '#00cec9' }}>{h.hours}</td>
              <td style={{ padding: '8px' }}>{h.manual_minutes}</td>
              <td style={{ padding: '8px', color: '#888' }}>{h.commit_minutes}</td>
              <td style={{ padding: '8px', fontWeight: 'bold', color: '#a29bfe' }}>{(h.lines_net ?? 0).toLocaleString('it-IT')}</td>
            </tr>
          ))}
          {hours.length === 0 && (
            <tr><td colSpan={5} style={{ padding: '8px', color: '#888' }}>Nessuna voce ore.</td></tr>
          )}
        </tbody>
      </table>

      {open && (
        <TimeEntryForm projects={knownProjects} onClose={() => setOpen(false)} onSaved={onSaved} />
      )}
    </div>
  );
}

function TimeEntryForm({ projects, onClose, onSaved }) {
  const [project, setProject] = useState(projects[0] || '');
  const [date, setDate] = useState(todayISO());
  const [h, setH] = useState(0);
  const [m, setM] = useState(30);
  const [description, setDescription] = useState('');
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    const minutes = (parseInt(h, 10) || 0) * 60 + (parseInt(m, 10) || 0);
    if (minutes <= 0) { setError('La durata deve essere maggiore di zero.'); return; }
    if (!description.trim()) { setError('La descrizione è obbligatoria.'); return; }
    if (!project) { setError('Seleziona un progetto.'); return; }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v2/stats/time_entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project, date, minutes, description: description.trim() }),
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok) {
        onSaved();
      } else {
        setError(json.error || `Errore ${res.status}`);
      }
    } catch (err) {
      setError('Errore di rete.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Aggiungi tempo"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
        style={{
          background: '#1e1e1e', color: '#fff', padding: '24px', borderRadius: '12px',
          width: 'min(420px, 90vw)', display: 'flex', flexDirection: 'column', gap: '14px',
          border: '1px solid #333',
        }}
      >
        <h3 style={{ margin: 0 }}>Aggiungi tempo</h3>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ color: '#aaa', fontSize: '0.85rem' }}>Progetto</span>
          <select value={project} onChange={(e) => setProject(e.target.value)} style={inputStyle}>
            {projects.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ color: '#aaa', fontSize: '0.85rem' }}>Data</span>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={inputStyle} />
        </label>

        <div style={{ display: 'flex', gap: '10px' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
            <span style={{ color: '#aaa', fontSize: '0.85rem' }}>Ore</span>
            <input type="number" min="0" value={h} onChange={(e) => setH(e.target.value)} style={inputStyle} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
            <span style={{ color: '#aaa', fontSize: '0.85rem' }}>Minuti</span>
            <input type="number" min="0" max="59" value={m} onChange={(e) => setM(e.target.value)} style={inputStyle} />
          </label>
        </div>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ color: '#aaa', fontSize: '0.85rem' }}>Descrizione</span>
          <input
            type="text" value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="es. incontro cliente" style={inputStyle}
          />
        </label>

        {error && <div role="alert" style={{ color: '#ff7675', fontSize: '0.9rem' }}>{error}</div>}

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '6px' }}>
          <button type="button" onClick={onClose} style={btnSecondary}>Annulla</button>
          <button type="submit" disabled={saving} style={btnPrimary}>
            {saving ? 'Salvataggio…' : 'Salva'}
          </button>
        </div>
      </form>
    </div>
  );
}

const inputStyle = {
  background: '#111', border: '1px solid #333', color: '#fff',
  padding: '8px 10px', borderRadius: '6px', fontSize: '1rem', fontFamily: 'inherit',
};
const btnPrimary = {
  background: '#00cec9', color: '#000', border: 'none', borderRadius: '6px',
  padding: '8px 18px', fontWeight: 'bold', cursor: 'pointer',
};
const btnSecondary = {
  background: 'transparent', color: '#aaa', border: '1px solid #333',
  borderRadius: '6px', padding: '8px 18px', cursor: 'pointer',
};
