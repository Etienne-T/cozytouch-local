#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
work=$(realpath "$1")
proofs="$here/../preuves"
mkdir -p "$proofs"
cc -DCT_ACK_TEST -Wall -Wextra -Werror -O2 "$here/../src/ack.c" -o "$work/bin/ack-test"
cc -Wall -Wextra -Werror -O2 -shared -fPIC "$here/../src/private.c" -o "$work/bin/libct-safe-test.so"
{
    python3 "$here/test-counter.py" "$work/bin/ack-test"
    python3 "$here/test-private.py" "$work/bin/libct-safe-test.so"
    python3 "$here/test-supervisor.py" "$here/../src/supervise"
} | tee "$proofs/compteur-et-controles.txt"
python3 -u "$here/test-update.py" "$work" | tee "$proofs/mise-a-jour-etats.txt"
python3 -u "$here/test-rescue.py" "$work" | tee "$proofs/secours-qemu.txt"
python3 -u "$here/test-qemu.py" "$work" | tee "$proofs/qemu-arm926.txt"

