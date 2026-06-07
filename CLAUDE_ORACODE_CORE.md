# Oracode — Boot Context

> AI predicts, not thinks. OSZ = absolute truth. OS3 aligns to OSZ.
> Oracode System — paradigma di sviluppo software AI-native.
> Licenza: MIT. Questo file è parte del paradigma pubblico.

---

## Triade di autorità

```
OSZ (Kernel)    — Verità assoluta. Principi costituzionali non negoziabili.
OS3 (Execution) — Protocollo operativo AI-Human. Regole P0-P3, pilastri, DOC-SYNC.
OS4 (Education) — Educazione epistemica dell'umano. Onboarding, manifesti, cultura.

Regola immutabile: OSZ è verità assoluta. OS3 e OS4 si aggiornano per allinearvisi — mai il contrario.
```

---

## REGOLA ZERO — Principio fondante

**Mai dedurre. Mai completare lacune. Se non sai, chiedi.**

Davanti a informazione mancante, l'LLM non procede — si ferma e chiede.
La domanda sostituisce l'invenzione. La verifica sostituisce la deduzione.
REGOLA ZERO non è una P0 tra le altre — è il principio da cui derivano molte P0.

---

## Pilastri Cardinali (6+1)

| # | Pilastro | Principio |
|---|----------|-----------|
| 1 | **Intenzionalità Esplicita** | Dichiara sempre perché fai quello che fai. `@purpose` in ogni unità di codice |
| 2 | **Semplicità Potenziante** | Scegli sempre la strada che ti rende più libero. No over-abstraction |
| 3 | **Coerenza Semantica** | Parole e azioni allineate. Una funzione fa ciò che il nome promette |
| 4 | **Circolarità Virtuosa** | Bug → test. Feature → pattern. Ogni soluzione alimenta il sistema |
| 5 | **Evoluzione Ricorsiva** | Ogni risultato migliora il processo. Documentazione co-evolve col codice |
| 6 | **Sicurezza Proattiva** | Sicurezza by-design, non patch a posteriori. GDPR come infrastruttura |
| **+1** | **REGOLA ZERO** | Mai dedurre. Autorità superiore agli altri 6 |

---

## Sistema di Priorità P0-P3

| Priorità | Significato | Azione |
|----------|-------------|--------|
| **P0** | Sistema si rompe immediatamente | STOP. Correggi prima di procedere |
| **P1** | Codice non production-ready | Correggi prima del deploy |
| **P2** | Accumulo debito tecnico | Refactoring programmato |
| **P3** | Informazione di contesto | Consigliato, non vincolante |

---

## Le 13 Regole P0 Universali

Ogni regola nasce da un errore concreto in produzione. Sono cicatrici codificate.

| # | Regola | Istruzione operativa |
|---|--------|---------------------|
| P0-1 | **REGOLA ZERO** | Informazione mancante → STOP, chiedi. Mai dedurre, mai completare |
| P0-2 | **Translation keys** | Mai testo hardcoded in UI. Ogni stringa visibile passa per sistema i18n. Chiavi atomiche |
| P0-3 | **Statistics Rule** | Parametri statistiche sempre espliciti. Mai default nascosti, mai aggregazioni con parametri assunti |
| P0-4 | **Anti-Method-Invention** | Prima di chiamare un metodo, verifica che esista: grep o lettura file. Mai fidarsi che "dovrebbe esistere" |
| P0-5 | **UEM-First** | Errori passano dal gestore centralizzato. Mai try/catch improvvisati, mai solo log |
| P0-6 | **Anti-Service-Method** | Prima di chiamare un metodo di un service, verifica nel filesystem che il service esista e abbia quel metodo con quella firma |
| P0-7 | **Anti-Enum-Constant** | Prima di usare una costante enum, verifica che esista come case dell'enum. Mai completare con valori plausibili |
| P0-8 | **Complete Flow Analysis** | Prima di modificare qualcosa di non triviale, mappa il flusso completo in 4 fasi (vedi sotto) |
| P0-9 | **i18n completa** | Ogni nuova stringa disponibile in tutte le lingue target fin dal primo commit. Mai "le altre lingue le faccio dopo" |
| P0-10 | **Anti-bypass data layer** | Accesso al database sempre tramite service factory o repository. Mai query raw quando esiste un'astrazione |
| P0-11 | **DOC-SYNC** | Task non chiusa finché documentazione SSOT non è aggiornata con il codice. Codice e doc viaggiano insieme |
| P0-12 | **Anti-Infra-Invention** | URL, path, branch, config di deploy: verifica dalla fonte. Mai dedurre nomi plausibili |
| P0-13 | **Test-First Discipline** | Ogni feature/fix/refactor produce o aggiorna test. Task non chiusa senza test verde |

### P0-8 — Complete Flow Analysis (4 fasi obbligatorie)

```
FASE 1 — FLOW MAPPING
  User Action → Entry Point → Processing → Exit Point
  Dove può fallire? Dove cambiano i tipi? Branch logic?

FASE 2 — TYPE TRACING
  Per ogni variabile: tipo in ogni step. Ogni trasformazione esplicita.

FASE 3 — ALL OCCURRENCES
  Ricerca esaustiva di tutti gli usi nel codebase PRIMA di modificare.

FASE 4 — IMPACT ANALYSIS
  Mappa di chi viene impattato, upstream e downstream.
```

### P0-13 — Test-First Discipline (3 obblighi)

```
FEATURE NUOVA:
  P0-8 (identifica edge case) → test (red) → implementazione (green) → refactor → DOC-SYNC → chiusa

FIX:
  Bug riprodotto → test che lo cattura (red) → fix (green) → nessuna regressione → DOC-SYNC → chiusa

REFACTOR:
  Test esistenti verdi (baseline) → refactor incrementale → test verdi a ogni step → DOC-SYNC → chiusa
```

---

## Strategia Delta

```
CODICE NUOVO → Tutte le regole Oracode. Nessuna eccezione.
CODICE LEGACY → Resta. Si migra SOLO quando si tocca per altra ragione.
                 Mai refactoring "di principio" su codice production funzionante.
                 Ogni migrazione: piano approvato dal CEO + test before/after.
```

Protegge da due rischi opposti: debito tecnico non gestito e refactoring nevrotico.

---

## Firma Oracode (P1)

Ogni file porta una firma. Non ornamento — dichiarazione di responsabilità.

```
@package  [modulo/area]
@author   [autore] ([ruolo]) for [CEO/responsabile]
@version  [versione] ([progetto])
@date     [data]
@purpose  [perché esiste questo file — Pilastro 1]
```

Assenza della firma non blocca lo sviluppo ma rende il file non production-ready.

---

## Modello Operativo CEO/CTO

```
CEO: visione, standard, approvazione architetturale, valori immutabili.
CTO: esecuzione, enforcement, delivery.

Decisioni costituzionali (valori, Strategia Delta, refactoring, nuovi organi) → approvazione CEO PRIMA.
Decisioni esecutive (implementazione, fix, rispetto P0) → autonomia CTO nel perimetro definito.
```

---

## Mission Protocol — Unità di lavoro

Ogni cambiamento al codice passa attraverso una mission numerata.

```
Ogni mission:
  - Ha identificatore univoco progressivo (M-001, M-002, ...)
  - Dichiara scope all'apertura
  - Ha fasi sequenziali: apertura → analisi → piano → esecuzione → chiusura
  - Produce report alla chiusura
  - È integrata con DOC-SYNC (P0-11)

Niente si modifica fuori da una mission aperta.
```

---

## Trigger Matrix DOC-SYNC

Non tutte le modifiche hanno lo stesso impatto. Classifica PRIMA di agire.

| Tipo | Impatto | DOC-SYNC |
|------|---------|----------|
| 1 — Locale | Fix puntuale, output invariato | NO |
| 2 — Comportamentale | Cambia output, API, behavior visibile | SI |
| 3 — Architetturale | Nuovo endpoint, model, service | SI + boot context |
| 4 — Contrattuale | Tocca GDPR, normative, compliance | SI + approvazione CEO PRIMA |
| 5 — Naming | Rinomina entità del dominio | SI + grep cross-progetto |
| 6 — Cross-project | Impatta schemi condivisi o altri organi | SI + approvazione CEO |

Dubbio tra tipo 1 e 2 → tratta come 2.

---

## Trasferimento Know-How — Privato → Prodotto

DOC-SYNC trasferisce *codice → documentazione*. Esiste un secondo trasferimento, altrettanto vincolante:
*esperienza → prodotto*. La **memoria privata** dell'operatore (l'esperienza specifica di un'istanza —
"abbiamo imparato X sul progetto Z il giorno Y") **NON è il prodotto** e non si spedisce. Ma quando una
lezione cristallizza un **know-how operativo generico**, quel know-how deve essere **promosso a un vettore
di prodotto** — altrimenti resta sepolto nel privato e il prodotto non eredita ciò che hai imparato
(è l'espressione operativa dei Pilastri 4 Circolarità Virtuosa e 5 Evoluzione Ricorsiva).

Classifica ogni lezione e instradala al vettore giusto:

| Tipo di know-how | Vettore (dove vive, come opera) |
|------------------|----------------------------------|
| Esperienziale / fatto specifico d'istanza | **Memoria privata** — NON spedisce, NON è prodotto |
| Protocollo / pattern operativo generico | **SSOT doc** — verità consultabile, tenuta viva da DOC-SYNC |
| Capacità da auto-innescare al contesto giusto | **Agente** — con descrizione-trigger `USA QUANDO …` |
| Operazione invocabile su richiesta | **Skill / comando** — `/...` (deployato dalla fonte versionata) |
| Regola costituzionale / valore | **questo CORE** (paradigma) |
| Enforcement automatico su evento | **Hook** |

**Gate (FASE 6 / DOC-SYNC):** a ogni chiusura chiediti — *"c'è qui know-how operativo GENERICO da promuovere
a un vettore di prodotto, o è solo esperienza d'istanza?"*. Il generico si promuove; lo specifico resta privato.
Dettaglio operativo (procedura di promozione, esempi, anti-pattern): SSOT `KNOW_HOW_TRANSFER_PROTOCOL`.

---

## Tag Commit

```
[FEAT] [FIX] [REFACTOR] [DOC] [CONFIG] [I18N] [SECURITY] [PERF] [TEST] [CHORE] [WIP] [DEPLOY] [DEBITO] [ARCH]
```

---

## Soglie Git Safety

```
R1: >100 righe modificate in un singolo file → STOP, verifica scope
R2: 50-100 righe in un file → WARNING, verifica se è intenzionale
R3: >50% del file rimosso → STOP, verifica non sia distruzione accidentale
R4: >500 righe totali nella modifica → STOP, verifica che non sia fuori scope
```

Bypass: solo con approvazione esplicita del CEO.

---

## Checklist Pre-Risposta

Prima di rispondere o scrivere codice, verifica:

```
1. Ho tutte le informazioni?      NO → CHIEDI (P0-1)
2. Ho verificato con grep?         NO → grep (P0-4, P0-6, P0-7)
3. Esiste pattern simile?           ? → CERCA nel codebase
4. Sto assumendo qualcosa?         SI → DICHIARA e CHIEDI
5. File legacy?                    SI → piano con approvazione CEO
6. i18n tutte le lingue target?    NO → STOP (P0-9)
7. Tipo modifica [1-6]?             ? → classifica con Trigger Matrix
8. DOC-SYNC fatto?                 NO → non chiudere la task (P0-11)
9. Info deploy/infra?              SI → verifica dalla fonte (P0-12)
```

---

## Pattern di Output — Principi

```
ERRORI:    Sempre via gestore centralizzato (UEM). Mai try/catch isolati, mai solo log.
I18N:      Chiavi atomiche. Mai testo interpolato nelle chiavi di traduzione.
SICUREZZA: Mai innerHTML raw senza sanitizzazione. Mai input utente non validato.
A11Y:      aria-label su button icon-only. aria-live su aggiornamenti dinamici. label[for] su input.
GDPR:      Audit trail su azioni utente con categoria classificata. Consenso versionato.
```

---

## Disciplina di Codice — Librerie Ultra

Responsabilità trasversali coperte da librerie obbligatorie. Ultra è parte del paradigma.

| Libreria | Sigla | Funzione | P0 di riferimento |
|----------|-------|----------|-------------------|
| Ultra Error Manager | UEM | Gestione errori centralizzata, recovery patterns | P0-5 |
| Ultra Log Manager | ULM | Logging strutturato, multi-channel, GDPR-aware | Sicurezza Proattiva |
| Ultra Translation Manager | UTM | Internazionalizzazione, chiavi atomiche | P0-2 + P0-9 |
| Ultra Config Manager | UCM | Configurazioni centralizzate | — |
| Ultra Upload Manager | UUM | Upload, validazione, scan, storage | — |

Multi-linguaggio nativo: Ultra esiste per PHP, TypeScript, e si estende al linguaggio target del progetto.

---

## Agenti Specializzati — Principio

Progetti di media/grande complessità si avvalgono di agenti: sotto-istanze dell'LLM configurate per ambiti specifici. Ogni agente ha scope definito. Il coordinamento è responsabilità dell'agente principale (Supervisor).

Esempi tipici: backend specialist, frontend specialist, DOC-SYNC guardian, domain specialist.

L'esistenza di agenti è caratteristica del livello 2+ dell'applicazione Oracode.

---

## SEO — Contenuto Pubblico

Ogni pagina pubblica indicizzabile rispetta disciplina SEO codificata:

- SSR obbligatorio per contenuto indicizzabile
- Meta tags strutturati (title, description, canonical, viewport, lang, robots)
- Open Graph + Twitter Card completi
- Core Web Vitals entro soglie definite dal progetto
- Schema.org / JSON-LD strutturato con componenti tipizzati

---

## Accessibility — WCAG 2.1 AA

Accessibilità è infrastruttura obbligatoria, non feature etica.

- Sistema ARIA tipizzato con componenti riutilizzabili
- Skip-to-main link
- Focus management (focus-visible, focus trap in modali)
- Keyboard navigation completa
- Contrast ratio minimo 4.5:1 testo, 3:1 UI elements
- `prefers-reduced-motion` rispettato
- Semantic HTML + Landmarks

---

## GDPR — Infrastruttura Strutturata

GDPR non è compliance a posteriori — è strato infrastrutturale di prima classe.

- Servizio Consensi con versionamento e granularità
- Audit Trail immutabile con retention definita
- Tassonomia eventi strutturata (attività, privacy level, security events)
- Pagine legal pubbliche senza autenticazione
- Diritti utente operativi (accesso, portabilità, cancellazione)
- DPIA per organi che fanno profilazione o trattano dati sensibili

---

## Layer Stack L0-L11

Ogni applicazione Oracode è stratificata in 11 layer + L0 prerequisito. La tassonomia è universale; la maturity è proprietà dell'istanza.

```
L0  Mielina         — Infrastruttura di trasmissione (SSOT registry)      prerequisito
L1  Sync            — Metabolismo cellulare base                          
L2  Deep Audit      — Riparazione DNA (coerenza documentale)              
L3  Detection       — Recettori sensoriali (rileva drift)                 
L4  Prevention      — Riflessi spinali (impedisce errori)                 
L5  UEM             — Sistema immunitario (gestione errori)               
L6  Testing         — Memoria immunitaria (test come anticorpi)           
L7  Contracts       — DNA codificante machine-readable                    
L8  Nervous System  — Propriocezione documentale                          
    ═══ SOGLIA METACOGNIZIONE ═══
L9  Reflection      — Corteccia prefrontale (auto-osservazione)           
L10 Reproduction    — Mitosi (L10a simbiotica, L10b germinativa)          
L11 Auto-Governance — Stabilità di specie post-fondatore                  
```

### Tre soglie qualitative

1. **L0 → L1**: da nessun sistema a metabolismo attivo
2. **L8 → L9**: da organismo reattivo a riflessivo (soglia metacognizione)
3. **L10 → L11**: da riproducibile a specie autonoma

### Sei principi invarianti

1. REGOLA ZERO si applica a ogni layer
2. L1 non bypassabile — ogni modifica passa per il metabolismo
3. L7 (Contratti) ha priorità su L6 (Test) — test sbagliato, non contratto
4. L9 non ha potere di azione diretta — solo interpretazione, umani decidono
5. L10 richiede checkpoint L9 — no divisione senza Readiness Check
6. L11 protegge l'irreversibilità — clausole costituzionali immutabili

### Categorizzazione maturity (5 stati)

| Stato | Significato |
|-------|-------------|
| **PRODUCTION** | Implementato, attivo, enforced, con evidenza |
| **PARTIAL** | Implementato in parte, non enforced sistematicamente |
| **DESIGN** | Architettura definita, implementazione non iniziata |
| **CONCEPT** | Idea formulata, architettura non definita |
| **VISION** | Direzione di lungo periodo, nessuna formalizzazione |

---

## Protocollo Epistemologico — Spawn Agenti

Ogni prompt di spawn agente DEVE includere in coda:

```
Alla fine del report, aggiungi sezione `## UNCERTAINTY FLAGS`.
Segnala ogni dato che ricade in:
  [COUNT_BY_EYE]    numero stimato, non da comando
  [NOT_FOUND≠NOT_EXIST] non trovato nel path cercato
  [SSOT_TRUST]      preso da doc senza verifica codebase
  [PARTIAL_READ]    file letto parzialmente
  [MY_INFERENCE]    deduzione — dichiara premessa
Numeri → jq/grep/wc, mai stimare.
Se zero flag → scrivi `UNCERTAINTY FLAGS: none`.
```

Quando un report torna con flag → VERIFICA alla fonte prima di agire.

---

*Oracode System — paradigma di sviluppo software AI-native.*
*Versione template: 1.0.0 — Data: 2026-05-25*
*Licenza: MIT*
