#!/bin/bash
# Script de gerenciamento da camada de inspeção e mitigação no Gateway

IFACE="eth2"                             # Interface voltada para a LAN (br-lan / Sensor / Atacante)
GATEWAY="clab-seg-gateway"              # Nome exato do container no Containerlab
PROG_PATH="/scripts/xdp_monitor.o"      # Caminho montado via volume no container
PIN_PATH="/sys/fs/bpf/xdp_monitor"

limpar_defesa() {
    echo "[*] Desativando configurações e limpando mapas pinados..."
    
    # 1. Limpa regras de firewall do Netfilter
    docker exec $GATEWAY iptables -F 2>/dev/null || true
    
    # 2. Desanexa o programa XDP da interface
    docker exec $GATEWAY ip link set dev $IFACE xdpgeneric off 2>/dev/null || true
    docker exec $GATEWAY ip link set dev $IFACE xdp off 2>/dev/null || true
    
    # 3. Remove mapas e programas pinados no BPF FS
    docker exec $GATEWAY rm -f $PIN_PATH 2>/dev/null || true
    docker exec $GATEWAY rm -f /sys/fs/bpf/estatisticas 2>/dev/null || true
    docker exec $GATEWAY rm -f /sys/fs/bpf/ips_detectados 2>/dev/null || true
}

if [ "$1" == "xdp" ]; then
    limpar_defesa
    echo "[*] Carregando e pino do programa XDP..."
    docker exec $GATEWAY bpftool prog load $PROG_PATH $PIN_PATH type xdp pinmaps /sys/fs/bpf/
    
    echo "[*] Anexando o filtro XDP à interface $IFACE..."
    docker exec $GATEWAY ip link set dev $IFACE xdpgeneric pinned $PIN_PATH
    echo "--- MONITORAMENTO XDP ATIVADO ---"

elif [ "$1" == "iptables" ]; then
    limpar_defesa
    echo "[*] Ativando regra de mitigação via Iptables..."
    docker exec $GATEWAY iptables -A FORWARD -p tcp --dport 1883 -m connlimit --connlimit-above 50 -j DROP
    echo "--- IPTABLES ATIVADO ---"

elif [ "$1" == "off" ]; then
    limpar_defesa
    echo "--- DEFESA/MONITORAMENTO DESATIVADO ---"
    
else
    echo "Uso: ./load_xdp.sh [xdp|iptables|off]"
fi
