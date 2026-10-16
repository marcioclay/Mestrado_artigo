# 🛡️ Mecanismos de Defesa e Estrutura do Testbed (eBPF/XDP vs. Baseline)

Este documento descreve o funcionamento, a lógica de implementação e a configuração dos quatro cenários de mitigação e baseline avaliados na pesquisa, além de especificar as versões do software, a justificativa topológica e a fundamentação teórica.

---

## 📌 1. Regras e Funcionamento das Quatro Abordagens de Defesa

O gerenciamento dos modos de segurança no Gateway IoT (`clab-seg-gateway`) é executado dinamicamente por meio do script de gerenciamento dos ganchos do kernel (`load_xdp.sh`).

### A. Cenário 1: Baseline — Sem Proteção (`./load_xdp.sh off`)

- **Descrição:** todos os filtros de rede, ganchos XDP e regras de Netfilter utilizados na mitigação são desativados no gateway. O gateway opera como um roteador IP, com `net.ipv4.ip_forward = 1`.
- **Comportamento sob ataque:** o tráfego SlowTT atravessa o gateway sem restrições específicas de mitigação. O broker Mosquitto processa as solicitações de conexão MQTT, podendo atingir o limite de conexões simultâneas configurado (`max_connections = 1024`) e comprometer a disponibilidade do serviço.

### B. Cenário 2: Netfilter Convencional (`./load_xdp.sh iptables`)

- **Descrição:** aplicação de uma regra de controle de densidade de conexões por endereço IP de origem, utilizando o Netfilter na camada de transporte (L4) do gateway Linux.

**Regra aplicada:**

```bash
iptables -A FORWARD -p tcp --dport 1883 \
  -m connlimit --connlimit-above 20 -j DROP
```

- **Funcionamento:** o módulo `connlimit` limita a quantidade de conexões simultâneas que correspondem aos critérios configurados. Quando o limite é excedido, os pacotes correspondentes à regra são descartados.
- **Limitação potencial:** a filtragem convencional processa os pacotes na pilha de rede do kernel e pode apresentar maior custo computacional que uma estratégia XDP, dependendo da carga e da configuração.
- **Possíveis falsos positivos:** clientes legítimos que excedam o limite configurado também poderão ser afetados.

> **Observação:** a regra deve ser validada no ambiente experimental. O comportamento exato depende do rastreamento de conexões, dos critérios do `connlimit` e das regras existentes no firewall.

### C. Cenário 3: eBPF Stateless — Sem Autômato (`./load_xdp.sh stateless`)

- **Descrição:** anexa o programa `xdp_stateless.o` à interface de rede definida na configuração experimental, por exemplo, `eth2` (LAN).
- **Funcionamento:** o programa eBPF em C contabiliza pacotes por endereço IP de origem em janelas de tempo, sem manter o estado completo da sessão MQTT. Pode utilizar um mapa do tipo `BPF_MAP_TYPE_HASH` para armazenar contadores por IP.
- **Limitação potencial:** como o SlowTT é caracterizado, neste cenário, como um ataque de baixa taxa (*low-rate*), os pacotes curtos e espaçados podem não ultrapassar os limiares de detecção.
- **Risco de falsos positivos:** a redução excessiva dos limiares pode bloquear tráfego legítimo, como rajadas de mensagens de emergência do `sensor-evento`.

### D. Cenário 4: eBPF Stateful + Autômato Finito Determinístico — Proposta (`./load_xdp.sh dfa`)

- **Descrição:** anexa o programa `xdp_monitor_dfa.o` ao gancho XDP. A proposta utiliza estado por fluxo ou sessão e um Autômato Finito Determinístico (DFA) para classificar padrões de comunicação MQTT.
- **Modelo formal:** o autômato é representado por:

\[
\mathcal{M} = (Q, \Sigma, \delta, q_0, F)
\]

Em que:

- \(Q\): conjunto de estados.
- \(\Sigma\): alfabeto de entrada.
- \(\delta\): função de transição.
- \(q_0\): estado inicial.
- \(F\): conjunto de estados de aceitação.

#### Funcionamento proposto

1. **Camadas L2/L3/L4:** o programa verifica os cabeçalhos Ethernet, IP e TCP e identifica os segmentos que contêm dados de aplicação.
2. **Inspeção L7:** quando os dados necessários estão disponíveis no segmento, o programa identifica o tipo de pacote MQTT.
3. **Transição de estados:** o programa mantém o estado associado ao fluxo ou cliente, de acordo com a lógica definida na implementação.

Exemplo conceitual de transições:

| Transição ou estado | Significado |
|---|---|
| `q₀` → `q₁` | Recebimento de `CONNECT` |
| `q₁` → `q_pub` | Recebimento de `PUBLISH` |
| `q₁` → `q_sub` | Recebimento de `SUBSCRIBE` |
| `q_err` | Estado de classificação de um padrão considerado inválido ou suspeito pelas regras experimentais |

4. **Mitigação:** quando um comportamento satisfaz os critérios de bloqueio, o programa pode registrar o endereço IP em um mapa eBPF, como `blocked_ips_map`, e descartar pacotes subsequentes com `XDP_DROP`.

A consulta a um mapa hash pode apresentar custo médio aproximadamente constante em condições usuais, mas não deve ser tratada como uma garantia absoluta de complexidade ou latência.

> **Limitação técnica importante:** receber `CONNECT` e depois `PINGREQ` sem `PUBLISH` ou `SUBSCRIBE` não caracteriza, por si só, uma violação do protocolo MQTT. Clientes legítimos podem manter conexões ociosas. A política de detecção precisa considerar o contexto, o tempo de conexão, os limites de recursos e o comportamento legítimo esperado.

---

## 🌐 2. Justificativa da Topologia e Especificações de Software

### 2.1. Especificação das versões dos componentes

| Componente | Software / Imagem | Versão de referência | Papel na arquitetura |
|---|---|---|---|
| Gateway IoT | Ubuntu Server / `ebpf-host` | Ubuntu 22.04 LTS, kernel Linux 5.15 ou superior | Roteamento L3 e ponto de inspeção XDP |
| Compilador e toolchain eBPF | Clang / LLVM / libbpf | Clang/LLVM 14.0.0 ou superior | Compilação do código C para bytecode eBPF |
| Ferramenta de diagnóstico | `bpftool` | Compatível com o kernel utilizado | Inspeção de programas e mapas eBPF |
| Broker MQTT | Eclipse Mosquitto | 2.0.11 ou superior | Serviço de mensageria na camada de aplicação |
| Biblioteca de telemetria | Python `paho-mqtt` | 2.0.0 ou superior | Implementação dos clientes MQTT e sensores |
| Emulador de topologia | Containerlab | 0.40.0 ou superior | Orquestração da topologia e dos contêineres |

> As versões acima são referências de configuração. Registre as versões efetivamente utilizadas nos experimentos para garantir a reprodutibilidade.

### 2.2. Justificativa da topologia de rede

A topologia definida em `topologia.yml` representa um cenário de ameaça interna (*insider threat*) ou de comprometimento de um dispositivo conectado à rede local IIoT (*Industrial Internet of Things*).

```text
[ Sensores Legítimos ] ──┐
                         ├──► [ Bridge L2: br-lan ]
[ Botnet Atacante ] ─────┘                |
                                          v
                                [ Gateway eBPF ]
                                          |
                                          v
                                [ DMZ: Broker MQTT ]
```

#### 1. Compartilhamento do domínio de broadcast L2

O atacante (`10.0.1.20`) e os sensores legítimos (`10.0.1.10` a `10.0.1.12`) compartilham a ponte virtual `br-lan`.

Essa configuração representa um cenário em que um invasor obtém acesso à rede local por meio de uma conexão Ethernet, Wi-Fi ou de um dispositivo comprometido.

#### 2. Gateway intermediário obrigatório

A comunicação destinada ao broker MQTT na DMZ (`10.0.2.10`) deve atravessar o gateway (`10.0.1.1` na LAN e `10.0.2.1` na DMZ).

Para garantir esse comportamento, os nós da LAN precisam utilizar o gateway como rota para a rede da DMZ. O encaminhamento IP e as regras de firewall também devem estar configurados corretamente.

Essa organização permite avaliar o processamento do tráfego no ponto de inspeção XDP.

#### 3. Restrição de recursos computacionais

O ambiente pode impor limites de CPU e memória ao contêiner do gateway para simular recursos restritos.

Exemplo de parâmetros experimentais:

- CPU: até 4 núcleos.
- Memória RAM: até 4 GB.

Esses limites representam uma configuração de recursos, não uma reprodução exata do hardware de um Raspberry Pi 4 Model B. O desempenho real depende também da arquitetura do processador, do kernel, do driver de rede e do ambiente de virtualização.

---

## 📚 3. Referências Bibliográficas e Fundamentação

As referências abaixo estão organizadas em formato Markdown. Os dados bibliográficos devem ser conferidos nas publicações originais antes da submissão do artigo.

- **Vaccari et al. (2020).** *SlowITe: A novel Slow DoS attack against IoT environments*. MDPI Sensors, 20(11), 3032.  
  Fundamentação relacionada a ataques Slow DoS em ambientes IoT.

- **Vaccari et al. (2020b).** *MQTTset: A new dataset for machine learning techniques on MQTT*. IEEE Access.  
  Referência relacionada à análise de tráfego MQTT e à estrutura de dados utilizada em pesquisas sobre o protocolo.

- **Tolay (2025).** *eBPF-Based Real-Time DDoS Mitigation for IoT Edge Devices*. arXiv preprint arXiv:2508.00851.  
  Referência indicada para investigação do uso de eBPF na mitigação de ataques DDoS em dispositivos de borda. A identificação e os resultados da publicação devem ser conferidos na fonte original.

- **Kostopoulos et al. (2026).** *eBPF-Based Cybersecurity Mechanisms: A Systematic Literature Review*. Journal of Systems Architecture.  
  Referência indicada para fundamentação sobre mecanismos de segurança baseados em eBPF. Confirmar os dados de publicação e a disponibilidade do artigo.

- **Ficara et al. (2008).** *An improved DFA for fast regular expression matching*. ACM SIGCOMM.  
  Referência relacionada à utilização de autômatos determinísticos na análise eficiente de padrões.

- **OASIS (2014).** *MQTT Version 3.1.1 Specification*. OASIS Standard.  
  Especificação normativa do protocolo MQTT, incluindo as regras relacionadas ao Keep Alive e ao intervalo de tolerância de até \(1{,}5 \times T\) para a detecção de perda de comunicação.

---

## 🔬 4. Considerações Técnicas para a Validação

Para garantir consistência científica, os seguintes pontos devem ser documentados:

1. **Segmentação TCP:** os dados MQTT podem estar divididos em vários segmentos TCP. Uma implementação XDP não recebe automaticamente um fluxo TCP reconstituído.
2. **Cabeçalhos de protocolo:** o cálculo do início do payload deve considerar os comprimentos reais dos cabeçalhos, as opções TCP e os limites de memória acessíveis ao programa.
3. **Classificação MQTT:** `CONNECT`, `PUBLISH`, `SUBSCRIBE` e `PINGREQ` precisam ser identificados corretamente a partir dos dados efetivamente disponíveis.
4. **Estado do cliente:** a manutenção de estado deve definir como os fluxos são identificados, atualizados, expirados e removidos dos mapas eBPF.
5. **Política de bloqueio:** o bloqueio de um IP inteiro pode afetar múltiplos clientes legítimos que compartilhem o mesmo endereço de origem.
6. **Medição de desempenho:** consumo de CPU, latência, taxa de descarte e falsos positivos devem ser obtidos por meio de experimentos repetíveis.

## Conclusão

A estrutura experimental compara quatro abordagens: baseline sem proteção, filtragem convencional com Netfilter, eBPF Stateless e eBPF Stateful com DFA.

O objetivo é investigar se a inspeção no ponto XDP, associada à manutenção de estado e a critérios de classificação do tráfego MQTT, pode reduzir o impacto do SlowTT sem comprometer a comunicação legítima dos dispositivos IoT.

A eficácia da proposta deve ser demonstrada por métricas experimentais e por uma descrição reproduzível da implementação, da topologia e dos parâmetros utilizados.

