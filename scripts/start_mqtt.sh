#!/bin/bash
echo "[*] Iniciando Broker Mosquitto com a configuração customizada..."
mosquitto -c /scripts/mosquitto.conf -d

# Mantém o log ativo para acompanhamento
tail -f /var/log/mosquitto/mosquitto.log 2>/dev/null || sleep infinity
