#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "[*] Compilando programas eBPF (xdp_monitor_dfa.c e xdp_stateless.c)..."

sudo docker run --rm -v "$SCRIPT_DIR":/code -w /code ubuntu:22.04 /bin/bash -c "
    apt-get update -qq && \
    apt-get install -y -qq clang llvm libbpf-dev gcc-multilib && \
    clang -g -O2 -target bpf -D__TARGET_ARCH_x86 -c xdp_monitor_dfa.c -o xdp_monitor_dfa.o && \
    clang -g -O2 -target bpf -D__TARGET_ARCH_x86 -c xdp_stateless.c -o xdp_stateless.o
"

if [ -f xdp_monitor_dfa.o ] && [ -f xdp_stateless.o ]; then
    echo "[✓] Sucesso! Bytecodes 'xdp_monitor_dfa.o' e 'xdp_stateless.o' gerados."
else
    echo "[-] Falha na compilação do eBPF."
    exit 1
fi