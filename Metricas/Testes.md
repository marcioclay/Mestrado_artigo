# 🛡️ eBPF/XDP-Based Slow DoS Mitigation on IoT Edge Gateways

Este repositório contém a implementação e a infraestrutura de testes para validação e avaliação de desempenho de um mecanismo de segurança baseado em **eBPF (Extended Berkeley Packet Filter)** e **XDP (eXpress Data Path)**, com suporte a **Autômato Finito Determinístico (DFA)**.

A solução é implantada em um IoT Edge Gateway para mitigar ataques de negação de serviço de baixa taxa (*Slow DoS / SlowTT*) direcionados a brokers MQTT (Mosquitto), buscando preservar a disponibilidade e evitar falsos positivos no tráfego de dispositivos IoT legítimos.

---

## 📌 1. Métricas de Avaliação Padronizadas

Para garantir a reprodutibilidade científica e comparar a eficiência do mecanismo nos diferentes cenários de teste, são adotadas as seguintes métricas:

## Eixos de Métricas Essenciais da Pesquisa

| Eixo de avaliação | Métricas |
|---|---|
| **1. Eficiência da Defesa (L7)** | • Taxa de Falsos Positivos (FPR %). **Meta:** próxima de 0%.<br>• Cadência de Pings / Wait Timeout: \(WT < 1{,}5 \times T\).<br>• Razão de Payload Útil: \(R_{payload} \rightarrow 0\). |
| **2. Custo do Gateway (Kernel/Edge)** | • Consumo de CPU por core (%).<br>• Latência de decisão no driver XDP (\(\mu s\)). |
| **3. Impacto no Broker (Alvo/Aplicação)** | • Exaustão de soquetes: \(N_{conn} = 1024\).<br>• Taxa de sucesso/entrega das mensagens dos sensores (%). |


---

## 🌐 2. Arquitetura da Topologia de Rede

A infraestrutura é orquestrada por meio do **Containerlab**, utilizando o arquivo `topologia.yml`. A topologia é dividida em dois domínios de rede, interligados pelo gateway de borda.

### 2.1. Diagrama da topologia

```text
                  +--------------------------------------+
                  | Servidor MQTT Mosquitto              |
                  | clab-seg-mqtt                        |
                  | IP: 10.0.2.10/24                     |
                  +-------------------+------------------+
                                      |
                                      | Interface DMZ (eth1)
                                      |
                  +-------------------+------------------+
                  | Gateway eBPF                         |
                  | clab-seg-gateway                     |
                  | IP DMZ (eth1): 10.0.2.1/24           |
                  | IP LAN (eth2): 10.0.1.1/24           |
                  +-------------------+------------------+
                                      |
                                      | Interface LAN (eth2)
                                      |
                  +-------------------+------------------+
                  | Switch LAN Virtual / Bridge L2       |
                  | br-lan                               |
                  +-------------------+------------------+
                                      |
                 +--------------------+--------------------+
                 |                    |                    |
                 v                    v                    v
        +------------------+  +------------------+  +------------------+
        | sensor-evento    |  | sensor-sub       |  | sensor-jitter    |
        | 10.0.1.10/24     |  | 10.0.1.11/24     |  | 10.0.1.12/24     |
        +------------------+  +------------------+  +------------------+
                                      |
                                      v
                             +------------------+
                             | atacante         |
                             | SlowTT           |
                             | 10.0.1.20/24     |
                             +------------------+
```

### 2.2. Tabela de endereçamento IP

| Nó / Container | Interface | Endereço IP | Papel no experimento |
|---|---|---|---|
| `clab-seg-gateway` | `eth2` (LAN) | `10.0.1.1/24` | Gateway da LAN e ponto de inspeção do tráfego. |
| `clab-seg-gateway` | `eth1` (DMZ) | `10.0.2.1/24` | Interface voltada ao broker MQTT. |
| `clab-seg-mqtt` | `eth1` | `10.0.2.10/24` | Broker Mosquitto, alvo do ataque. |
| `clab-seg-sensor-evento` | `eth1` | `10.0.1.10/24` | Sensor legítimo orientado a eventos, com períodos de silêncio e rajadas de alertas. |
| `clab-seg-sensor-sub` | `eth1` | `10.0.1.11/24` | Cliente legítimo que realiza `SUBSCRIBE` e recebe publicações. |
| `clab-seg-sensor-jitter` | `eth1` | `10.0.1.12/24` | Sensor legítimo que simula oscilação ou jitter no enlace. |
| `clab-seg-atacante` | `eth1` | `10.0.1.20/24` | Gerador controlado do tráfego de ataque SlowTT. |

---

## ⚡ 3. Descrição Técnica do Ataque SlowTT

O SlowTT é tratado neste projeto como um cenário de ataque de negação de serviço de baixa taxa (*low-rate DoS*) direcionado a conexões MQTT.

### 3.1. Mecanismo de ação

O cenário experimental considera um atacante que:

1. Estabelece conexões TCP e inicia sessões MQTT com o broker.
2. Mantém múltiplas conexões simultâneas abertas.
3. Envia mensagens curtas de controle, como `PINGREQ` (`0xC0 0x00`), em intervalos relacionados ao parâmetro `Keep Alive`.
4. Ocupa recursos de conexão sem necessariamente gerar uma taxa elevada de tráfego.


### 3.2. Impacto esperado no broker

Se o número de conexões simultâneas atingir o limite configurado, novas conexões legítimas poderão ser recusadas ou sofrer falhas de estabelecimento.

O impacto será avaliado por meio de:

- Número de conexões simultâneas.
- Disponibilidade para novos clientes.
- Consumo de CPU e memória.
- Taxa de sucesso dos sensores legítimos.
- Eficácia das estratégias de mitigação.

---

## 🚀 4. Passo a Passo para Execução dos Testes

### 4.1. Pré-requisitos

O ambiente de testes requer:

- Host Linux.
- Docker instalado e operacional.
- Containerlab instalado.
- Compilador e dependências necessárias para compilar os programas eBPF.
- Privilégios adequados para configurar interfaces, carregar programas XDP e consultar mapas eBPF.

### 4.2. Clonar o repositório

```bash
git clone https://github.com/usuario/ebpf-mqtt-slowtt-mitigation.git

cd ebpf-mqtt-slowtt-mitigation/scripts
```

> Substitua `usuario` pelo nome de usuário ou organização responsável pelo repositório.

### 4.3. Preparar o ambiente

Conceda permissão de execução aos scripts:

```bash
chmod +x *.sh
```

Execute a preparação da topologia e das dependências:

```bash
./setup.sh
```

Compile os programas eBPF em C para gerar os arquivos de objeto:

```bash
./compile.sh
```

---

# 🧪 5. Cenários Experimentais Revisitados

## Fase 1 — Escuta, Monitoramento e Coleta Contínua de Dados (2 a 5 minutos)

Antes de iniciar qualquer tráfego, abra os terminais de monitoramento no host. Mantenha-os ativos durante todo o experimento, por um período recomendado de 2 a 5 minutos.

### Terminal 1 — Captura de Pacotes no Gateway

**Métricas:** taxa de tráfego (pps/bps), RTT, cadência de Pings (\(WT\)) e razão de payload útil (\(R_{payload}\)).

```bash
docker exec -it clab-seg-gateway \
  tcpdump -i eth2 -n "tcp port 1883" \
  -w /scripts/baseline_off.pcap
```

**Métricas extraídas:**
- Taxa de tráfego em pacotes por segundo (pps) e bits por segundo (bps).
- Cadência de Pings (\(WT\)).
- Razão de payload útil (\(R_{payload}\)).
- Latência/RTT, quando houver informações suficientes para calculá-los.

### Terminal 2 — Monitoramento de Recursos

**Métricas:** consumo de CPU e memória do broker Mosquitto e do gateway.

```bash
docker stats clab-seg-mqtt clab-seg-gateway
```

**Métricas extraídas:**
- Consumo percentual de CPU.
- Uso de memória (MB).

### Terminal 3 — Logs de Conexões do Broker

```bash
docker exec -it clab-seg-mqtt tail -f /scripts/mosquitto.log
```

**Métricas extraídas:**
- Conexões MQTT.
- Eventos de desconexão.
- Rejeições de novos clientes, quando registradas.

### Terminal 4 — Leitura dos Mapas eBPF no Gateway

Execute somente quando o XDP estiver carregado e o mapa existir.

```bash
docker exec -it clab-seg-gateway \
  bpftool map dump name map_metrics
```

**Métricas extraídas:**
- Contadores de pacotes permitidos (`XDP_PASS`) e descartados (`XDP_DROP`), caso implementados no mapa.
- Contagem de novas conexões TCP, caso contabilizada pelo programa.
- Estado dos fluxos registrado nos mapas eBPF.

### Terminal 5 — Registro de Mensagens Recebidas pelo Broker

```bash
docker exec -it clab-seg-mqtt \
  mosquitto_sub -h 10.0.2.10 -t "iot/#" -v |
  ts '[%Y-%m-%d %H:%M:%S]' \
  > mensagens_recebidas.log
```

**Métrica extraída:** quantidade e horário de recebimento das mensagens legítimas, para calcular a taxa de sucesso das publicações.

> **Observação:** confirme se o container possui `ts` (moreutils), se o broker permite a conexão do assinante e se o endereço `10.0.2.10` corresponde ao endereço correto do broker na sua topologia.

---

## Fase 2 — Cenário 1: Tráfego Legítimo e Linha de Base (*Baseline*)

### 1. Desativar o mecanismo de defesa

No terminal do host, execute:

```bash
./load_xdp.sh off
```

### 2. Iniciar os sensores legítimos

Abra três terminais separados. Cada script deve registrar localmente os horários de envio das mensagens.

**Terminal 6 — Sensor de Evento**

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py --perfil evento
```

**Terminal 7 — Sensor de Subscrição**

```bash
docker exec -it clab-seg-sensor-sub \
  python3 /scripts/sensor.py --perfil sub
```

**Terminal 8 — Sensor com Jitter**

```bash
docker exec -it clab-seg-sensor-jitter \
  python3 /scripts/sensor.py --perfil jitter
```

### Métricas coletadas

- **Latência:** diferença entre o envio da mensagem e sua confirmação de recebimento, usando timestamps sincronizados.
- **Taxa de publicações legítimas:** comparação entre as mensagens enviadas pelos sensores e as recebidas pelo assinante.
- **Referência de falsos positivos (FP):** sem ataque e com a defesa desativada, verificar se todas as conexões legítimas são aceitas.

Nesse cenário, espera-se que \(FP = 0\) para o mecanismo de defesa, pois ele está desativado. Isso não comprova, isoladamente, a ausência de falhas de conexão no broker ou na rede.

---

## Fase 3 — Disparo do Ataque SlowTT

### 3. Iniciar o gerador de ataque

No Terminal 9, execute o gerador de ataque no container atacante.

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py |
  ts '[%Y-%m-%d %H:%M:%S]' \
  > /scripts/ataque_execucao.log
```

**Métricas extraídas:**
- Número de conexões criadas.
- Taxa de pacotes por segundo.
- Duração da execução.

### 4. Medir as conexões simultâneas no broker

No Terminal 10:

```bash
docker exec -it clab-seg-mqtt sh -c \
  "ss -tna | grep ':1883' | grep -i ESTAB | wc -l"
```

**Métrica extraída:** número de conexões TCP estabelecidas (\(N_{conn}\)) na porta 1883.

> O comando depende da disponibilidade de `ss` no container e conta conexões TCP estabelecidas, não necessariamente sessões MQTT autenticadas ou ativas. Para acompanhar a evolução, registre o valor periodicamente.

### 5. Testar a disponibilidade durante o ataque

Execute um teste de conexão legítima:

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py \
  --perfil evento \
  --teste-disponibilidade
```

**Métrica extraída:** disponibilidade do broker, registrando horário, sucesso ou falha e mensagem de erro.

---

## Fase 4 — Encerramento e Pós-processamento

Após o período experimental, encerre o gerador de ataque e finalize a captura de pacotes com `Ctrl+C` no Terminal 1.

### 1. Classificação dos resultados

- **Falsos Positivos (FP):** conexões legítimas classificadas incorretamente como maliciosas ou bloqueadas pela defesa.
- **Verdadeiros Negativos (TN):** conexões legítimas corretamente classificadas como legítimas.
- **Verdadeiros Positivos (TP):** conexões maliciosas corretamente identificadas como ataque.
- **Falsos Negativos (FN):** conexões maliciosas que não foram identificadas.

Para calcular essas métricas, é necessário ter uma referência independente que identifique quais conexões são legítimas e quais pertencem ao ataque. Um pacote descartado não é automaticamente um verdadeiro positivo: é necessário confirmar que o tráfego descartado era malicioso.

### 2. Cálculo das métricas

**Taxa de falsos positivos (FPR):**

\[
\text{FPR} = \frac{FP}{FP + TN}
\]

**Taxa de detecção ou sensibilidade (TPR):**

\[
\text{TPR} = \frac{TP}{TP + FN}
\]

### 3. Análise do arquivo PCAP no Wireshark

Arquivo: `baseline_off.pcap`.

- **PPS e BPS:** consultar *Statistics → Capture File Properties* e *Statistics → I/O Graphs*.
- **Cadência de Pings (\(WT\)):** filtrar `mqtt.msgtype == 12` e, quando possível, limitar ao IP do atacante. Calcular os intervalos de tempo entre mensagens `PINGREQ`.
- **Razão de payload útil (\(R_{payload}\)):** contar mensagens `PUBLISH` (`mqtt.msgtype == 3`) e dividir pelo total de pacotes TCP capturados, conforme a definição operacional adotada.

\[
R_{payload} =
\frac{N_{\text{PUBLISH}}}{N_{\text{pacotes TCP}}}
\]

Essa última métrica representa uma razão de contagem de mensagens MQTT para pacotes TCP, não uma razão de bytes de payload. Se o objetivo for medir a proporção de bytes úteis, deve-se calcular separadamente o total de bytes de payload MQTT sobre o total de bytes de tráfego definido para a análise.

**Nota:** a captura `baseline_off.pcap` é adequada para a linha de base. Para avaliar o comportamento durante o ataque e comparar a defesa, gere capturas separadas para cada cenário, identificando claramente se o XDP está desativado, configurado com limiares fixos ou usando máquina de estados.

