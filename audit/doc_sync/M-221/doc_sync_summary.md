# DOC-SYNC M-221 — EGI-STAT enrich per-organo (grep-by-id)

> Istanza LSO ridotta: nessun `docs/lso/SSOT_REGISTRY.json`, nessun `RAG_SCHEMA`.
> Modalita: `registry_only`, RAG skippato. Set SSOT fornito esplicitamente dal chiamante.
> `CLAUDE_ECOSYSTEM_CORE.md` escluso dallo scope (modifica estranea nota).

## Cosa ha fatto M-221 (semantica)
Fase-2 di M-220. Aggiunge `backend/enrich_by_message.py`: enricha le missioni degli
organi senza blocco `stats` nel registry (os3-matrix, LeVespe, oracode) attribuendo i
commit per **id-missione** cercato nel **subject** dei commit di tutti i repo git
dell'ecosistema (cross-repo). `ingest_missions.sync_mission_stats()` ora lo invoca in
**fallback guardato** (`has_rich`): applica le grep-stats solo dove mancano git-stats
ricche, senza mai sovrascriverle. Risultato dichiarato: 208/218 missioni con PI reale,
10 residui PI=0. Nuovo test indipendente `tests/m_221_enrich_by_id_test.py`.

## SSOT verificati e azioni
| SSOT | Modo | Esito | Note |
|------|------|-------|------|
| `backend/MULTI_REGISTRY.md` | additive | applied | Corpo gia aggiornato a mano: copre enrich-by-message, subject-only, limiti, 10 residui PI=0, debito attribuzione, multi-id. Gap chiuso: aggiunta del test M-221 nella sezione Test. |
| `README.md` | additive | applied | Aggiunta voce `enrich_by_message.py` in "Componenti Chiave > Backend", con rinvio del dettaglio a MULTI_REGISTRY.md. |

### Verifica coverage (richiesta del chiamante)
1. **MULTI_REGISTRY.md copre M-221?** Si. Tutte le claim richieste (enrich-by-message,
   subject-only, limiti, 10 residui PI=0, debito attribuzione) sono presenti nel testo
   gia aggiornato a mano. Unica lacuna trovata e colmata: il nuovo test non era citato.
2. **README necessita un puntatore a enrich_by_message.py?** Si. Il README descriveva
   solo il meccanismo M-220 senza menzionare l'enrichment degli organi non enrichati.
   Aggiunto puntatore additivo (detail-link a MULTI_REGISTRY.md, pattern coerente).
3. **Patch applicate** in modalita additiva. **Codice non toccato.**

### Esaustivita (M-OS3-027)
`grep` post-edit: `enrich_by_message` e `m_221_enrich_by_id_test` presenti in entrambi i
doc dove pertinente. Nessun residuo stale `93/217`. Il `150/150` a riga 57 e riferimento
storico/comparativo legittimo (non un residuo da aggiornare).

## File nuovi della mission — coverage
- `backend/enrich_by_message.py` → documentato (README + MULTI_REGISTRY.md). OK
- `backend/tests/m_221_enrich_by_id_test.py` → documentato (MULTI_REGISTRY.md sez. Test). OK
- Nessun file nuovo scoperto.

## RAG
Skippato (nessun `RAG_SCHEMA`). Modalita LSO ridotta: nessun re-indexing, nessun sanity check.
