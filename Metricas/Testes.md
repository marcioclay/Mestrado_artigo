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

## 🧪 5. Cenários Experimentais

Terminal 1: Monitoramento no Broker MQTT aberto sempre
Inicie a escuta contínua de todas as mensagens que chegam ao broker:
```
docker exec -it clab-seg-mqtt mosquitto_sub -h 10.0.2.10 -t "iot/#" -v
```

### Cenário 1 — Baseline sem proteção

Este cenário estabelece a referência experimental sem mecanismos de mitigação ativos. O objetivo é observar o comportamento dos sensores legítimos, capturar o tráfego MQTT e avaliar o impacto do ataque SlowTT sobre o broker.

## 1. Desativar os mecanismos de proteção

No terminal do host, execute:

```bash
./load_xdp.sh off
```

Esse comando deve deixar o gateway sem os filtros de mitigação previstos no experimento.

## 2. Iniciar os sensores legítimos

Abra **três terminais separados no host** e execute um perfil de sensor em cada terminal.

**Terminal 1 — Sensor de eventos**

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py --perfil evento
```

**Terminal 2 — Sensor de subscrição**

```bash
docker exec -it clab-seg-sensor-sub \
  python3 /scripts/sensor.py --perfil sub
```

**Terminal 3 — Sensor de jitter**

```bash
docker exec -it clab-seg-sensor-jitter \
  python3 /scripts/sensor.py --perfil jitter
```

### Métricas analisadas

- **Taxa inicial de sucesso na entrega:** verificar se os sensores conseguem estabelecer conexão e transmitir mensagens ao broker.
- **Funcionamento normal do broker:** confirmar que o tráfego legítimo está fluindo antes do início do ataque.

> A taxa de entrega inicial de 100% é uma referência esperada, não um resultado que deve ser presumido. Registre o valor efetivamente observado.

## 3. Iniciar a captura de pacotes no gateway

Em um quarto terminal no host, inicie a captura do tráfego TCP/MQTT que atravessa a interface LAN `eth2` do gateway:

```bash
docker exec -it clab-seg-gateway \
  tcpdump -i eth2 -n "tcp port 1883" \
  -w /scripts/baseline_off.pcap
```

Mantenha a captura ativa durante o experimento e encerre-a com `Ctrl+C` após a coleta.

### Métricas analisadas no Wireshark

Após a captura, abra o arquivo `baseline_off.pcap` no Wireshark e analise:

- **Cadência de Pings / Wait Timeout (\(WT\)):** intervalo entre as mensagens MQTT `PINGREQ`, cujo conteúdo de controle é `C0 00`.
- **Razão de Payload Útil (\(R_{payload}\)):** proporção entre as mensagens `PUBLISH` e o tráfego de controle ou demais pacotes sem payload útil para a aplicação.

A interpretação de \(R_{payload}\) deve considerar a definição matemática adotada na metodologia. Pacotes TCP sem payload MQTT não são necessariamente tráfego malicioso.

## 4. Disparar o ataque SlowTT

Em um quinto terminal no host, execute o script responsável por gerar o ataque:

```bash
docker exec -it clab-seg-atacante \
  python3 /scripts/slowtt_attack.py
```

Registre o horário de início do ataque para correlacionar os eventos com a captura de pacotes e as medições realizadas no broker.

## 5. Medir a exaustão de conexões no broker

Com o ataque ativo, abra um sexto terminal no host e consulte as conexões TCP estabelecidas na porta MQTT do broker `clab-seg-mqtt`.

### 5.1. Contar os soquetes estabelecidos

```bash
docker exec -it clab-seg-mqtt \
  sh -c "ss -tna | grep ':1883' | grep -i ESTAB | wc -l"
```

**Métrica analisada:** número de conexões TCP estabelecidas na porta 1883 (\(N_{conn}\)).

Registre a quantidade retornada e compare-a com o limite de conexões configurado no broker.

> O valor `1024` só deve ser tratado como limite experimental se estiver efetivamente configurado e confirmado na instalação do Mosquitto. A contagem de conexões TCP estabelecidas também não equivale necessariamente ao número de clientes MQTT ativos.

### 5.2. Testar a negação de serviço em um novo cliente

Em outro terminal, tente iniciar uma nova instância do sensor:

```bash
docker exec -it clab-seg-sensor-evento \
  python3 /scripts/sensor.py --perfil evento
```

**Métrica analisada:** taxa de sucesso ou falha no estabelecimento de uma nova conexão durante o ataque.

Registre o resultado e a mensagem de erro apresentada pelo cliente. Possíveis sintomas incluem:

- `Connection timed out`;
- `Connection refused`;
- falha de autenticação ou rejeição pelo broker;
- conexão estabelecida, mas sem entrega de mensagens.

A ocorrência de um desses sintomas, isoladamente, não comprova que houve exaustão de recursos. Correlacione o resultado com o número de conexões, os logs e o tráfego capturado.

### 5.3. Verificar os logs do Mosquitto

No host, consulte as últimas 20 linhas do arquivo de log:

```bash
tail -n 20 /Mestrado/scripts/mosquitto.log
```

**Métrica analisada:** eventos de rejeição, desconexão e limitação de conexões registrados pelo broker.

Procure mensagens relacionadas a:

- limite de conexões atingido;
- desconexão de clientes;
- falhas de autenticação;
- conexões encerradas por timeout;
- erros ou recusas associados ao ataque.

A mensagem exata depende da versão do Mosquitto, das configurações de logging e do mecanismo responsável pela rejeição. Não presuma que o log conterá literalmente `Client disconnected due to message/connection limit`.

## 6. Consolidar os resultados do cenário

Ao finalizar a execução, registre os dados coletados.

| Métrica | Dado a registrar |
|---|---|
| Taxa inicial de entrega | Percentual de mensagens entregues antes do ataque |
| Cadência de `PINGREQ` | Intervalos observados na captura |
| Razão de payload útil (\(R_{payload}\)) | Valor calculado conforme a definição experimental |
| Conexões estabelecidas (\(N_{conn}\)) | Quantidade observada durante o ataque |
| Sucesso de novas conexões | Número de tentativas bem-sucedidas e malsucedidas |
| Entrega durante o ataque | Percentual de mensagens legítimas entregues |
| Logs do broker | Registros de rejeição, desconexão ou limitação |
| Captura de pacotes | Arquivo `baseline_off.pcap` |

**Resultado esperado:** estabelecer a linha de base sem mitigação, documentando o comportamento normal e as alterações observadas durante o ataque SlowTT. Esses dados serão comparados com os cenários que utilizam `iptables` e eBPF/XDP.
