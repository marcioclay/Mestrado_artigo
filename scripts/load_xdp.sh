#!/bin/bash
# load_xdp.sh - Gerenciador dos Modos de Defesa no Gateway

IFACE="eth2"
GATEWAY="clab-seg-gateway"
PIN_PATH="/sys/fs/bpf/xdp_prog"

limpar_defesa() {
    echo "[*] Limpando filtros e regras anteriores..."
    docker exec $GATEWAY iptables -F 2>/dev/null || true
    docker exec $GATEWAY ip link set dev $IFACE xdpgeneric off 2>/dev/null || true
    docker exec $GATEWAY ip link set dev $IFACE xdp off 2>/dev/null || true
    docker exec $GATEWAY rm -rf /sys/fs/bpf/* 2>/dev/null || true
}

if [ "$1" == "dfa" ]; then
    limpar_defesa
    echo "[*] Carregando eBPF Stateful (Com Autômato DFA)..."
    docker exec $GATEWAY bpftool prog load /scripts/xdp_monitor_dfa.o $PIN_PATH type xdp pinmaps /sys/fs/bpf/
    docker exec $GATEWAY ip link set dev $IFACE xdpgeneric pinned $PIN_PATH
    echo "--- [✓] MITIGAÇÃO eBPF + DFA ATIVADA ---"

elif [ "$1" == "stateful" ]; then
    limpar_defesa
    echo "[*] Carregando eBPF Stateful Heurístico (Contadores L7 Sem DFA)..."
    docker exec $GATEWAY bpftool prog load /scripts/xdp_stateful.o $PIN_PATH type xdp pinmaps /sys/fs/bpf/
    docker exec $GATEWAY ip link set dev $IFACE xdpgeneric pinned $PIN_PATH
    echo "--- [✓] MITIGAÇÃO eBPF STATEFUL HEURÍSTICA ATIVADA ---"

elif [ "$1" == "stateless" ]; then
    limpar_defesa
    echo "[*] Carregando eBPF Stateless (Sem Autômato / Contadores)..."
    docker exec $GATEWAY bpftool prog load /scripts/xdp_stateless.o $PIN_PATH type xdp pinmaps /sys/fs/bpf/
    docker exec $GATEWAY ip link set dev $IFACE xdpgeneric pinned $PIN_PATH
    echo "--- [✓] MITIGAÇÃO eBPF STATELESS ATIVADA ---"

elif [ "$1" == "iptables" ]; then
    limpar_defesa
    echo "[*] Ativando Mitigação via iptables..."
    docker exec $GATEWAY iptables -A FORWARD -p tcp --dport 1883 -m connlimit --connlimit-above 20 -j DROP
    echo "--- [✓] MITIGAÇÃO IPTABLES ATIVADA ---"

elif [ "$1" == "off" ]; then
    limpar_defesa
    echo "--- BASELINE (SEM PROTEÇÃO) ATIVADO ---"

else
    echo "Uso: ./load_xdp.sh [dfa|stateful|stateless|iptables|off]"
fi
