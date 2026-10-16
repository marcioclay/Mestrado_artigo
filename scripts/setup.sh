#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
TOPOLOGIA_FILE="$PROJECT_DIR/topologia.yml"

echo "[0/5] Criando a bridge 'br-lan' no host..."
if ! ip link show br-lan > /dev/null 2>&1; then
    sudo ip link add name br-lan type bridge
    sudo ip link set dev br-lan up
fi

echo "[1/5] Subindo a topologia no Containerlab..."
sudo clab deploy -t "$TOPOLOGIA_FILE" --reconfigure

echo "[2/5] Configurando rede no Gateway..."
docker exec clab-seg-gateway bash -c "
  sysctl -w net.ipv4.ip_forward=1 && \
  ip addr add 10.0.1.1/24 dev eth2 2>/dev/null || true && \
  ip addr add 10.0.2.1/24 dev eth1 2>/dev/null || true
"

echo "[3/5] Configurando Broker MQTT..."
docker exec clab-seg-mqtt bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 mosquitto mosquitto-clients python3 python3-pip && \
  ip addr add 10.0.2.10/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.2.1 && \
  mosquitto -c /scripts/mosquitto.conf -d
"

echo "[4/5] Configurando os 3 Sensores Legítimos..."
for sensor in clab-seg-sensor-evento clab-seg-sensor-sub clab-seg-sensor-jitter; do
    ip_last=""
    case $sensor in
        "clab-seg-sensor-evento") ip_last="10" ;;
        "clab-seg-sensor-sub") ip_last="11" ;;
        "clab-seg-sensor-jitter") ip_last="12" ;;
    esac
    
    docker exec $sensor bash -c "
      export DEBIAN_FRONTEND=noninteractive && \
      apt-get update -qq && \
      apt-get install -y -qq iproute2 python3 python3-pip python3-paho-mqtt mosquitto-clients iputils-ping && \
      ip addr add 10.0.1.$ip_last/24 dev eth1 2>/dev/null || true && \
      ip route replace default via 10.0.1.1
    "
done

echo "[5/5] Configurando Atacante (10.0.1.20)..."
docker exec clab-seg-atacante bash -c "
  export DEBIAN_FRONTEND=noninteractive && \
  apt-get update -qq && \
  apt-get install -y -qq iproute2 python3 hping3 iperf3 iputils-ping && \
  ip addr add 10.0.1.20/24 dev eth1 2>/dev/null || true && \
  ip route replace default via 10.0.1.1
"

echo ""
echo "======================================================="
echo "[✓] Ambiente totalmente reconfigurado e pronto!"
echo "======================================================="