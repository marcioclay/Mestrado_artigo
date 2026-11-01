#!/bin/bash
# load_xdp.sh - Gerenciador dos Modos de Defesa no Gateway

IFACE="eth2"
GATEWAY="clab-seg-gateway"
PIN_PATH="/sys/fs/bpf/xdp_prog"

limpar_defesa() {
    echo "[*] Limpando filtros e regras anteriores..."
    docker exec $GATEWAY iptables -F 2>/dev/null || true
    docker exec $GATEWAY iptables -X SLOWTT_DEFENSE 2>/dev/null || true
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
    echo "[*] Ativando Mitigação Avançada contra SlowTT via iptables..."
    
    # 1. Criação da sub-cadeia isolada de mitigação
    docker exec $GATEWAY iptables -N SLOWTT_DEFENSE
    docker exec $GATEWAY iptables -A FORWARD -p tcp --dport 1883 -j SLOWTT_DEFENSE

    # 2. Fast-Path: Bloqueio automático de IPs contidos na Blacklist Dinâmica
    docker exec $GATEWAY iptables -A SLOWTT_DEFENSE -m recent --name SLOWTT_BLACKLIST --update --seconds 3600 -j DROP

    # 3. Limite de Conexões Concorrentes (connlimit > 10) -> Adiciona à Blacklist e Descarta
    docker exec $GATEWAY iptables -A SLOWTT_DEFENSE -p tcp -m state --state NEW -m connlimit --connlimit-above 10 --connlimit-mask 32 -m recent --name SLOWTT_BLACKLIST --set -j DROP
    docker exec $GATEWAY iptables -A SLOWTT_DEFENSE -p tcp -m connlimit --connlimit-above 10 --connlimit-mask 32 -j DROP

    # 4. Limite de Taxa de Abertura de Conexões (> 5 novas conexões em 10 segundos)
    docker exec $GATEWAY iptables -A SLOWTT_DEFENSE -p tcp --dport 1883 -m state --state NEW -m recent --set --name SLOWTT_RATE
    docker exec $GATEWAY iptables -A SLOWTT_DEFENSE -p tcp --dport 1883 -m state --state NEW -m recent --update --seconds 10 --hitcount 6 --name SLOWTT_RATE -m recent --name SLOWTT_BLACKLIST --set -j DROP

    # 5. Inspeção de Payload L7 para PINGREQ sem dados (0xC0 0x00)
    docker exec $GATEWAY iptables -A SLOWTT_DEFENSE -p tcp --dport 1883 -m string --hex-string "|c0 00|" --algo bm -m hashlimit --hashlimit-name mqtt_ping --hashlimit-mode srcip --hashlimit-above 1/sec -j DROP

    echo "--- [✓] MITIGAÇÃO IPTABLES AVANÇADA (SLOWTT) ATIVADA ---"

elif [ "$1" == "off" ]; then
    limpar_defesa
    echo "--- BASELINE (SEM PROTEÇÃO) ATIVADO ---"

else
    echo "Uso: ./load_xdp.sh [dfa|stateful|stateless|iptables|off]"
fi
