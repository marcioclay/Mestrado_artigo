#!/bin/bash
set -e

# ==============================================================================
# setup.sh - Configuração de rede e dependências para os nós do Containerlab
# Corrige, em relação à versão anterior:
#   1. Mosquitto nunca era instalado no broker
#   2. IP do broker (10.0.2.2) não batia com BROKER_HOST="10.0.2.10" nos scripts
#   3. Gateway não recebia iptables/tcpdump
#   4. Pool de IPs do atacante incompleto (só .20, faltavam .21-.50)
# ==============================================================================

echo "[1/5] Configurando rede do Gateway eBPF..."
docker exec clab-seg-gateway ip addr add 10.0.1.1/24 dev eth2 2>/dev/null || true
docker exec clab-seg-gateway ip link set dev eth2 up
docker exec clab-seg-gateway ip addr add 10.0.2.1/24 dev eth1 2>/dev/null || true
docker exec clab-seg-gateway ip link set dev eth1 up
docker exec clab-seg-gateway sysctl -w net.ipv4.ip_forward=1

echo "[+] Instalando dependências no Gateway (iptables, tcpdump, bpftool helpers)..."
docker exec clab-seg-gateway bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iptables tcpdump iproute2 python3 python3-pip && \
  pip install paho-mqtt --quiet
" >/dev/null 2>&1

echo "[2/5] Configurando Broker MQTT (Mosquitto) na DMZ..."
# IP alinhado com BROKER_HOST="10.0.2.10" usado em sensor.py, s_check.py e slowtt_attack.py
docker exec clab-seg-mqtt ip addr add 10.0.2.10/24 dev eth1 2>/dev/null || true
docker exec clab-seg-mqtt ip link set dev eth1 up
docker exec clab-seg-mqtt ip route replace default via 10.0.2.1

docker exec clab-seg-mqtt bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq mosquitto mosquitto-clients iproute2 python3 python3-pip
" >/dev/null 2>&1

echo "[3/5] Configurando Sensores e Monitor na LAN (10.0.1.0/24)..."

# Sensor de Evento (.10)
docker exec clab-seg-sensor-evento ip addr add 10.0.1.10/24 dev eth1 2>/dev/null || true
docker exec clab-seg-sensor-evento ip link set dev eth1 up
docker exec clab-seg-sensor-evento ip route replace default via 10.0.1.1

# Sensor Subscritor (.11)
docker exec clab-seg-sensor-sub ip addr add 10.0.1.11/24 dev eth1 2>/dev/null || true
docker exec clab-seg-sensor-sub ip link set dev eth1 up
docker exec clab-seg-sensor-sub ip route replace default via 10.0.1.1

# Sensor Jitter (.12)
docker exec clab-seg-sensor-jitter ip addr add 10.0.1.12/24 dev eth1 2>/dev/null || true
docker exec clab-seg-sensor-jitter ip link set dev eth1 up
docker exec clab-seg-sensor-jitter ip route replace default via 10.0.1.1

# Monitor de Disponibilidade Isolado - S_check (.13)
# Container dedicado: não compartilha IP nem processo com nenhum sensor de aplicação,
# evitando que o estado do autômato (chaveado por IP) confunda monitor com sensor.
docker exec clab-seg-monitor-scheck ip addr add 10.0.1.13/24 dev eth1 2>/dev/null || true
docker exec clab-seg-monitor-scheck ip link set dev eth1 up
docker exec clab-seg-monitor-scheck ip route replace default via 10.0.1.1

echo "[4/5] Configurando Atacante com pool Multi-Bot (10.0.1.20 a 10.0.1.50)..."
docker exec clab-seg-atacante ip addr add 10.0.1.20/24 dev eth1 2>/dev/null || true
docker exec clab-seg-atacante ip link set dev eth1 up
docker exec clab-seg-atacante bash -c "for i in \$(seq 21 50); do ip addr add 10.0.1.\$i/24 dev eth1 2>/dev/null || true; done"
docker exec clab-seg-atacante ip route replace default via 10.0.1.1

echo "[5/5] Instalando dependências (Python3 e paho-mqtt) nos sensores, monitor e atacante..."
for node in sensor-evento sensor-sub sensor-jitter monitor-scheck atacante; do
    docker exec clab-seg-$node bash -c "
      export DEBIAN_FRONTEND=noninteractive && \
      apt-get update -qq && \
      apt-get install -y -qq python3 python3-pip iproute2 iputils-ping mosquitto-clients && \
      pip install paho-mqtt --quiet
    " >/dev/null 2>&1
done

echo ""
echo "======================================================="
echo "[✓] Setup de rede e ambiente concluído com sucesso!"
echo "    Broker MQTT : 10.0.2.10 (alinhado com os scripts)"
echo "    Gateway LAN : 10.0.1.1   | Gateway DMZ: 10.0.2.1"
echo "    Monitor S_check isolado : 10.0.1.13"
echo "    Pool do atacante        : 10.0.1.20 - 10.0.1.50 (31 IPs)"
echo "======================================================="
