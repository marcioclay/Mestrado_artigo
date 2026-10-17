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

# 🧪 5. Cenários Experimentais

## Fase 1 — Preparação e escuta contínua (2 a 5 minutos)

Antes de iniciar qualquer tráfego, prepare o ambiente de captura e monitoramento. Os terminais desta fase devem permanecer abertos durante o experimento, registrando os dados continuamente.

**Duração recomendada:** de 2 a 5 minutos, conforme o planejamento experimental.

### Terminal 1 — Captura de pacotes no gateway (PCAP)

Inicie a captura do tráfego TCP/MQTT que atravessa a interface LAN `eth2` do gateway:

```bash
docker exec -it clab-seg-gateway \
  tcpdump -i eth2 -n "tcp port 1883" \
  -w /scripts/baseline_off.pcap
```

Mantenha a captura ativa e encerre-a com `Ctrl+C` somente ao final da coleta de dados.

### Terminal 2 — Monitoramento dos logs do Mosquitto

Acompanhe os logs do broker em tempo real para correlacionar eventos de conexão, desconexão e possíveis rejeições:

```bash
docker exec -it clab-seg-mqtt \
  tail -f /var/log/mosquitto/mosquitto.log
```

> **Nota:** se o caminho do log ou o mapeamento de volumes for diferente, ajuste o comando. Por exemplo, o arquivo pode estar disponível em `/Mestrado/scripts/mosquitto.log`, dependendo da configuração do ambiente.

### Terminal 3 — Monitoramento do tráfego de aplicação MQTT

Inicie a escuta das mensagens publicadas nos tópicos que começam com `iot/`:

```bash
docker exec -it clab-seg-mqtt \
  mosquitto_sub -h 10.0.2.10 -t "iot/#" -v
```

Esse comando permite observar as mensagens recebidas pelo broker nos tópicos correspondentes, desde que o endereço IP, a conectividade e as permissões MQTT estejam configurados corretamente.

---

## Fase 2 — Cenário 1: Baseline sem proteção

O objetivo deste cenário é estabelecer a referência experimental sem mecanismos de mitigação ativos, observar o comportamento dos sensores legítimos, validar a captura do tráfego e avaliar o impacto do ataque SlowTT sobre o broker.

### 1. Desativar os mecanismos de proteção

No terminal do host, execute:

```bash
./load_xdp.sh off
```

Esse comando deve desativar os mecanismos de mitigação eBPF/XDP previstos no experimento.

### 2. Iniciar os sensores legítimos

Abra três terminais separados no host e execute um perfil de sensor em cada terminal.

**Terminal 4 — Sensor de eventos**

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py --perfil evento
```

**Terminal 5 — Sensor de subscrição**

```bash
docker exec -it clab-seg-sensor-sub \
  python3 /scripts/sensor.py --perfil sub
```

**Terminal 6 — Sensor de jitter**

```bash
docker exec -it clab-seg-sensor-jitter \
  python3 /scripts/sensor.py --perfil jitter
```

### Métricas analisadas nesta etapa

- **Taxa inicial de sucesso na entrega:** verificar se os sensores conseguem estabelecer conexão e transmitir mensagens ao broker.
- **Funcionamento normal do broker:** confirmar, por meio do Terminal 3, que o tráfego legítimo está fluindo antes do início do ataque.

A taxa inicial de entrega de 100% é uma referência esperada, não um resultado presumido. Registre o valor efetivamente observado.

---

## Fase 3 — Disparo e medição do ataque

### 3 Disparar o ataque SlowTT

Em um Terminal 7 no host, execute o script responsável por gerar o ataque:

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py
```

Registre o horário exato de início do ataque para correlacionar os eventos com a captura de pacotes (`PCAP`), os logs do Mosquitto e as medições realizadas no broker.

### 4. Medir a exaustão de conexões no broker

Com o ataque ativo, abra um Terminal 8 para consultar o impacto nos recursos do servidor.

#### 4.1. Contar os soquetes TCP estabelecidos

```bash
docker exec -it clab-seg-mqtt \
  sh -c "ss -tna | grep ':1883' | grep -i ESTAB | wc -l"
```

**Métrica analisada:** número de conexões TCP estabelecidas na porta 1883 (\(N_{conn}\)).

Registre a quantidade retornada e compare-a com o limite de conexões configurado no broker.

> **Importante:** o valor de 1024 só deve ser tratado como limite experimental se estiver efetivamente configurado e confirmado na instalação do Mosquitto. A contagem de conexões TCP estabelecidas não equivale necessariamente ao número de clientes MQTT ativos.

#### 4.2. Testar a negação de serviço em um novo cliente

Ainda durante o ataque, tente iniciar uma nova instância do sensor para simular uma tentativa de conexão de um novo dispositivo:

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py --perfil evento
```

**Métrica analisada:** taxa de sucesso ou falha no estabelecimento de uma nova conexão.

Registre o resultado e a mensagem de erro apresentada pelo cliente. Os possíveis sintomas incluem:

- `Connection timed out`;
- `Connection refused`;
- falha de autenticação ou rejeição pelo broker;
- conexão estabelecida, mas sem entrega de mensagens.

A ocorrência isolada de um desses sintomas não comprova exaustão total dos recursos. Correlacione o resultado com o número de conexões alcançado e os logs registrados no Terminal 2.

---

## Fase 4 — Encerramento e extração das métricas de tráfego

### 5. Analisar os pacotes no Wireshark

Após concluir o período experimental de 2 a 5 minutos:

1. Encerre o ataque com `Ctrl+C` no Terminal 7.
2. Encerre os sensores legítimos.
3. Interrompa a captura de pacotes no Terminal 1 com `Ctrl+C`.
4. Encerre os demais processos de monitoramento, conforme necessário.
5. Abra o arquivo `baseline_off.pcap` no Wireshark.

### Métricas analisadas na camada de rede e aplicação

#### 5.1. Cadência de Pings / Wait Timeout (\(WT\))

Inspecione o intervalo de tempo entre as mensagens MQTT `PINGREQ` enviadas pelos clientes analisados.

O conteúdo de controle MQTT do pacote `PINGREQ` é representado pelos bytes `C0 00`.

Registre os intervalos observados e compare-os com os parâmetros de tempo definidos na metodologia experimental.

#### 5.2. Razão de Payload Útil (\(R_{payload}\))

Calcule a proporção entre as mensagens `PUBLISH` legítimas e o tráfego de controle ou os pacotes sem payload útil para a aplicação.

A interpretação de \(R_{payload}\) deve seguir rigorosamente a definição matemática adotada na metodologia. Pacotes TCP sem payload MQTT não constituem necessariamente tráfego malicioso.

### Registro final do cenário

| Item | Dado a registrar |
|---|---|
| Duração do experimento | Tempo efetivo de coleta |
| Início do ataque | Horário registrado |
| Taxa inicial de entrega | Percentual observado antes do ataque |
| Conexões TCP estabelecidas | Valor de \(N_{conn}\) durante o ataque |
| Resultado de nova conexão | Sucesso ou falha, com mensagem apresentada |
| Cadência de `PINGREQ` | Intervalos observados |
| Razão de payload útil | Valor calculado de \(R_{payload}\) |
| Logs do Mosquitto | Eventos relevantes registrados |
| Captura PCAP | Arquivo `baseline_off.pcap` |

**Resultado esperado:** estabelecer uma linha de base mensurável para comparar o comportamento do gateway e do broker sem proteção com os resultados dos cenários que utilizam `iptables` e eBPF/XDP.
