#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação do Experimento (v2)
# Corrige, em relação à versão anterior:
#   1. S_check agora roda em container dedicado (clab-seg-monitor-scheck),
#      não mais dentro de clab-seg-sensor-evento (evita contaminação do
#      estado do autômato, que é chaveado por IP)
#   2. Encerramento do S_check por PID próprio, não mais via
#      "pkill -9 -f python3" genérico (que podia truncar o CSV do S_check
#      ao matar também o sensor.py do mesmo container)
#   3. Nconn, CPU e RAM deixam de ser amostra única no meio do teste e
#      passam a ser amostrados continuamente (1 amostra/s) do início ao
#      fim da janela de tráfego, salvos em metricas_tempo_real.csv
# ==============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DEFESA="dfa"
CENARIO="todos"
DURACAO=60

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
HOST_PCAP="${SCRIPT_DIR}/${NOME_PCAP}"
CONTAINER_PCAP="/scripts/${NOME_PCAP}"
REL_FILE="${SCRIPT_DIR}/relatorio_${DEFESA}_${CENARIO}.md"
METRICAS_CSV="${SCRIPT_DIR}/metricas_tempo_real_${DEFESA}_${CENARIO}.csv"
SCHECK_PID_FILE="${SCRIPT_DIR}/scheck.pid"
MONITOR_PID_FILE="${SCRIPT_DIR}/monitor_amostragem.pid"

echo "======================================================="
echo " 🚀 EXECUTANDO EXPERIMENTO"
echo " Defesa:  ${DEFESA^^}"
echo " Cenário: ${CENARIO^^}"
echo " Duração: ${DURACAO}s"
echo "======================================================="

# [1/9] Higienização Limpa
echo "[1/9] Limpando ambiente e redefinindo conexões..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-monitor-scheck pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-mqtt pkill -9 -f mosquitto 2>/dev/null || true
sleep 1

# Limpa logs e PIDs do ensaio anterior
rm -f "${SCRIPT_DIR}/s_check_metrics.csv"
rm -f "${SCRIPT_DIR}/mensagens_recebidas.log"
rm -f "${SCRIPT_DIR}/latencia_mensagens.csv"
rm -f "${METRICAS_CSV}"
rm -f "${SCHECK_PID_FILE}"
rm -f "${MONITOR_PID_FILE}"
rm -f "${HOST_PCAP}"

# Reinicia Mosquitto limpo
docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 1

# [2/9] Carregar Defesa no Gateway
echo "[2/9] Aplicando defesa no Gateway ($DEFESA)..."
"${SCRIPT_DIR}/load_xdp.sh" "$DEFESA"

# [3/9] Captura tcpdump e Log MQTT
echo "[3/9] Iniciando captura tcpdump na interface eth1 ($CONTAINER_PCAP)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth0 -n 'tcp port 1883' -w ${CONTAINER_PCAP} >/dev/null 2>&1"
docker exec -d clab-seg-mqtt bash -c "mosquitto_sub -h 10.0.2.10 -t 'iot/#' -v > /scripts/mensagens_recebidas.log 2>&1"

# [4/9] Monitor de Disponibilidade (S_check) em container dedicado
echo "[4/9] Iniciando S_check em container isolado (clab-seg-monitor-scheck)..."
docker exec -d clab-seg-monitor-scheck bash -c \
    "python3 /scripts/s_check.py --duracao $DURACAO & echo \$! > /scripts/scheck.pid"
sleep 1
if docker exec clab-seg-monitor-scheck test -f /scripts/scheck.pid; then
    docker exec clab-seg-monitor-scheck cat /scripts/scheck.pid > "${SCHECK_PID_FILE}"
    echo "      S_check ativo (PID remoto: $(cat "${SCHECK_PID_FILE}"))"
else
    echo "      [!] Aviso: não foi possível capturar PID do S_check; encerramento usará fallback pkill."
fi

# [5/9] Amostragem Contínua de CPU, RAM e Nconn (1 amostra/segundo)
echo "[5/9] Iniciando amostragem contínua de CPU/RAM/Nconn em segundo plano..."
echo "timestamp,cpu_broker,ram_broker,cpu_gateway,ram_gateway,nconn_estab" > "${METRICAS_CSV}"
(
    while true; do
        TS=$(date '+%Y-%m-%d %H:%M:%S.%3N')
        STATS_MQTT=$(docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' clab-seg-mqtt 2>/dev/null || echo "N/A|N/A")
        STATS_GW=$(docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' clab-seg-gateway 2>/dev/null || echo "N/A|N/A")
        CPU_MQTT=$(echo "$STATS_MQTT" | cut -d'|' -f1)
        RAM_MQTT=$(echo "$STATS_MQTT" | cut -d'|' -f2 | cut -d'/' -f1 | xargs)
        CPU_GW=$(echo "$STATS_GW" | cut -d'|' -f1)
        RAM_GW=$(echo "$STATS_GW" | cut -d'|' -f2 | cut -d'/' -f1 | xargs)
        NCONN=$(docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l" 2>/dev/null || echo "0")
        echo "${TS},${CPU_MQTT},${RAM_MQTT},${CPU_GW},${RAM_GW},${NCONN}" >> "${METRICAS_CSV}"
        sleep 1
    done
) &
MONITOR_PID=$!
echo "$MONITOR_PID" > "${MONITOR_PID_FILE}"
echo "      Amostragem ativa (PID local: ${MONITOR_PID}) -> ${METRICAS_CSV}"

# [6/9] Sensores Legítimos
if [[ "$CENARIO" == "legitimo" || "$CENARIO" == "todos" ]]; then
    echo "[6/9] Disparando os 3 sensores legítimos..."
    docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
    docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
    docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
else
    echo "[6/9] Pulo: Sensores legítimos desativados."
fi
sleep 1

# [7/9] Ataque Multi-Bot (Garante pool de IPs ativo)
if [[ "$CENARIO" == "atacante" || "$CENARIO" == "todos" ]]; then
    echo "[7/9] Garantindo pool de IPs e disparando Ataque SlowTT Multi-Bot (31 IPs)..."
    docker exec clab-seg-atacante bash -c "for i in \$(seq 21 50); do ip addr add 10.0.1.\$i/24 dev eth1 2>/dev/null || true; done"
    docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py -c 1100 -wt 15"
else
    echo "[7/9] Pulo: Ataque desativado."
fi

# [8/9] Execução do Teste (janela completa; o pico real é extraído depois da série temporal)
echo "[8/9] Aguardando duração do experimento ($DURACAO segundos)..."
sleep "$DURACAO"

# Encerrar amostragem contínua
kill "$MONITOR_PID" 2>/dev/null || true
wait "$MONITOR_PID" 2>/dev/null || true
echo "      Amostragem contínua encerrada (${METRICAS_CSV})."

# Encerrar S_check por PID próprio (fallback: pkill restrito ao container do monitor)
if [[ -f "${SCHECK_PID_FILE}" ]]; then
    SCHECK_PID=$(cat "${SCHECK_PID_FILE}")
    docker exec clab-seg-monitor-scheck kill -9 "$SCHECK_PID" 2>/dev/null || true
else
    docker exec clab-seg-monitor-scheck pkill -9 -f s_check.py 2>/dev/null || true
fi

# [9/9] Encerrar Processos de Tráfego e Salvar Capturas
echo "[9/9] Encerrando geradores de tráfego e salvando capturas..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
sleep 1
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# Relatório
echo "      Consolidando relatório..."
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$DEFESA" "$CENARIO"

echo "======================================================="
echo " [✓] Teste concluído com sucesso."
echo "     Série temporal: ${METRICAS_CSV}"
echo "======================================================="
