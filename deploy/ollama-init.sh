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
