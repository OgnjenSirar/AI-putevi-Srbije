#!/usr/bin/env bash
# Upisuje sadrzaj fajla kao GitHub Actions anotaciju (vidljivo u pregledu run-a i preko API-ja).
# Upotreba: deploy/gh-annotate.sh error|warning|notice "Naslov" fajl [broj_linija]
level="$1" title="$2" file="$3" lines="${4:-25}"
[ -s "$file" ] || exit 0
msg=$(tail -n "$lines" "$file" | sed -e 's/\x1b\[[0-9;]*m//g' -e 's/%/%25/g' -e 's/\r//g' | awk 'BEGIN{ORS="%0A"}{print}')
echo "::${level} title=${title}::${msg}"
