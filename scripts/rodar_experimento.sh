#!/bin/bash
# ==============================================================================
# rodar_experimento.sh - Automação Multi-Cenário e Defesas 
# ==============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Valores padrão
DEFESA="dfa"
CENARIO="todos"
DURACAO=60

# Processar os argumentos passados no terminal
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --off|--iptables|--stateful|--dfa) DEFESA="${1:2}" ;; # Remove os '--' para pegar o nome
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

# [1/8] Higienização (Mantém igual ao seu script original)
echo "[1/8] Limpando ambiente e redefinindo conexões..."
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-sensor-evento pkill -9 -f python3 2>/dev/null || true
# ... (restante dos comandos de kill do seu script[cite: 6])

docker exec clab-seg-mqtt bash -c "mosquitto -c /scripts/mosquitto.conf -d"
sleep 2

# [2/8] Carregar Defesa (Mantém igual)
echo "[2/8] Aplicando defesa no Gateway ($DEFESA)..."
"${SCRIPT_DIR}/load_xdp.sh" "$DEFESA"
sleep 2

# [3/8] Captura
echo "[3/8] Iniciando captura tcpdump ($PCAP_FILE)..."
docker exec -d clab-seg-gateway bash -c "tcpdump -i eth2 -n 'tcp port 1883' -w $PCAP_FILE 2>/dev/null"

# =====================================================
# A MÁGICA DOS CENÁRIOS ACONTECE AQUI (Etapas 4 e 5)
# =====================================================

# [4/8] Iniciar Sensores Legítimos (Somente se for 'legitimo' ou 'todos')
if [[ "$CENARIO" == "legitimo" || "$CENARIO" == "todos" ]]; then
    echo "[4/8] Disparando os 3 sensores legítimos..."
    docker exec -d clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
    docker exec -d clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
    docker exec -d clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
else
    echo "[4/8] Pulo: Sensores legítimos desativados neste cenário."
fi
sleep 3

# [5/8] Iniciar Ataque Multi-Bot (Somente se for 'atacante' ou 'todos')
T_INICIO=$(date +%s)
if [[ "$CENARIO" == "atacante" || "$CENARIO" == "todos" ]]; then
    echo "[5/8] Disparando Ataque SlowTT Multi-Bot (31 IPs)..."
    docker exec -d clab-seg-atacante bash -c "python3 /scripts/slowtt_attack.py -c 310 -wt 15"
else
    echo "[5/8] Pulo: Ataque desativado neste cenário."
fi

# [6/8] Medição do Tempo de Reação e Hardware (Mantém igual)
echo "[6/8] Monitorando tempo de reação e consumo..."
# ... (lógica de T_DET e docker stats do seu script[cite: 6])

sleep $((DURACAO - 10)) # Ajuste do tempo de espera

# [7/8] Coletar métricas finais (Mantém igual)
echo "[7/8] Coletando métricas finais..."
# ... (salvar o JSON do seu script[cite: 6])

# Encerrar tudo (Mantém igual)
docker exec clab-seg-atacante pkill -9 -f python3 2>/dev/null || true
docker exec clab-seg-gateway pkill -9 -f tcpdump 2>/dev/null || true

# [8/8] Relatório
echo "[8/8] Consolidação do relatório..."
# O script Python agora deve receber a defesa e o cenário para nomear o arquivo corretamente
python3 "${SCRIPT_DIR}/gerar_relatorio.py" "$DEFESA" "$CENARIO"

echo ""
echo "======================================================="
echo " 📊 RESULTADO GRAVADO EM: $REL_FILE"
echo "======================================================="
