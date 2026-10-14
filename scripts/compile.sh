#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "[*] Compilando programa eBPF (xdp_monitor.c) via Docker..."

sudo docker run --rm -v "$SCRIPT_DIR":/code -w /code ubuntu:22.04 /bin/bash -c "
    apt-get update -qq && \
    apt-get install -y -qq clang llvm libbpf-dev gcc-multilib && \
    clang -g -O2 -target bpf -D__TARGET_ARCH_x86 -c xdp_monitor.c -o xdp_monitor.o
"

if [ -f xdp_monitor.o ]; then
    echo "[✓] Compilação concluída com sucesso: xdp_monitor.o gerado!"
else
    echo "[-] Erro na compilação."
    exit 1
fi
