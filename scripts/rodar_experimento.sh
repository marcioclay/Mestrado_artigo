#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação Total de Testes e Coleta de Métricas
# ==============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# --- 1. Seleção Interativa do Método ---
MODO=$1
DURACAO=${2:-60} # Tempo de duração do ataque em segundos (padrão: 60s)

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
echo " 🛠️ INICIANDO TESTE: ${MODO^^} | DURAÇÃO: ${DURACAO}s"
echo "======================================================="

# --- 2. Higienização Completa do Ambiente (Evita acúmulo de soquetes) ---
echo "[1/8] Executando higienização do ambiente e limpando soquetes..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true
docker exec clab-seg-mqtt pkill -9 -f mosquitto_sub 2>/dev/null || true

# Reinicia o Mosquitto para liberar 100% dos soquetes em TIME_WAIT
docker exec clab-seg-mqtt bash -c "pkill -9 mosquitto 2>/dev/null || true"
sleep 1
docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 2

SOQ_INICIAL=$(docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l")
echo "[✓] Soquetes ativos no Mosquitto pós-limpeza: $SOQ_INICIAL"

# --- 3. Aplicar Política de Segurança no Gateway ---
echo "[2/8] Aplicando política de defesa no Gateway ($MODO)..."
"${SCRIPT_DIR}/load_xdp_2.sh" "$MODO"
sleep 2

# --- 4. Iniciar Captura de Pacotes (.pcap) e Escuta do Broker ---
echo "[3/8] Iniciando captura de rede tcpdump e logs de escuta..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth2 -n 'tcp port 1883' -w $PCAP_FILE 2>/dev/null"
docker exec -d clab-seg-mqtt bash -c "mosquitto_sub -h 10.0.2.10 -t 'iot/#' -v | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/mensagens_recebidas.log"

# --- 5. Disparar os 3 Sensores Legítimos em Paralelo ---
echo "[4/8] Iniciando os 3 perfis de sensores legítimos (Evento, Subscrição, Jitter)..."
docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
sleep 3

# --- 6. Disparar o Ataque SlowTT ---
echo "[5/8] Disparando gerador de ataque SlowTT..."
docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/ataque_execucao.log"

# --- 7. Monitoramento durante a Execução ---
echo "[6/8] Executando o teste por $DURACAO segundos (aguarde)..."
sleep $((DURACAO / 2))

# Executa teste ad-hoc de disponibilidade no meio do ataque
echo "[*] Disparando teste ad-hoc de disponibilidade do sensor de evento..."
docker exec clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento --teste-disponibilidade &
PID_TESTE=$!

sleep $((DURACAO / 2))
kill $PID_TESTE 2>/dev/null || true

# --- 8. Coleta Final de Métricas ---
echo "[7/8] Finalizando coleta de métricas e estado do kernel..."
SOQ_FINAL=$(docker exec clab-seg-mqtt bash -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l")

# Finalizar processos de captura e geradores
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-sub pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-jitter pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# --- 9. Geração e Exibição do Relatório ---
echo "[8/8] Gerando relatório do experimento e exibindo na tela..."
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$MODO" -y

REL_FILE="${SCRIPT_DIR}/relatorio_xdp_${MODO}.md"
[ "$MODO" == "off" ] && REL_FILE="${SCRIPT_DIR}/relatorio_xdp_off.md"
[ "$MODO" == "iptables" ] && REL_FILE="${SCRIPT_DIR}/relatorio_iptables.md"

echo ""
echo "======================================================="
echo " 📊 RESULTADO DO EXPERIMENTO NO TERMINAL ($MODO)"
echo "======================================================="
if [ -f "$REL_FILE" ]; then
    cat "$REL_FILE"
else
    echo "Conexões ativas no Broker Mosquitto: $SOQ_FINAL"
fi
echo "======================================================="
echo "[✓] Teste concluído com sucesso!"
