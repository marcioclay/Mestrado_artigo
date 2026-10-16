# 🛡️ eBPF/XDP-Based Slow DoS Mitigation on IoT Edge Gateways

Este repositório contém a implementação e a infraestrutura de testes para validação e avaliação de desempenho de um mecanismo de segurança baseado em **eBPF (Extended Berkeley Packet Filter)** e **XDP (eXpress Data Path)**, com suporte a **Autômato Finito Determinístico (DFA)**.

A solução é implantada em um IoT Edge Gateway para mitigar ataques de negação de serviço de baixa taxa (*Slow DoS / SlowTT*) direcionados a brokers MQTT (Mosquitto), buscando preservar a disponibilidade e evitar falsos positivos no tráfego de dispositivos IoT legítimos.

---

## 📌 1. Métricas de Avaliação Padronizadas

Para garantir a reprodutibilidade científica e comparar a eficiência do mecanismo nos diferentes cenários de teste, são adotadas as seguintes métricas:

| Métrica | Descrição |
|---|---|
| **Packet Drop Rate (pps / %)** | Taxa de pacotes maliciosos descartados no nível XDP (`XDP_DROP`), comparada à filtragem na camada Netfilter (`iptables`). |
| **Consumo de CPU (%)** | Carga de processamento do gateway, considerando a utilização dos núcleos da CPU. |
| **False Positive Rate (FPR)** | Percentual de mensagens ou conexões legítimas de sensores rejeitadas indevidamente pela defesa. Meta experimental: \(FPR \to 0\). |
| **Disponibilidade do broker MQTT** | Número de conexões estabelecidas e recursos de conexão disponíveis no Mosquitto durante o ataque. O cenário considera `max_connections = 1024`. |
| **Latência de decisão no kernel (µs)** | Tempo necessário para o programa eBPF inspecionar os dados disponíveis do protocolo e tomar uma decisão de encaminhamento ou descarte. |

> **Nota metodológica:** a inspeção de mensagens MQTT na camada de aplicação por um programa XDP exige tratamento explícito dos cabeçalhos Ethernet, IP, TCP e dos dados MQTT. A implementação precisa considerar fragmentação, segmentação TCP e pacotes incompletos.

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

A condição temporal considerada no cenário é:

\[
WT < 1.5 \times KeepAlive
\]

Essa expressão deve ser interpretada como uma hipótese de temporização do experimento, e não como uma regra universal do protocolo MQTT.

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

## 🧪 5. Cenários Experimentais

Terminal 1: Monitoramento no Broker MQTT aberto sempre
Inicie a escuta contínua de todas as mensagens que chegam ao broker:
```
docker exec -it clab-seg-mqtt mosquitto_sub -h 10.0.2.10 -t "iot/#" -v
```

### Cenário 1 — Baseline sem proteção

**Objetivo:** estabelecer uma referência de comportamento sem os mecanismos de mitigação avaliados.

Desative a proteção:

```bash
./load_xdp.sh off
```

Inicie os clientes legítimos em terminais distintos.

**Terminal A — Sensor orientado a eventos**

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py --perfil evento
```

**Terminal B — Dashboard subscritor**

```bash
docker exec -it clab-seg-sensor-sub \
  python3 /scripts/sensor.py --perfil sub
```

**Terminal C — Sensor com jitter**

```bash
docker exec -it clab-seg-sensor-jitter \
  python3 /scripts/sensor.py --perfil jitter
```

Em outro terminal, execute o gerador de ataque controlado:

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py
```

#### Validação das conexões no broker

Consulte as conexões TCP estabelecidas na porta MQTT:

```bash
docker exec -it clab-seg-mqtt \
  ss -tna | grep ':1883' | grep -i ESTAB | wc -l
```

O comando contabiliza conexões TCP estabelecidas que correspondem ao filtro utilizado. Ele não comprova, isoladamente, que todas as conexões são sessões MQTT válidas ou que o limite de conexões foi atingido.

#### Teste de uma nova conexão

Tente estabelecer uma nova conexão MQTT legítima usando um cliente de teste independente.

**Resultado esperado:** caso os recursos de conexão tenham sido esgotados, o novo cliente poderá falhar ao se conectar.

---

### Cenário 2 — Mitigação convencional com iptables

**Objetivo:** avaliar uma estratégia convencional de filtragem e comparar seu comportamento com as alternativas baseadas em eBPF/XDP.

Ative o cenário:

```bash
./load_xdp.sh iptables
```

Execute novamente os clientes legítimos e o gerador de ataque:

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py
```

#### Coleta de métricas

Observe o consumo de CPU do gateway:

```bash
docker exec -it clab-seg-gateway htop
```

Registre também:

- Conexões simultâneas no broker.
- Taxa de sucesso das conexões legítimas.
- Pacotes recebidos e descartados.
- CPU e memória consumidas.
- Eventuais falsos positivos.

**Hipótese experimental:** regras convencionais baseadas em limites de conexões ou taxas podem não distinguir adequadamente todos os comportamentos legítimos e maliciosos. O resultado depende das regras efetivamente implementadas e dos parâmetros de configuração.

---

### Cenário 3 — eBPF Stateless

**Objetivo:** avaliar uma estratégia eBPF/XDP que utiliza critérios estatísticos ou limiares de tráfego sem manter o estado completo do protocolo MQTT.

Ative o cenário:

```bash
./load_xdp.sh stateless
```

Execute novamente os sensores legítimos e o gerador de ataque:

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py
```

#### Coleta de métricas

Avalie:

- Percentual de tráfego malicioso descartado.
- Taxa de falsos positivos.
- Consumo de CPU do gateway.
- Disponibilidade do broker MQTT.
- Comportamento diante de tráfego legítimo de baixa frequência.

**Hipótese experimental:** uma estratégia baseada apenas em limiares pode ter dificuldade para identificar ataques de baixa taxa, especialmente quando o tráfego malicioso se assemelha ao comportamento legítimo dos sensores.

---

### Cenário 4 — eBPF Stateful + DFA

**Objetivo:** avaliar a proposta de inspeção de tráfego MQTT com manutenção de estado e um Autômato Finito Determinístico (DFA), conforme a implementação experimental.

Ative o cenário:

```bash
./load_xdp.sh dfa
```

Execute novamente os sensores e o gerador de ataque:

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py
```

#### Validação e coleta de evidências

**No gateway:** consulte o mapa eBPF de endereços bloqueados:

```bash
docker exec -it clab-seg-gateway \
  bpftool map dump name blocked_ips_map
```

**Nos sensores legítimos:** verifique se os clientes continuam estabelecendo e mantendo suas conexões e executando as operações MQTT previstas.

**No broker:** acompanhe o número de conexões estabelecidas:

```bash
docker exec -it clab-seg-mqtt \
  ss -tna | grep ':1883' | grep -i ESTAB | wc -l
```

Registre os resultados e compare-os com os cenários anteriores.

**Hipótese experimental:** a combinação de inspeção e estado pode melhorar a discriminação entre comportamentos legítimos e maliciosos, desde que as condições de detecção estejam corretamente definidas e implementadas.

> **Importante:** os resultados dependem da implementação real. O comando `bpftool` somente funcionará se o mapa `blocked_ips_map` existir e estiver acessível. O descarte em XDP também depende do ponto de anexação do programa e do caminho percorrido pelo tráfego.

---

## 📊 6. Matriz Comparativa de Resultados

A tabela abaixo apresenta os resultados esperados como hipóteses a serem verificadas experimentalmente.

| Indicador | Baseline (`off`) | `iptables` | eBPF Stateless (`stateless`) | eBPF Stateful + DFA (`dfa`) |
|---|---|---|---|---|
| Mitigação do SlowTT | Sem mitigação dedicada | Depende das regras | Potencialmente limitada para ataques de baixa taxa | Espera-se maior capacidade de discriminação |
| Falsos positivos | Não há filtro de mitigação | Dependem das regras | Dependem dos limiares utilizados | Meta experimental próxima de zero |
| Consumo de CPU no gateway | Referência de comparação | Deve ser medido | Deve ser medido | Deve ser medido |
| Disponibilidade do broker | Pode degradar sob ataque | Depende da eficácia das regras | Pode degradar sob ataque | Meta experimental: manter a disponibilidade |
| Descarte na borda | Não aplicável à mitigação | Depende do mecanismo utilizado | Deve ser medido | Deve ser medido |

**Nota:** não atribua percentuais de mitigação, valores de CPU ou latência sem medições reproduzíveis. Os resultados devem ser obtidos com repetições controladas e condições de execução documentadas.

---

## 🔬 7. Reprodutibilidade Científica

Para permitir que outros pesquisadores reproduzam os experimentos, registre:

- Versão do kernel Linux.
- Versões do Docker e do Containerlab.
- Versão do Mosquitto.
- Configuração do broker, incluindo o limite de conexões.
- Modelo de CPU e quantidade de núcleos.
- Configuração de interfaces e modo de anexação XDP.
- Parâmetros do gerador de ataque.
- Duração de cada experimento.
- Número de repetições.
- Métricas brutas coletadas e método de cálculo.
- Configurações utilizadas em cada cenário.

Sempre que possível, disponibilize os arquivos de configuração, os scripts de execução e os dados brutos utilizados na análise.

---

## 📁 8. Estrutura sugerida do repositório

```text
ebpf-mqtt-slowtt-mitigation/
├── README.md
├── topologia.yml
├── configs/
│   └── mosquitto.conf
├── ebpf/
│   └── xdp_filter.c
├── scripts/
│   ├── setup.sh
│   ├── compile.sh
│   ├── load_xdp.sh
│   ├── sensor.py
│   └── slowtt_attack.py
├── results/
│   ├── baseline/
│   ├── iptables/
│   ├── stateless/
│   └── dfa/
└── docs/
    └── methodology.md
```

> A estrutura é uma sugestão de organização. Ajuste os nomes e diretórios de acordo com os arquivos efetivamente presentes no projeto.

---

## 📚 9. Considerações finais

Este projeto propõe uma avaliação experimental de estratégias de mitigação de ataques Slow DoS direcionados a brokers MQTT em gateways de borda IoT.

A comparação entre baseline, filtragem convencional e mecanismos eBPF/XDP busca investigar:

- A eficácia da mitigação de tráfego malicioso de baixa taxa.
- O impacto sobre os recursos computacionais do gateway.
- A preservação da conectividade dos sensores legítimos.
- A disponibilidade do broker MQTT durante os ataques.
- A latência de decisão e o custo de processamento na borda.

A conclusão sobre a eficácia da solução deverá ser baseada nos dados coletados, na análise dos falsos positivos e na reprodução dos cenários experimentais.
