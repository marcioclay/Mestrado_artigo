#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação Multi-Cenário com S_check e Captura Corrigida
# ==============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Valores padrão
DEFESA="dfa"
CENARIO="todos"
DURACAO=60

# Processar argumentos
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --off|--iptables|--stateless|--stateful|--dfa) DEFESA="${1:2}" ;;
        --legitimo|--atacante|--todos) CENARIO="${1:2}" ;;
        --duracao) DURACAO="$2"; shift ;;
        *) echo "Parâmetro desconhecido: $1"; exit 1 ;;
    esac
    shift
done

PCAP_FILE="${SCRIPT_DIR}/captura_${DEFESA}_${CENARIO}.pcap"
REL_FILE="${SCRIPT_DIR}/relatorio_${DEFESA}_${CENARIO}.md"

echo "======================================================="
echo " 🚀 EXECUTANDO EXPERIMENTO"
echo " Defesa:  ${DEFESA^^}"
echo " Cenário: ${CENARIO^^}"
echo " Duração: ${DURACAO}s"
echo "======================================================="

# [1/8] Higienização
echo "[1/8] Limpando ambiente e redefinindo conexões..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-mqtt pkill -9 -f mosquitto 2>/dev/null || true
sleep 1

# Garante que o arquivo CSV de métricas antigo seja apagado
rm -f "${SCRIPT_DIR}/s_check_metrics.csv"
rm -f "${SCRIPT_DIR}/mensagens_recebidas.log"

docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 2

# [2/8] Carregar Defesa
echo "[2/8] Aplicando defesa no Gateway ($DEFESA)..."
"${SCRIPT_DIR}/load_xdp.sh" "$DEFESA"
sleep 2

# [3/8] Captura tcpdump e Log MQTT
echo "[3/8] Iniciando captura tcpdump na interface interna eth1 ($PCAP_FILE)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth1 -n 'tcp port 1883' -w $PCAP_FILE >/dev/null 2>&1"
# Coleta de mensagens recebidas (Subscriber legítimo extra para validação)
docker exec -d clab-seg-mqtt bash -c "mosquitto_sub -h 10.0.2.10 -t 'iot/#' > /scripts/mensagens_recebidas.log"

# NOVO: Iniciar Monitor de Disponibilidade S_check
echo "      Iniciando monitoramento S_check em segundo plano..."
# Executa o s_check a partir do Gateway simulando uma conexão externa
docker exec -d clab-seg-gateway python3 /scripts/s_check.py --duracao $DURACAO

# [4/8] Sensores Legítimos
if [[ "$CENARIO" == "legitimo" || "$CENARIO" == "todos" ]]; then
    echo "[4/8] Disparando os 3 sensores legítimos..."
    docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
    docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
    docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
else
    echo "[4/8] Pulo: Sensores legítimos desativados neste cenário."
fi
sleep 3

# [5/8] Ataque Multi-Bot
if [[ "$CENARIO" == "atacante" || "$CENARIO" == "todos" ]]; then
    echo "[5/8] Disparando Ataque SlowTT Multi-Bot (31 IPs)..."
    docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py -c 310 -wt 15"
else
    echo "[5/8] Pulo: Ataque desativado neste cenário."
fi

# [6/8] Execução do Teste
echo "[6/8] Aguardando duração do experimento ($DURACAO segundos)..."
sleep $((DURACAO - 10))

# [7/8] Coleta e Encerramento
echo "[7/8] Encerrando processos de rede e ataque..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
sleep 2 # Dá tempo pro tcpdump escrever no disco
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# [8/8] Relatório
echo "[8/8] Consolidação do relatório..."
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$DEFESA" "$CENARIO"

echo ""
echo "======================================================="
echo " 📊 RESULTADO GRAVADO EM: $REL_FILE"
echo "======================================================="
