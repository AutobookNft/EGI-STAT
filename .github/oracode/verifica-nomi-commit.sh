#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# @package  os3-matrix/git-hooks
# @author   Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version  1.0.0 (os3-matrix — M-OS3-184, il muro sul server)
# @date     2026-07-31
# @purpose  Verifica che OGNI commit di un intervallo porti il nome della capacità. Gira SUL
#           SERVER (GitHub Actions), dove chi spinge non decide quali controlli girano.
#
#           PERCHE' ESISTE, misurato il 2026-07-31: il cancello installato nei 27 repository alle
#           13:22 funziona — provato sui messaggi veri, li rifiuta — ma sei commit della mission
#           M-EGI-415 sono passati lo stesso dopo quell'ora. L'unica strada e `git commit
#           --no-verify`, l'opzione con cui git salta tutti i ganci. Nessun controllo che vive nel
#           computer puo impedirlo: e git stesso a offrire la scorciatoia. Qui la scorciatoia non c'e'.
#
#           NON REINVENTA IL RICONOSCIMENTO: legge il contratto unico
#           contracts/grano-recognition.json (SSOT GRANO_RECOGNITION_UNICA), lo stesso del
#           contatore, del cancello di sessione e della chiusura. Nei repository dove viene
#           installato il contratto viaggia accanto (.github/oracode/).
#
# Uso:  verifica-nomi-commit.sh <sha-inizio> <sha-fine>
# Exit: 0 tutti in regola (o nessun commit) · 1 almeno uno senza nome · 2 uso/errore
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

DA="${1:-}"; A="${2:-}"
[ -n "$DA" ] && [ -n "$A" ] || { printf 'verifica-nomi-commit: uso: %s <sha-inizio> <sha-fine>\n' "$0" >&2; exit 2; }

QUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB=""
for c in "$QUI/../bin/grano-recognition-lib.sh" "$QUI/grano-recognition-lib.sh" \
         "$HOME/os3-matrix/bin/grano-recognition-lib.sh"; do
  [ -r "$c" ] && { LIB="$c"; break; }
done
[ -n "$LIB" ] || { printf 'verifica-nomi-commit: libreria del riconoscimento non trovata — non giudico a occhio.\n' >&2; exit 2; }
# shellcheck source=/dev/null
. "$LIB"
CONTRATTO=""
for c in "$QUI/../contracts/grano-recognition.json" "$QUI/grano-recognition.json" \
         "$HOME/os3-matrix/contracts/grano-recognition.json"; do
  [ -r "$c" ] && { CONTRATTO="$c"; break; }
done
grano_load_contract "$CONTRATTO" || { printf 'verifica-nomi-commit: contratto non caricabile.\n' >&2; exit 2; }

# I commit di FUSIONE li genera git da sé, con un messaggio suo: non sono lavoro di nessuno e non
# si giudicano (più di un genitore in %P).
MAPPA="$(git log --pretty=format:'%H%x09%P%x09%s' "$DA..$A" 2>/dev/null)" || {
  printf 'verifica-nomi-commit: intervallo non leggibile: %s..%s\n' "$DA" "$A" >&2; exit 2; }

SENZA=0
while IFS=$'\t' read -r sha genitori subj; do
  [ -n "${sha:-}" ] || continue
  case "$genitori" in *" "*) continue ;; esac      # più di un genitore = fusione
  slug="$(grano_slug "$subj")"
  if [ -z "$slug" ]; then
    SENZA=$((SENZA+1))
    printf '  ✗ %s  %s\n' "${sha:0:8}" "$subj" >&2
  fi
done <<< "$MAPPA"

if [ "$SENZA" -gt 0 ]; then
  printf '\n━━━ %d commit senza il nome della capacità ━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n' "$SENZA" >&2
  printf 'Ogni commit dice a quale capacità appartiene il lavoro: senza il nome, quel\n' >&2
  printf 'lavoro non entra nella produzione e non viene contato.\n\n' >&2
  printf 'Forma:  [TAG][M-XXX][grano:nome-della-capacita] messaggio\n' >&2
  printf 'Il nome e tutto minuscolo, parole unite da trattini.\n' >&2
  printf 'Qui non si passa con --no-verify: questo controllo gira sul server.\n' >&2
  printf '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n' >&2
  exit 1
fi
exit 0
