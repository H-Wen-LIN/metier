#!/bin/sh
# Met à jour les CSV d'offres. À lancer à la main (./mise-a-jour.sh) ou via cron.
# Modifiez les recherches ci-dessous : une ligne par commande, toujours avec --mise-a-jour.
cd "$(dirname "$0")" || exit 1
PY="$PWD/.venv/bin/python"
JOURNAL="$PWD/journal-mise-a-jour.log"
echo "===== $(date)" >> "$JOURNAL"

(cd jobijoba-scraper && "$PY" scraper.py "developpeur web" --ville Clermont-ferrand --ville Paris --pages 3 --sans-sponsorises --mise-a-jour) >> "$JOURNAL" 2>&1

(cd wttj-scraper && "$PY" scraper.py emploi-developpeur-web-paris-75000 --suivre 3 --mise-a-jour) >> "$JOURNAL" 2>&1

echo "Mise à jour terminée. Détails dans journal-mise-a-jour.log"
