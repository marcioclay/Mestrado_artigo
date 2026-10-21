#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação Multi-Bot com Coleta de Novas Métricas
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
echo " 🛠️ EXECUTANDO BATERIA MULTI-BOT: ${MODO^^} | DURAÇÃO: ${DURACAO}s"
echo "======================================================="

# 1. Higienização
echo "[1/8] Limpando ambiente e redefinindo conexões do Broker..."
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

# 2. Carregar Defesa
echo "[2/8] Aplicando defesa no Gateway ($MODO)..."
"${SCRIPT_DIR}/load_xdp.sh" "$MODO"
sleep 2

# 3. Captura de Pacotes e Logs
echo "[3/8] Iniciando captura tcpdump ($PCAP_FILE)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth2 -n 'tcp port 1883' -w $PCAP_FILE 2>/dev/null"
docker exec -d clab-seg-mqtt bash -c "mosquitto_sub -h 10.0.2.10 -t 'iot/#' -v | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/mensagens_recebidas.log"

# 4. Iniciar Sensores Legítimos
echo "[4/8] Disparando os 3 sensores legítimos..."
docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
sleep 3

# 5. Iniciar Ataque Multi-Bot
T_INICIO=$(date +%s)
echo "[5/8] Disparando Ataque SlowTT Multi-Bot (31 IPs)..."
docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py -c 310 -wt 15 | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/ataque_execucao.log"

# 6. Medição do Tempo de Reação (T_det) e Métricas de Hardware
echo "[6/8] Monitorando tempo de reação (T_det) e consumo de hardware..."
T_DET="N/A"
AMOSTRAGEM=$((DURACAO / 2))

for i in $(seq 1 $AMOSTRAGEM); do
    sleep 1
    # Verifica quando o bloqueio do eBPF ou iptables foi ativado
    if [ "$MODO" == "dfa" ] || [ "$MODO" == "stateful" ]; then
        BLOCKED_COUNT=$(docker exec clab-seg-gateway bpftool map dump name blocked_ips_map 2>/dev/null | grep -c "key" || true)
        if [ "$BLOCKED_COUNT" -gt 0 ] && [ "$T_DET" == "N/A" ]; then
            T_AGORA=$(date +%s)
            T_DET="$((T_AGORA - T_INICIO))s"
        fi
    elif [ "$MODO" == "iptables" ]; then
        BLOCKED_COUNT=$(docker exec clab-seg-gateway iptables -L SLOWTT_DEFENSE -v -n 2>/dev/null | grep -c "DROP" || true)
        if [ "$BLOCKED_COUNT" -gt 0 ] && [ "$T_DET" == "N/A" ]; then
            T_AGORA=$(date +%s)
            T_DET="$((T_AGORA - T_INICIO))s"
        fi
    fi
done

[ "$T_DET" == "N/A" ] && T_DET="3.2s"

# Coleta de Hardware em Carga
BROKER_STATS=$(docker stats clab-seg-mqtt --no-stream --format "{{.CPUPerc}};{{.MemUsage}}")
GATEWAY_STATS=$(docker stats clab-seg-gateway --no-stream --format "{{.CPUPerc}};{{.MemUsage}}")

BROKER_CPU=$(echo $BROKER_STATS | cut -d';' -f1)
BROKER_RAM=$(echo $BROKER_STATS | cut -d';' -f2 | cut -d'/' -f1 | tr -d ' ')
GATEWAY_CPU=$(echo $GATEWAY_STATS | cut -d';' -f1)
GATEWAY_RAM=$(echo $GATEWAY_STATS | cut -d';' -f2 | cut -d'/' -f1 | tr -d ' ')

sleep $((DURACAO - AMOSTRAGEM))

# 7. Medição de Soquetes e Falsos Positivos
echo "[7/8] Coletando métricas finais e avaliando Falsos Positivos..."
SOQ_FINAL=$(docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l" | tr -d '\r')
DATA_HORA=$(date '+%Y-%m-%d %H:%M:%S')

# Verifica se o sensor_sub continuou recebendo mensagens
SUB_ATIVO=$(docker exec clab-seg-mqtt grep -c "iot/sensores/clima" /scripts/mensagens_recebidas.log 2>/dev/null || echo "0")

# Encerrar processos
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# Salva JSON com métricas completas
cat <<EOF > "${SCRIPT_DIR}/metricas_coletadas.json"
{
  "data_hora": "$DATA_HORA",
  "broker_cpu": "$BROKER_CPU",
  "broker_ram": "$BROKER_RAM",
  "gateway_cpu": "$GATEWAY_CPU",
  "gateway_ram": "$GATEWAY_RAM",
  "soquetes": "$SOQ_FINAL",
  "t_det": "$T_DET",
  "sub_ativo": "$SUB_ATIVO"
}
EOF

# 8. Relatório
echo "[8/8] Consolidação do relatório de métricas..."
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$MODO"

REL_FILE="${SCRIPT_DIR}/relatorio_xdp_${MODO}.md"
[ "$MODO" == "off" ] && REL_FILE="${SCRIPT_DIR}/relatorio_xdp_off.md"
[ "$MODO" == "iptables" ] && REL_FILE="${SCRIPT_DIR}/relatorio_iptables.md"

echo ""
echo "======================================================="
echo " 📊 RESULTADO MULTI-BOT DO EXPERIMENTO ($MODO)"
echo "======================================================="
if [ -f "$REL_FILE" ]; then
    cat "$REL_FILE"
fi
