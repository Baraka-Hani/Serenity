#!/bin/zsh
# Double-click this file to start the local Serenity app and open account creation.
cd -- "${0:A:h}" || exit 1

if /usr/bin/curl --silent --fail http://127.0.0.1:8765/api/me >/dev/null; then
  /usr/bin/open 'http://127.0.0.1:8765/auth.html?mode=signup'
  exit 0
fi

echo "Starting Serenity at http://127.0.0.1:8765/"
/usr/bin/python3 backend/server.py &
serenity_server_pid=$!
trap 'kill "$serenity_server_pid" 2>/dev/null' EXIT INT TERM
for attempt in {1..30}; do
  if /usr/bin/curl --silent --fail http://127.0.0.1:8765/api/me >/dev/null; then
    /usr/bin/open 'http://127.0.0.1:8765/auth.html?mode=signup'
    wait "$serenity_server_pid"
    exit $?
  fi
  /bin/sleep 0.2
done
echo "Serenity did not start. Check the error above."
exit 1
