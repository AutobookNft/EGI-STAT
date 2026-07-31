# shellcheck shell=bash
# ─────────────────────────────────────────────────────────────────────────────
# @package  os3-matrix/bin
# @author   Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
# @version  1.0.0 (M-OS3-165)
# @date     2026-07-21
# @purpose  Lettore bash UNICO del contratto contracts/grano-recognition.json:
#           riconosce il tag-di-classe (regex + esclusione prefisso M-* + alias)
#           e il marcatore [grano:<slug>] (regex kebab-strict) di un commit.
#           Sorgente-dato = il JSON (una fonte). Sourgono questo file il GATE
#           (hooks/capability-commit-gate.sh) e il test di parita (M-OS3-165):
#           una sola implementazione bash, mai reimplementata nel test. Vive in
#           bin/ (non superficie-di-difesa) per NON moltiplicare i file-hook.
#           Non ha shebang: e una libreria da `source`, non un eseguibile.
# ─────────────────────────────────────────────────────────────────────────────

# Stato caricato dal contratto (globali del processo che sourcia).
GRANO_TAG_PAT=""          # ERE del tag, es. ^\[([A-Z0-9_-]+)\]
GRANO_SLUG_PAT=""         # ERE del grano, es. \[grano:([a-z0-9-]+)\]
GRANO_TAG_EXCLUDE=""      # prefisso di tag escluso (es. M-)
GRANO_CONTRACT_JSON=""    # path del contratto caricato (per il lookup alias)
GRANO_LOADED=0            # 1 = contratto caricato e valido

# grano_load_contract [path] -> 0 se caricato e valido; non-zero altrimenti.
# Con path vuoto risolve il contratto relativo a questa libreria (bin/../contracts).
grano_load_contract() {
  local c="${1:-}"
  if [ -z "$c" ]; then
    local self
    self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || return 1
    c="$self/../contracts/grano-recognition.json"
  fi
  [ -r "$c" ] || return 1
  GRANO_TAG_PAT="$(jq -r '.tag_pattern // empty' "$c" 2>/dev/null)"
  GRANO_SLUG_PAT="$(jq -r '.grano_pattern // empty' "$c" 2>/dev/null)"
  GRANO_TAG_EXCLUDE="$(jq -r '.tag_exclude_prefix // empty' "$c" 2>/dev/null)"
  [ -n "$GRANO_TAG_PAT" ] && [ -n "$GRANO_SLUG_PAT" ] || return 1
  GRANO_CONTRACT_JSON="$c"
  GRANO_LOADED=1
  return 0
}

# grano_tag <msg> -> tag normalizzato su stdout (alias applicato); return 1 se
# nessun tag riconoscibile a inizio messaggio o tag escluso; return 2 se il
# contratto non e caricato (il chiamante decide se degradare a pass).
grano_tag() {
  [ "$GRANO_LOADED" = 1 ] || return 2
  local m="$1" tag aliased
  # Pattern NON quotato: e una regex ERE per [[ =~ ]] (BASH_REMATCH[1] = capture).
  [[ "$m" =~ $GRANO_TAG_PAT ]] || return 1
  tag="${BASH_REMATCH[1]}"
  if [ -n "$GRANO_TAG_EXCLUDE" ]; then
    case "$tag" in "$GRANO_TAG_EXCLUDE"*) return 1 ;; esac
  fi
  aliased="$(jq -r --arg t "$tag" '.tag_aliases[$t] // empty' "$GRANO_CONTRACT_JSON" 2>/dev/null)"
  [ -n "$aliased" ] && tag="$aliased"
  printf '%s' "$tag"
}

# grano_slug <msg> -> slug kebab su stdout (vuoto se assente/non-kebab).
# return 2 se il contratto non e caricato; 0 negli altri casi (anche no-match).
grano_slug() {
  [ "$GRANO_LOADED" = 1 ] || return 2
  local m="$1"
  [[ "$m" =~ $GRANO_SLUG_PAT ]] && printf '%s' "${BASH_REMATCH[1]}"
  return 0
}
