#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação Otimizada do Experimento
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

echo "======================================================="
echo " 🚀 EXECUTANDO EXPERIMENTO"
echo " Defesa:  ${DEFESA^^}"
echo " Cenário: ${CENARIO^^}"
echo " Duração: ${DURACAO}s"
echo "======================================================="

# [1/8] Higienização Limpa
echo "[1/8] Limpando ambiente e redefinindo conexões..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-mqtt pkill -9 -f mosquitto 2>/dev/null || true
sleep 1

# Limpa logs do ensaio anterior
rm -f "${SCRIPT_DIR}/s_check_metrics.csv"
rm -f "${SCRIPT_DIR}/mensagens_recebidas.log"
rm -f "${SCRIPT_DIR}/soquetes_pico.txt"
rm -f "${HOST_PCAP}"

# Reinicia Mosquitto limpo
docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 1

# [2/8] Carregar Defesa no Gateway
echo "[2/8] Aplicando defesa no Gateway ($DEFESA)..."
"${SCRIPT_DIR}/load_xdp.sh" "$DEFESA"

# [3/8] Captura tcpdump e Log MQTT
echo "[3/8] Iniciando captura tcpdump na interface eth1 ($CONTAINER_PCAP)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth1 -n 'tcp port 1883' -w ${CONTAINER_PCAP} >/dev/null 2>&1"
docker exec -d clab-seg-mqtt bash -c "mosquitto_sub -h 10.0.2.10 -t 'iot/#' -v > /scripts/mensagens_recebidas.log 2>&1"

# Iniciar S_check a partir do Sensor de Evento (atravessa a defesa)
echo "      Iniciando monitoramento S_check em segundo plano..."
docker exec -d clab-seg-sensor-evento python3 /scripts/s_check.py --duracao $DURACAO

# [4/8] Sensores Legítimos
if [[ "$CENARIO" == "legitimo" || "$CENARIO" == "todos" ]]; then
    echo "[4/8] Disparando os 3 sensores legítimos..."
    docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
    docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
    docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
else
    echo "[4/8] Pulo: Sensores legítimos desativados."
fi
sleep 1

# [5/8] Ataque Multi-Bot (Garante pool de IPs ativo)
if [[ "$CENARIO" == "atacante" || "$CENARIO" == "todos" ]]; then
    echo "[5/8] Garantindo pool de IPs e disparando Ataque SlowTT Multi-Bot (31 IPs)..."
    docker exec clab-seg-atacante bash -c "for i in \$(seq 21 50); do ip addr add 10.0.1.\$i/24 dev eth1 2>/dev/null || true; done"
    docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py -c 310 -wt 15"
else
    echo "[5/8] Pulo: Ataque desativado."
fi

# [6/8] Execução do Teste (Dividida para capturar o pico)
MEIO=$((DURACAO / 2))
RESTO=$((DURACAO - MEIO))
echo "[6/8] Aguardando duração do experimento ($DURACAO segundos)..."
sleep $MEIO

echo "      [+] Capturando o pico de conexões no Broker a meio do tempo..."
docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l" > "${SCRIPT_DIR}/soquetes_pico.txt"

sleep $RESTO

# [7/8] Encerrar Processos
echo "[7/8] Encerrando geradores de tráfego e salvando capturas..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
sleep 1
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# [8/8] Relatório
echo "[8/8] Consolidação do relatório..."
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$DEFESA" "$CENARIO"

echo "======================================================="
echo " [✓] Teste concluído com sucesso."
echo "======================================================="
