#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação Total com Coleta Real de Métricas de Hardware
# ==============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

MODO=$1
DURACAO=${2:-60}

if [ -z "$MODO" ]; then
    echo "======================================================="
    echo " 🚀 SELECIONE O MÉTODO DE DEFESA PARA O EXPERIMENTO"
    echo "======================================================="
    echo " [0] off       - Baseline sem proteção (XDP OFF)"
    echo " [1] stateless - XDP Stateless (Rate-limiting L3/L4)"
    echo " [2] stateful  - XDP Stateful Heurístico (Contadores L7 Sem DFA)"
    echo " [3] dfa       - XDP Stateful DFA (Autômato MQTT Proposto)"
    echo " [4] iptables  - Mitigação Netfilter/iptables"
    echo "======================================================="
    read -p "Opção [0/1/2/3/4 ou nome]: " OPCAO
    case $OPCAO in
        0|off)       MODO="off" ;;
        1|stateless) MODO="stateless" ;;
        2|stateful)  MODO="stateful" ;;
        3|dfa)       MODO="dfa" ;;
        4|iptables)  MODO="iptables" ;;
        *)           MODO="dfa" ;;
    esac
fi

PCAP_FILE="${SCRIPT_DIR}/${MODO}.pcap"
[ "$MODO" == "off" ] && PCAP_FILE="${SCRIPT_DIR}/baseline_off.pcap"

echo ""
echo "======================================================="
echo " 🛠️ INICIANDO TESTE REAL: ${MODO^^} | DURAÇÃO: ${DURACAO}s"
echo "======================================================="

# --- 1. Higienização Completa do Ambiente ---
echo "[1/8] Higienizando processos e redefinindo conexões..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true
docker exec clab-seg-mqtt pkill -9 -f mosquitto_sub 2>/dev/null || true

docker exec clab-seg-mqtt bash -c "pkill -9 mosquitto 2>/dev/null || true"
sleep 1
docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 2

# --- 2. Aplicar Política de Segurança ---
echo "[2/8] Aplicando política de defesa ($MODO)..."
"${SCRIPT_DIR}/load_xdp.sh" "$MODO"
sleep 2

# --- 3. Iniciar Captura de Rede e Log de Mensagens ---
echo "[3/8] Iniciando captura tcpdump ($PCAP_FILE)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth2 -n 'tcp port 1883' -w $PCAP_FILE 2>/dev/null"
docker exec -d clab-seg-mqtt bash -c "mosquitto_sub -h 10.0.2.10 -t 'iot/#' -v | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/mensagens_recebidas.log"

# --- 4. Disparar Sensores Legítimos ---
echo "[4/8] Disparando os 3 perfis de sensores legítimos..."
docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
sleep 3

# --- 5. Disparar Ataque SlowTT ---
echo "[5/8] Disparando gerador de ataque SlowTT..."
docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/ataque_execucao.log"

# --- 6. Aguardar e Coletar Métricas Reais de Hardware no Pico da Carga ---
AMOSTRAGEM=$((DURACAO / 2))
echo "[6/8] Executando o teste por $DURACAO segundos (coletando métricas reais aos ${AMOSTRAGEM}s)..."
sleep $AMOSTRAGEM

echo "[*] Capturando consumo de CPU/RAM real no Docker durante a carga..."
BROKER_STATS=$(docker stats clab-seg-mqtt --no-stream --format "{{.CPUPerc}};{{.MemUsage}}")
GATEWAY_STATS=$(docker stats clab-seg-gateway --no-stream --format "{{.CPUPerc}};{{.MemUsage}}")

BROKER_CPU=$(echo $BROKER_STATS | cut -d';' -f1)
BROKER_RAM=$(echo $BROKER_STATS | cut -d';' -f2 | cut -d'/' -f1 | tr -d ' ')

GATEWAY_CPU=$(echo $GATEWAY_STATS | cut -d';' -f1)
GATEWAY_RAM=$(echo $GATEWAY_STATS | cut -d';' -f2 | cut -d'/' -f1 | tr -d ' ')

sleep $((DURACAO - AMOSTRAGEM))

# --- 7. Finalizar Processos e Ler Soquetes Ativos Reais ---
echo "[7/8] Medindo soquetes TCP estabelecidos reais no Broker..."
SOQ_FINAL=$(docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l" | tr -d '\r')
DATA_HORA=$(date '+%Y-%m-%d %H:%M:%S')

# Encerrar geradores de tráfego
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# Salvar arquivo JSON temporário com as medições reais
cat <<EOF > "${SCRIPT_DIR}/metricas_coletadas.json"
{
  "data_hora": "$DATA_HORA",
  "broker_cpu": "$BROKER_CPU",
  "broker_ram": "$BROKER_RAM",
  "gateway_cpu": "$GATEWAY_CPU",
  "gateway_ram": "$GATEWAY_RAM",
  "soquetes": "$SOQ_FINAL"
}
EOF

# --- 8. Gerar e Exibir o Relatório Real ---
echo "[8/8] Consolidação e exibição do relatório dinâmico..."
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$MODO"

REL_FILE="${SCRIPT_DIR}/relatorio_xdp_${MODO}.md"
[ "$MODO" == "off" ] && REL_FILE="${SCRIPT_DIR}/relatorio_xdp_off.md"
[ "$MODO" == "iptables" ] && REL_FILE="${SCRIPT_DIR}/relatorio_iptables.md"

echo ""
echo "======================================================="
echo " 📊 RESULTADO EXPERIMENTAL REAL ($MODO)"
echo "======================================================="
if [ -f "$REL_FILE" ]; then
    cat "$REL_FILE"
fi
echo "======================================================="
echo "[✓] Teste concluído com métricas empíricas coletadas."
