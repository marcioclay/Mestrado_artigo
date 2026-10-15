#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
TOPOLOGIA_FILE="$PROJECT_DIR/topologia.yml"

echo "[0/6] Verificando e criando a bridge 'br-lan' no host..."
if ! ip link show br-lan > /dev/null 2>&1; then
    sudo ip link add name br-lan type bridge
    sudo ip link set dev br-lan up
fi

echo "[1/6] Subindo a topologia 'seg' no Containerlab..."
echo "[*] Arquivo de topologia: $TOPOLOGIA_FILE"
sudo clab deploy -t "$TOPOLOGIA_FILE" --reconfigure

echo "[2/6] Configurando rede no Gateway..."
docker exec clab-seg-gateway bash -c "
  sysctl -w net.ipv4.ip_forward=1 && \
  ip addr add 10.0.1.1/24 dev eth2 2>/dev/null || true && \
  ip addr add 10.0.2.1/24 dev eth1 2>/dev/null || true
"

echo "[3/6] Configurando Broker MQTT..."
docker exec clab-seg-mqtt bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 mosquitto mosquitto-clients python3 python3-pip && \
  ip addr add 10.0.2.10/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.2.1 && \
  echo 'listener 1883 0.0.0.0' > /etc/mosquitto/conf.d/custom.conf && \
  echo 'allow_anonymous true' >> /etc/mosquitto/conf.d/custom.conf && \
  echo 'max_connections 1024' >> /etc/mosquitto/conf.d/custom.conf && \
  mosquitto -c /etc/mosquitto/conf.d/custom.conf -d
"

echo "[4/6] Configurando os 3 Sensores Legítimos..."
# Sensor Evento (IP: 10.0.1.10)
docker exec clab-seg-sensor-evento bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 python3 python3-pip python3-paho-mqtt iputils-ping && \
  ip addr add 10.0.1.10/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.1.1
"

# Sensor Subscritor (IP: 10.0.1.11)
docker exec clab-seg-sensor-sub bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 python3 python3-pip python3-paho-mqtt iputils-ping && \
  ip addr add 10.0.1.11/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.1.1
"

# Sensor Jitter (IP: 10.0.1.12)
docker exec clab-seg-sensor-jitter bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 python3 python3-pip python3-paho-mqtt iputils-ping && \
  ip addr add 10.0.1.12/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.1.1
"

echo "[5/6] Configurando Atacante (IP: 10.0.1.20)..."
docker exec clab-seg-atacante bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 python3 hping3 iperf3 iputils-ping && \
  ip addr add 10.0.1.20/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.1.1
"

echo "[6/6] Instalando utilitários no Gateway..."
docker exec clab-seg-gateway bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && apt-get install -y -qq htop iperf3 tcpdump || true
"

echo ""
echo "======================================================="
echo "[✓] Ambiente 'clab-seg' reconfigurado com 3 perfis de sensores!"
echo "======================================================="
