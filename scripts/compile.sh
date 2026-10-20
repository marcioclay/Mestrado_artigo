#!/bin/bash
set -e

echo "[*] Compilando arquivos eBPF/XDP via Clang/LLVM..."

clang -O2 -g -target bpf -c /Mestrado/scripts/xdp_stateless.c -o /Mestrado/scripts/xdp_stateless.o
clang -O2 -g -target bpf -c /Mestrado/scripts/xdp_stateful.c -o /Mestrado/scripts/xdp_stateful.o
clang -O2 -g -target bpf -c /Mestrado/scripts/xdp_monitor_dfa.c -o /Mestrado/scripts/xdp_monitor_dfa.o

echo "[✓] Compilação concluída com sucesso!"
ls -la /Mestrado/scripts/*.o
