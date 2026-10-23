# 🛡️ eBPF/XDP-Based Slow DoS Mitigation on IoT Edge Gateways

Este repositório contém a implementação e a infraestrutura de testes para validação e avaliação de desempenho de um mecanismo de segurança baseado em **eBPF (Extended Berkeley Packet Filter)** e **XDP (eXpress Data Path)**, com suporte a **Autômato Finito Determinístico (DFA)**.

A solução é implantada em um IoT Edge Gateway para mitigar ataques de negação de serviço de baixa taxa (*Slow DoS / SlowTT*) direcionados a brokers MQTT (Mosquitto), buscando preservar a disponibilidade e evitar falsos positivos no tráfego de dispositivos IoT legítimos.

---

## 📌 1. Métricas de Avaliação Padronizadas

Para garantir a reprodutibilidade científica e comparar a eficiência do mecanismo nos diferentes cenários de teste, são adotadas as seguintes métricas:

### Eixos de Métricas Essenciais da Pesquisa

| Eixo de avaliação | Métricas |
|---|---|
| **1. Eficiência da Defesa (L7)** | • Taxa de Falsos Positivos (FPR %). **Meta:** próxima de 0%.<br>• Cadência de Pings / Wait Timeout: $WT < 1{,}5 \times T$.<br>• Razão de Payload Útil: $R_{payload} \rightarrow 0$. |
| **2. Custo do Gateway (Kernel/Edge)** | • Consumo de CPU por core (%).<br>• Latência de decisão no driver XDP ($\mu s$). |
| **3. Impacto no Broker (Alvo/Aplicação)** | • Exaustão de soquetes: $N_{conn} = 1024$.<br>• Taxa de sucesso/entrega das mensagens dos sensores (%).<br>• Disponibilidade Contínua ($S_{check}$) e Latência de Acesso. |

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
                             | SlowTT (Botnet)  |
                             | 10.0.1.20 a .50  |
                             +------------------+
```

---

## ⚡ 3. Descrição Técnica do Ataque SlowTT

O SlowTT é tratado neste projeto como um ataque de negação de serviço de baixa taxa (*low-rate DoS*). O atacante:
1. Estabelece sessões MQTT simultâneas (distribuídas em 31 IPs).
2. Mantém os soquetes abertos enviando mensagens curtas `PINGREQ` (`0xC0 0x00`).
3. Ocupa recursos no Broker silenciosamente, exaurindo o limite de conexões, o que impede clientes legítimos de operar.

---

## 🚀 4. Passo a Passo para Execução dos Testes

### 4.1. Pré-requisitos
- Host Linux com Docker e Containerlab operacionais.
- Ferramentas de compilação instaladas (Clang/LLVM, bpftool, tshark, etc).

### 4.2. Preparar o ambiente

```bash
# Entrar no diretório
cd ebpf-mqtt-slowtt-mitigation/scripts

# Dar permissões
chmod +x *.sh

# Inicializar Topologia e compilar eBPF
./setup.sh
./compile.sh
```

---

# 🧪 5. Cenários Experimentais (Execução Passo a Passo)

A execução exige a abertura de múltiplos terminais para garantir que os processos de rede, o monitoramento, os clientes legítimos e o ataque ocorram simultaneamente. Recomenda-se rodar o experimento por **2 a 5 minutos**.

### Fase 1: Inicialização e Monitoramento Passivo

**Terminal 1 — Aplicar a Defesa no Gateway**
Escolha o cenário que será executado e aplique a política:
```bash
./load_xdp.sh off        # Cenário 0: Baseline sem proteção
./load_xdp.sh iptables   # Cenário 1: Mitigação Tradicional L4
./load_xdp.sh stateful   # Cenário 2: eBPF Heurístico (Sem DFA)
./load_xdp.sh dfa        # Cenário 3: eBPF com Autômato (DFA - Proposto)
```

**Terminal 2 — Captura de Pacotes**
Altere o nome do `.pcap` de acordo com o cenário escolhido no Terminal 1:
```bash
# Escolha o respectivo pcap: baseline_off.pcap, iptables.pcap, heuristic.pcap ou dfa.pcap
docker exec -i clab-seg-gateway tcpdump -i eth2 -n "tcp port 1883" -w /scripts/dfa.pcap
```

**Terminal 3 — Consumo de Hardware (Recursos)**
```bash
docker stats clab-seg-mqtt clab-seg-gateway
```

**Terminal 4 — Logs do Broker Mosquitto**
```bash
docker exec -it clab-seg-mqtt tail -f /scripts/mosquitto.log
```

**Terminal 5 — Tabelas de Descarte eBPF (Somente para cenários com XDP)**
```bash
# Ver quais IPs foram inseridos na blocklist L7
docker exec clab-seg-gateway bpftool map dump name blocked_ips_map
```

**Terminal 6 — Registro de Mensagens Legítimas Entregues**
```bash
docker exec -i clab-seg-mqtt mosquitto_sub -h 10.0.2.10 -t "iot/#" -v | ts '[%Y-%m-%d %H:%M:%S]' > /Mestrado/scripts/mensagens_recebidas.log
```

---

### Fase 2: Geração de Tráfego Legítimo e Verificador $S_{check}$

**Terminal 7 — Sensor de Evento**
```bash
docker exec -it clab-seg-sensor-evento python3 /scripts/sensor.py --perfil evento
```

**Terminal 8 — Sensor de Subscrição**
```bash
docker exec -it clab-seg-sensor-sub python3 /scripts/sensor.py --perfil sub
```

**Terminal 9 — Sensor com Jitter**
```bash
docker exec -it clab-seg-sensor-jitter python3 /scripts/sensor.py --perfil jitter
```

**Terminal 10 — Monitor Contínuo de Disponibilidade ($S_{check}$)**
Abra este terminal **ANTES** de iniciar o ataque. Ele sondará a disponibilidade e a latência a cada 2 segundos, gravando tudo automaticamente para o gerador de relatórios.
```bash
docker exec -it clab-seg-sensor-sub python3 /scripts/s_check.py
```

---

### Fase 3: Injeção do Ataque SlowTT Distribuído

**Terminal 11 — Gerador Botnet SlowTT**
Inicia o ataque distribuindo conexões pelo pool de 31 IPs configurados:
```bash
docker exec -it clab-seg-atacante python3 /scripts/slowtt_attack.py | ts '[%Y-%m-%d %H:%M:%S]' > /scripts/ataque_execucao.log
```

**Terminal 12 — Medidor de Conexões TCP no Alvo ($N_{conn}$)**
Durante o ataque, acompanhe se as conexões estouram ou se a mitigação as reduz:
```bash
watch -n 2 'docker exec clab-seg-mqtt sh -c "ss -tna | grep :1883 | grep -i ESTAB | wc -l"'
```

---

# 📊 6. Geração do Relatório Consolidado

Após concluir o tempo desejado, encerre todos os terminais (`Ctrl+C`). O script Python a seguir lerá o `.pcap`, os logs e o arquivo de métricas do $S_{check}$ para compilar toda a matemática acadêmica em um arquivo Markdown formatado.

Execute o comando apontando para a flag `--cenario` que corresponde ao ensaio atual:

```bash
# Cenário 0: Baseline (XDP OFF)
python3 /Mestrado/scripts/gerar_relatorio.py --cenario off

# Cenário 1: iptables
python3 /Mestrado/scripts/gerar_relatorio.py --cenario iptables

# Cenário 2: eBPF Stateless/Heurístico
python3 /Mestrado/scripts/gerar_relatorio.py --cenario heuristic

# Cenário 3: eBPF DFA (Autômato)
python3 /Mestrado/scripts/gerar_relatorio.py --cenario dfa
```

Os resultados serão salvos individualmente como `relatorio_xdp_off.md`, `relatorio_iptables.md`, etc., prontos para serem anexados à dissertação.