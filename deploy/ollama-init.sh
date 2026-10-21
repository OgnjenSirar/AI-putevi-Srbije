#!/bin/sh
# Priprema modela na Ollama serveru hosta. Pokrece se pri svakom deploy-u, a posao
# radi samo ako nesto nedostaje. Modeli drugih projekata se ne menjaju.
O=${OLLAMA_URL:-http://ollama-proxy}

i=0
until v=$(curl -fsS --max-time 5 $O/api/version); do
  i=$((i+1))
  if [ $i -ge 30 ]; then
    echo "GRESKA: Ollama na hostu ne odgovara (127.0.0.1:11434). Proveriti: systemctl status ollama"
    exit 1
  fi
  sleep 10
done
echo "Ollama verzija: $v"

if curl -sS $O/api/tags | grep -q "\"name\":\"$BASE_MODEL\""; then
  echo "Osnovni model $BASE_MODEL je vec na serveru"
else
  echo "Preuzimam $BASE_MODEL (jednom, nekoliko GB)..."
  resp=$(curl -sS --max-time 7200 $O/api/pull -d "{\"model\":\"$BASE_MODEL\",\"stream\":false}")
  echo "$resp"
  if echo "$resp" | grep -q '"error"'; then
    echo "GRESKA: preuzimanje nije uspelo. Gemma 4 zahteva Ollama 0.20 ili noviju (ollama --version na hostu)."
    exit 1
  fi
fi

# Varijanta sa vecim kontekstom, jer OpenAI-kompatibilan API ne prima num_ctx po zahtevu
echo "Pravim $MODEL iz $BASE_MODEL (num_ctx $NUM_CTX)..."
resp=$(curl -sS $O/api/create -d "{\"model\":\"$MODEL\",\"from\":\"$BASE_MODEL\",\"parameters\":{\"num_ctx\":$NUM_CTX,\"temperature\":0.2},\"stream\":false}")
echo "$resp"
if echo "$resp" | grep -q '"error"'; then
  echo "GRESKA: pravljenje modela $MODEL nije uspelo"
  exit 1
fi
echo "Model $MODEL je spreman"

# Kratak test brzine (ujedno ucitava model u memoriju pre prvog pravog zahteva)
echo "Test brzine..."
resp=$(curl -sS --max-time 600 $O/api/generate -d "{\"model\":\"$MODEL\",\"prompt\":\"Napiši tri rečenice o elektronskoj naplati putarine.\",\"stream\":false,\"think\":false,\"options\":{\"num_predict\":120}}")
num() { echo "$resp" | grep -o "\"$1\":[0-9]*" | head -1 | cut -d: -f2; }
ec=$(num eval_count) ed=$(num eval_duration) ld=$(num load_duration) pc=$(num prompt_eval_count) pd=$(num prompt_eval_duration)
if [ -n "$ec" ] && [ -n "$ed" ] && [ "$ed" -gt 0 ]; then
  awk -v ec="$ec" -v ed="$ed" -v ld="${ld:-0}" -v pc="${pc:-0}" -v pd="${pd:-1}" 'BEGIN{
    printf "Generisanje: %.1f tokena/s (%d tokena)\n", ec/(ed/1e9), ec
    printf "Obrada upita: %.0f tokena/s (%d tokena)\n", pc/(pd/1e9), pc
    printf "Ucitavanje modela: %.1f s\n", ld/1e9 }'
else
  echo "Test brzine nije uspeo: $(echo "$resp" | head -c 300)"
fi
curl -sS $O/api/ps | grep -oE '"name":"[^"]*"|"size":[0-9]+|"size_vram":[0-9]+' | paste - - - | sed -E 's/"name":"([^"]*)"[[:space:]]+"size":([0-9]+)[[:space:]]+"size_vram":([0-9]+)/\1 \2 \3/' | awk '{printf "U memoriji: %s, ukupno %.1f GB, na GPU %.1f GB (%.0f%%)\n", $1, $2/1e9, $3/1e9, ($2>0?100*$3/$2:0)}'
