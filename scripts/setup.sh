#!/bin/bash
set -e

echo "[0/5] Verificando e criando a bridge 'br-lan' no host..."
if ! ip link show br-lan > /dev/null 2>&1; then
    sudo ip link add name br-lan type bridge
    sudo ip link set dev br-lan up
fi

echo "[1/5] Subindo a topologia 'seg' no Containerlab..."
sudo clab deploy -t topologia.yml --reconfigure

echo "[2/5] Configurando rede e instalando ferramentas no Atacante..."
docker exec -it clab-seg-atacante bash -c "
  apt-get update && \
  apt-get install -y iproute2 python3 hping3 iperf3 iputils-ping && \
  ip addr add 10.0.1.20/24 dev eth1 && \
  ip route replace default via 10.0.1.1
"

echo "[3/5] Configurando rede e instalando Mosquitto no Broker MQTT..."
docker exec -it clab-seg-mqtt bash -c "
  apt-get update && \
  apt-get install -y iproute2 mosquitto mosquitto-clients python3 python3-pip && \
  ip addr add 10.0.2.10/24 dev eth1 && \
  ip route replace default via 10.0.2.1 && \
  echo 'listener 1883 0.0.0.0' > /etc/mosquitto/conf.d/custom.conf && \
  echo 'allow_anonymous true' >> /etc/mosquitto/conf.d/custom.conf && \
  echo 'max_connections 1024' >> /etc/mosquitto/conf.d/custom.conf && \
  mosquitto -c /etc/mosquitto/conf.d/custom.conf -d
"

echo "[4/5] Configurando dependências do Python no Sensor (Alpine)..."
docker exec -it clab-seg-sensor sh -c "
  apk add --no-cache python3 py3-pip py3-paho-mqtt 2>/dev/null || pip install paho-mqtt
"

echo "[5/5] Instalando utilitários de monitoramento no Gateway..."
docker exec -it clab-seg-gateway bash -c "
  apt-get update && apt-get install -y htop iperf3 tcpdump 2>/dev/null || true
"

echo ""
echo "======================================================="
echo "[✓] Ambiente 'clab-seg' configurado com sucesso!"
echo "======================================================="
