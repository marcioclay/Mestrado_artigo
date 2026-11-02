#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[*] Compilando arquivos eBPF/XDP via Clang/LLVM..."

clang -O2 -g -target bpf -c "${SCRIPT_DIR}/xdp_stateless.c" -o "${SCRIPT_DIR}/xdp_stateless.o"
clang -O2 -g -target bpf -c "${SCRIPT_DIR}/xdp_stateful.c" -o "${SCRIPT_DIR}/xdp_stateful.o"
clang -O2 -g -target bpf -c "${SCRIPT_DIR}/xdp_monitor_dfa.c" -o "${SCRIPT_DIR}/xdp_monitor_dfa.o"

echo "[✓] Compilação concluída com sucesso!"
ls -la "${SCRIPT_DIR}"/*.o
