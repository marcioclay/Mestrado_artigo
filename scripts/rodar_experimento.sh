#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Foco EXCLUSIVO em 6 Métricas
# ==============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DEFESA="dfa"
CENARIO="todos"
DURACAO=600

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --off|--iptables|--stateless|--stateful|--dfa) DEFESA="${1:2}" ;;
        --legitimo|--atacante|--todos) CENARIO="${1:2}" ;;
        --duracao) DURACAO="$2"; shift ;;
        *) echo "Parâmetro desconhecido: $1"; exit 1 ;;
    esac
    shift
done

NOME_PCAP="captura_${DEFESA}_${CENARIO}.pcap"
CONTAINER_PCAP="/scripts/${NOME_PCAP}"

# Arquivos de métricas puras
NCONN_CSV="${SCRIPT_DIR}/nconn_series.csv"
RECURSOS_CSV="${SCRIPT_DIR}/recursos_series.csv"
LATENCIA_CSV="${SCRIPT_DIR}/latencia_mensagens.csv"
ENVIOS_EVENTO_CSV="${SCRIPT_DIR}/envios_evento.csv"
ENVIOS_JITTER_CSV="${SCRIPT_DIR}/envios_jitter.csv"
TENTATIVAS_ATAQUE_CSV="${SCRIPT_DIR}/ataque_tentativas.csv"

echo "======================================================="
echo " 🚀 EXECUTANDO EXPERIMENTO - FOCO EM 6 MÉTRICAS"
echo " Defesa:  ${DEFESA^^} | Cenário: ${CENARIO^^} | Duração: ${DURACAO}s"
echo "======================================================="

echo "[1/7] Limpando ambiente e arquivos anteriores..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true
docker exec clab-seg-mqtt pkill -9 -f mosquitto 2>/dev/null || true
sleep 1

rm -f "${LATENCIA_CSV}" "${ENVIOS_EVENTO_CSV}" "${ENVIOS_JITTER_CSV}" "${TENTATIVAS_ATAQUE_CSV}"
rm -f "${NCONN_CSV}" "${RECURSOS_CSV}" "${SCRIPT_DIR}/${NOME_PCAP}"

docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 1

echo "[2/7] Aplicando defesa no Gateway ($DEFESA)..."
"${SCRIPT_DIR}/load_xdp.sh" "$DEFESA"

echo "[3/7] Iniciando tcpdump (Vazão) e Amostragens (Nconn, CPU/RAM)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -U -i eth1 -n 'tcp port 1883' -w ${CONTAINER_PCAP} >/dev/null 2>&1"

echo "timestamp,nconn_estab" > "${NCONN_CSV}"
echo "timestamp,cpu_broker,ram_broker,cpu_gateway,ram_gateway" > "${RECURSOS_CSV}"

# Loop Python para Nconn e Recursos (Sem dependência de AWK)
(
    while true; do
        t_inicio=$(python3 -c "import time; print(time.time())")
        TS=$(python3 -c "import datetime; print(datetime.datetime.now().strftime('%H:%M:%S'))")
        
        # Coleta Nconn
        NCONN=$(docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l" 2>/dev/null || echo "0")
        echo "${TS},${NCONN}" >> "${NCONN_CSV}"
        
        # Coleta CPU/RAM
        STATS_MQTT=$(docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' clab-seg-mqtt 2>/dev/null || echo "0%|0MB")
        STATS_GW=$(docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' clab-seg-gateway 2>/dev/null || echo "0%|0MB")
        
        CPU_MQTT=$(echo "$STATS_MQTT" | cut -d'|' -f1)
        RAM_MQTT=$(echo "$STATS_MQTT" | cut -d'|' -f2 | cut -d'/' -f1 | xargs)
        CPU_GW=$(echo "$STATS_GW" | cut -d'|' -f1)
        RAM_GW=$(echo "$STATS_GW" | cut -d'|' -f2 | cut -d'/' -f1 | xargs)
        
        echo "${TS},${CPU_MQTT},${RAM_MQTT},${CPU_GW},${RAM_GW}" >> "${RECURSOS_CSV}"
        
        t_fim=$(python3 -c "import time; print(time.time())")
        dormir=$(python3 -c "d=1-($t_fim-$t_inicio); print(d if d>0 else 0)")
        sleep "$dormir"
    done
) &
AMOSTRAGEM_PID=$!

echo "[4/7] Disparando Sensores Legítimos (Latência e Telemetria)..."
if [[ "$CENARIO" == "legitimo" || "$CENARIO" == "todos" ]]; then
    docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
    docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
    docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
fi

echo "[5/7] Disparando Ataque SlowTT (PDR do Atacante)..."
if [[ "$CENARIO" == "atacante" || "$CENARIO" == "todos" ]]; then
    docker exec clab-seg-atacante bash -c "for i in \$(seq 21 50); do ip addr add 10.0.1.\$i/24 dev eth1 2>/dev/null || true; done"
    docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py -c 1100 -wt 15"
fi

echo "[6/7] Aguardando o tempo do experimento ($DURACAO segundos)..."
sleep "$DURACAO"

echo "[7/7] Encerrando captura e gerando o relatório focado nas 6 métricas..."
kill "$AMOSTRAGEM_PID" 2>/dev/null || true
wait "$AMOSTRAGEM_PID" 2>/dev/null || true

docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
sleep 1

docker exec clab-seg-gateway pkill -f tcpdump 2>/dev/null || true
sleep 2

python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$DEFESA" "$CENARIO"
