# M-266 — Report Esteso: il cantiere aperto va online

**Mission:** M-266 | **Data:** 2026-06-11

## Perché

La nuova pagina /softwarehouse di fabiocherici.com ha come elemento distintivo
il "cantiere aperto": le statistiche di produzione REALI (ore, progetti, righe)
visibili live al visitatore — la prova di metodo che nessuna agenzia può
copiare, verificabile su GitHub. Vincolo CEO: "i dati saranno live, punto" —
niente placeholder.

EGI-STAT (il tracker interno) esisteva solo in locale. Serviva esporlo:
ma è uno strumento interno con dati di dettaglio (nomi progetto, mission,
ore per cliente) che NON devono essere pubblici.

## La soluzione: tutto chiuso, una sola finestra

- **stat.florenceegi.com** (sottodominio nuovo, creato con la procedura SSOT
  Route 53): dashboard e API interne dietro password — solo il CEO entra.
- **Una sola finestra pubblica**: /api/public/site-stats — otto numeri
  aggregati (ore totali, ore della settimana, conteggio progetti, righe,
  ultima attività). Mai un nome di progetto o cliente. Rate-limit contro
  gli abusi, CORS ristretto al solo fabiocherici.com.
- **Onestà epistemica nei dati**: il campo hours_note dichiara che le ore
  sono "manual + commit-estimate" — la stima non si spaccia per misura.

## Come restano "live"

I dati sorgente (i mission registry) vivono sulla macchina di sviluppo. Lo
SQLite aggregato viaggia verso il server con `push-stats.sh` (un comando, o
cron locale). Il widget mostra anche "ultima attività: oggi" — il vero
segnale di cantiere vivo.

## Numeri al primo deploy

2.243,7 ore tracciate · 179,4 ore negli ultimi 7 giorni · 23 progetti
(21 attivi nel mese) · 2.595.750 righe nette · ultima attività: oggi.

## Cosa sblocca

M-015 — il rewrite della pagina softwarehouse — parte con la dipendenza
stats già viva: il widget cantiere nasce collegato a dati veri, come voleva
il CEO ("così la pagina nasce con le stat già visibili").

## Residui

- Fix R1 (messaggi d'errore generici sull'endpoint pubblico) committato,
  sale al prossimo lancio del deploy da parte del CEO.
- push-stats.sh da mettere in cron locale per il refresh automatico.
