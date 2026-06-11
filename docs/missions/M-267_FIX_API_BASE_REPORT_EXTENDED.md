# M-267 — Report Esteso: perché la dashboard era vuota

**Mission:** M-267 | **Data:** 2026-06-11

## Cosa è successo

Subito dopo il deploy di stat.florenceegi.com (M-266) il CEO ha aperto la
dashboard: tabelle vuote, grafici vuoti, "No data found". I dati però
c'erano: l'endpoint pubblico rispondeva con i numeri giusti.

## La causa

L'interfaccia (la SPA React) viene "buildata" con un file di configurazione
che le dice DOVE sta l'API. Quel file (`.env.production`) era rimasto al
deploy precedente di mesi fa — un indirizzo temporaneo ormai spento. La
dashboard chiedeva i dati a un server che non esiste più, e mostrava il vuoto.

M-266 non l'aveva intercettato perché nessun test controllava quel file.

## La lezione (Circolarità Virtuosa)

Il bug è diventato un test permanente: da oggi l'acceptance verifica che
l'env di produzione punti al dominio giusto, che il bundle compilato non
contenga l'host morto, e che l'API risponda con dati veri. Questo errore
specifico non può ripetersi in silenzio.

## Esito

Dashboard piena: ore per progetto, grafici, indice di produttività. Il
"cantiere aperto" è completo: vetrina pubblica (8 numeri aggregati per
fabiocherici.com) + ufficio privato (dashboard dietro password per il CEO).
