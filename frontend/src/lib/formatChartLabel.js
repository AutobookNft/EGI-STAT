/**
 * @package   EGI-STAT/frontend/lib
 * @author    Padmin D. Curtis (AI) for Fabio Cherici
 * @version   1.0.0 (EGI-STAT)
 * @date      2026-06-07
 * @purpose   Formatta la label sopra i punti dei grafici AdminChart.
 *            I valori frazionari (Carico Cognitivo, Indice Produttività, Commit Pesati)
 *            devono mostrare almeno un decimale: prima Math.round collassava 2.4 in "2"
 *            rendendo tutti i punti uguali a occhio (bug M-242). I conteggi interi
 *            (missions, files) restano interi per non sporcare la label.
 */

/**
 * @param {number|*} v valore del punto. Se non numerico viene restituito invariato.
 * @returns {string|*} stringa localizzata: intero per i conteggi, 1–2 decimali per i frazionari.
 */
export function formatChartLabel(v) {
    if (typeof v !== 'number') return v;
    if (Number.isInteger(v)) return v.toLocaleString();
    return v.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 });
}
