#!/bin/sh
# Pravi self-signed sertifikat za javnu adresu demoa ako ga nema ili ako se adresa promenila.
# Sopstveni sertifikat: kopirati server.crt i server.key u volumen i napraviti prazan fajl .sopstveni
set -e
D="${CERT_DIR:-/etc/nginx/certs}"
H="${CERT_HOST:-localhost}"
mkdir -p "$D"

if [ -f "$D/.sopstveni" ]; then
  echo "sertifikat: koristi se sopstveni sertifikat"
  exit 0
fi

case "$H" in
  *[!0-9.]*) SAN="DNS:$H" ;;
  *) SAN="IP:$H" ;;
esac

if [ -s "$D/server.crt" ] && [ -s "$D/server.key" ] && [ "$(cat "$D/.san" 2>/dev/null)" = "$SAN" ]; then
  echo "sertifikat: postoji za $SAN"
  exit 0
fi

echo "sertifikat: pravim self-signed za $SAN"
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 825 \
  -keyout "$D/server.key" -out "$D/server.crt" \
  -subj "/CN=$H/O=Korisnicki centar demo" \
  -addext "subjectAltName=$SAN,DNS:localhost,IP:127.0.0.1" \
  -addext "keyUsage=digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth" 2>/dev/null
chmod 600 "$D/server.key"
echo "$SAN" > "$D/.san"
