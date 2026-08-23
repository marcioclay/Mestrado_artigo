#!/bin/bash
set -e

echo "[1/4] Subindo a topologia no Containerlab..."
sudo clab deploy -t lab.clab.yml --reconfigure

echo "[2/4] Configurando o Broker MQTT (instalando Mosquitto)..."
docker exec -it clab-iot-ebpf-topology-mqtt bash -c "
  apt-get update && \
  apt-get install -y mosquitto mosquitto-clients python3 python3-pip && \
  echo 'listener 1883 0.0.0.0' > /etc/mosquitto/conf.d/custom.conf && \
  echo 'allow_anonymous true' >> /etc/mosquitto/conf.d/custom.conf && \
  echo 'max_connections 1024' >> /etc/mosquitto/conf.d/custom.conf && \
  mosquitto -c /etc/mosquitto/conf.d/custom.conf -d
"

echo "[3/4] Configurando o Sensor (instalando Python e Paho-MQTT)..."
docker exec -it clab-iot-ebpf-topology-sensor bash -c "
  apt-get update && \
  apt-get install -y python3 python3-pip python3-paho-mqtt || pip3 install paho-mqtt
"

echo "[4/4] Configurando o Atacante (instalando dependências)..."
docker exec -it clab-iot-ebpf-topology-atacante bash -c "
  apt-get update && \
  apt-get install -y python3 hping3 iperf3 iproute2 iputils-ping
"

echo ""
echo "======================================================="
echo "[✓] Ambiente configurado e Broker MQTT rodando com sucesso!"
echo "======================================================="
