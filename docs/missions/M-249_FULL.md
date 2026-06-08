# M-249 — API stat no-store (esteso)

> Report esteso (FASE 6a). Tecnico: M-249.md.

## Contesto
Dopo i fix M-247/M-248/M-OS3-104 (stat coerenti lato backend) e l'attivazione dei servizi systemd, il CEO vedeva ancora la dashboard "rotta": charts mission-derivati (PI/CL/Mission/Commit) a zero, asse settimanale fermo a una settimana passata, daily snapshot "No data found" — mentre tutti gli endpoint API restituivano dati corretti (verificato via curl: weekly W23=168 mission/thru 681; daily 2026-06-08 = 26 mission/PI 31.39; missions_by_day 50 giorni/16 organi).

## Causa radice
L'API Flask non impostava header di cache. Le richieste GET `/api/v2/stats/*` venivano **cacheate dal browser**: al reload normale il browser serviva la risposta vecchia (dal disk cache) invece di ri-scaricarla. Poiché durante tutte le iterazioni di fix le stat erano cambiate molte volte, la copia in cache era pre-fix (mission a 0, senza la settimana corrente). Il "hard refresh" la aggirava una volta, ma tornava stale.

## Fix
`api.py`, hook `@app.after_request`:
```python
@app.after_request
def _no_store_api(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp
```
Le statistiche sono dati vivi (il serving si auto-rigenera dai registry, M-247). `no-store` garantisce che il browser ri-scarichi sempre le metriche correnti → la dashboard riflette sempre lo stato reale, senza intervento manuale.

## Verifica
- `curl -D-` su `/api/v2/stats/weekly` → `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`.
- `tests/m_249_nocache_test.py`: la risposta `/api/v2/stats/weekly` ha `no-store`. 1/1.
- Regressione completa: 19/19.
- Servizio `egi-stat-api.service` riavviato → header attivo in produzione.

## Effetto utente
Un'unica ricarica della pagina (per prendere il nuovo bundle JS + la prima risposta no-store) e da lì la dashboard è sempre aggiornata. Fine del problema "app rotta/ferma".
