#!/usr/bin/env bash

set -Eeuo pipefail

SETUP_STATUS_URL="${SETUP_STATUS_URL:-http://127.0.0.1:8000/api/security/setup-initial-admin/status}"
SETUP_URL="${SETUP_URL:-http://127.0.0.1:8000/api/security/setup-initial-admin}"
APPLICATION_ORIGIN="${APPLICATION_ORIGIN:-https://carequeue.local}"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 \
        || fail "Required command was not found: $1"
}

get_setup_status() {
    curl \
        --silent \
        --show-error \
        --fail \
        "${SETUP_STATUS_URL}"
}

setup_is_available() {
    local response

    response="$(get_setup_status)" \
        || fail "Unable to check CareQueue initial admin setup status."

    python3 - "${response}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])

raise SystemExit(
    0 if payload.get("setup_available") is True else 1
)
PY
}

create_admin() {
    local username
    local password
    local password_confirmation
    local payload_file
    local response_file
    local http_status

    printf '\n'
    printf 'CareQueue First-Time Admin Setup\n'
    printf '================================\n\n'

    read -r -p 'Admin username: ' username

    if [[ -z "${username}" ]]; then
        fail "Admin username cannot be empty."
    fi

    while true; do
        read -r -s -p 'Admin password: ' password
        printf '\n'

        read -r -s -p 'Confirm admin password: ' password_confirmation
        printf '\n'

        if [[ "${password}" != "${password_confirmation}" ]]; then
            printf 'Passwords do not match. Try again.\n\n'
            continue
        fi

        break
    done

    response_file="$(mktemp)"
    payload_file="$(mktemp)"

    trap 'rm -f "${response_file}" "${payload_file}"' EXIT

USERNAME="${username}" \
PASSWORD="${password}" \
python3 - "${payload_file}" <<'PY'
import json
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

path.write_text(
    json.dumps(
        {
            "username": os.environ["USERNAME"],
            "password": os.environ["PASSWORD"],
        }
    )
)
PY

    chmod 0600 "${payload_file}"

    unset password
    unset password_confirmation

    http_status="$(
        curl \
            --silent \
            --show-error \
            --output "${response_file}" \
            --write-out '%{http_code}' \
            --request POST \
            --header 'Content-Type: application/json' \
            --data-binary "@${payload_file}" \
            "${SETUP_URL}"
    )"

    if [[ "${http_status}" == "201" ]]; then
        printf '\nInitial administrator account created successfully.\n'
        printf 'Open CareQueue at: %s\n' "${APPLICATION_ORIGIN}"

        return
    fi

    printf '\nCareQueue rejected the setup request.\n'

    if [[ -s "${response_file}" ]]; then
        python3 - "${response_file}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

try:
    payload = json.loads(path.read_text())
except Exception:
    print(path.read_text())
else:
    detail = payload.get("detail")

    if detail:
        print(detail)
    else:
        print(json.dumps(payload))
PY
    fi

    fail "Initial administrator account was not created."
}

main() {
    require_command curl
    require_command python3

    if ! setup_is_available; then
        printf 'Initial admin setup is already complete.\n'
        printf 'Open CareQueue at: %s\n' "${APPLICATION_ORIGIN}"
        exit 0
    fi

    create_admin
}

main "$@"