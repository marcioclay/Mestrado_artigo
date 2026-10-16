# 📊 Tabelas Comparativas e Gráficos dos Experimentos

Este documento apresenta as tabelas comparativas das métricas de extração das camadas L4/L7, detecção do ataque SlowTT e desempenho dos mecanismos de mitigação.

Também são apresentadas orientações para gerar gráficos comparativos entre os seguintes cenários experimentais:

- **Baseline (`off`):** gateway sem proteção específica.
- **Netfilter (`iptables`):** filtragem convencional.
- **eBPF Stateless (`stateless`):** filtragem sem manutenção de estado do protocolo.
- **eBPF Stateful (`dfa`):** filtragem com estado e Autômato Finito Determinístico (DFA), conforme a proposta experimental.

---

## 📊 1. Tabela das Métricas de Extração L4/L7 e Detecção

Esta tabela apresenta os atributos monitorados pelo gateway para caracterizar o tráfego legítimo e investigar possíveis padrões associados ao ataque SlowTT.

| Camada | Atributo / Métrica | Identificador / Variável | Comportamento legítimo | Comportamento no SlowTT |
|---|---|---|---|---|
| L7 (MQTT) | Keep Alive | `mqtt.kalive` (\(T\)) | \(10\,s \leq T \leq 60\,s\), conforme os parâmetros definidos no experimento. | Valor normal ou elevado, com manutenção de conexões e pouco ou nenhum payload de aplicação. |
| L7 (MQTT) | Cadência de Pings | Wait Timeout (\(WT\)) | Intervalos de controle compatíveis com o comportamento esperado do cliente. | Envio periódico de `PINGREQ`, conforme a estratégia de ataque. |
| L7 (MQTT) | Razão de Payload | \(R_{payload}\) | \(R_{payload} > 0\), quando há publicação de mensagens ou outras operações de aplicação. | \(R_{payload} \to 0\), quando predominam conexões e mensagens de controle. |
| L7 (MQTT) | Tipo de Pacote | `mqtt.msgtype` | Tipos de pacote compatíveis com as operações executadas, como `CONNECT`, `PUBLISH` e `SUBSCRIBE`. | Possível predominância de `CONNECT` e `PINGREQ`, dependendo da implementação do ataque. |
| L4 (TCP) | Delta Temporal | `tcp.time_delta` | Intervalos variáveis, conforme o perfil do sensor e as condições da rede. | Intervalos periódicos e espaçados, conforme a estratégia de manutenção das conexões. |
| L4 (TCP) | Tamanho do Segmento | `tcp.len` | Tamanho variável, conforme os dados transportados. | Possível predominância de segmentos pequenos. |
| L4 (TCP) | Janela TCP | `tcp.window` | Valores compatíveis com o controle de fluxo TCP. | Monitoramento de variações da janela e de possíveis condições de saturação. |
| L4 (TCP) | Densidade de Conexões | \(N_{conn}\) por IP | Referência experimental de 1 a 3 conexões por nó. | Número elevado de conexões simultâneas, potencialmente associado à exaustão de recursos. |

### Observações metodológicas

- Os intervalos de Keep Alive e o número de conexões legítimas são parâmetros de referência do experimento, não limites universais do protocolo MQTT.
- A quantidade de conexões por IP deve ser avaliada considerando NAT, múltiplos clientes e particularidades da infraestrutura.
- A razão de payload deve ter sua fórmula explicitada na metodologia, incluindo o período de observação e os tipos de pacotes contabilizados.
- Os atributos `mqtt.kalive` e `mqtt.msgtype` dependem da ferramenta de captura ou análise utilizada. Não são, por si só, campos padronizados de cabeçalho TCP.
- Um pacote TCP pequeno ou uma mensagem `PINGREQ` não caracterizam isoladamente um ataque. A classificação deve considerar múltiplos atributos e o contexto da conexão.

---

## 📉 2. Tabela Comparativa de Desempenho dos Cenários

A matriz a seguir organiza os indicadores utilizados para comparar o comportamento do gateway e do broker durante os experimentos.

> **Importante:** os valores numéricos abaixo são estimativas ou resultados declarados no material de referência. Antes de apresentá-los como resultados científicos, confirme-os por meio dos dados brutos, das configurações e das medições experimentais.

| Métrica de desempenho | Baseline (`off`) | Netfilter (`iptables`) | eBPF Stateless (`stateless`) | eBPF Stateful (`dfa`) — Proposta |
|---|---|---|---|---|
| **Consumo de CPU no gateway (%)** | Aproximadamente 0,5%, apenas roteamento. | 15% a 35%, conforme a carga e as regras. | Aproximadamente 2,0%, conforme a implementação do filtro XDP. | Aproximadamente 2,2%, conforme a implementação proposta. |
| **Taxa de falsos positivos (FPR)** | 0%, sem filtro de mitigação. | Declarada como alta; requer medição. | Declarada como alta; requer medição. | Meta experimental próxima de 0%; requer validação. |
| **Soquetes livres no Mosquitto** | 0 de 1024 no cenário de exaustão total. | Instável; estimativa de 200 a 500 livres. | Instável, dependendo dos contadores e das regras. | Meta superior a 1000 conexões disponíveis, conforme o limite efetivo configurado. |
| **Latência de decisão** | Não aplicável à mitigação. | Aproximadamente 12 a 25 µs, conforme a medição declarada. | Aproximadamente 1,2 µs, conforme a medição declarada. | Aproximadamente 1,5 µs, conforme a medição declarada. |
| **Vazão de descarte (pps)** | 0 pps de descarte pelo mecanismo de mitigação. | Limitada pelo custo de processamento e pela configuração. | Potencialmente elevada; requer medição. | Potencialmente elevada; requer medição. |

### 2.1. Critérios para interpretação dos resultados

**Consumo de CPU:** a comparação deve usar a mesma máquina, carga de tráfego, duração do experimento e método de coleta. Diferencie o consumo total do gateway do consumo por núcleo.

**Taxa de falsos positivos (FPR):** calcule a proporção de conexões ou mensagens legítimas classificadas incorretamente como maliciosas:

\[
FPR = \frac{FP}{FP + TN} \times 100
\]

Em que:

- \(FP\): conexões ou mensagens legítimas classificadas incorretamente como maliciosas.
- \(TN\): conexões ou mensagens legítimas corretamente classificadas como legítimas.

**Disponibilidade do broker:** se o limite de conexões for 1024, o número de conexões livres pode ser estimado por:

\[
N_{livres} = N_{limite} - N_{ocupadas}
\]

Essa estimativa só é válida quando as conexões ocupadas e o limite configurado usam a mesma definição de recurso. O número de conexões TCP estabelecidas não equivale necessariamente ao número de clientes MQTT autenticados e conectados.

**Latência de decisão:** documente se o valor representa latência por pacote, tempo de execução do programa eBPF, ou latência de ponta a ponta. Esses indicadores não são equivalentes.

**Vazão de descarte:** informe o número de pacotes descartados por segundo e o total de pacotes observados. A taxa percentual de descarte deve ser apresentada separadamente:

\[
Taxa_{descarte} = \frac{P_{descartados}}{P_{observados}} \times 100
\]

---

## 📈 3. Sugestão de Gráficos para o Artigo e a Dissertação

Recomenda-se gerar três gráficos principais utilizando Python e bibliotecas como `matplotlib` ou `seaborn`.

Os gráficos devem ser construídos a partir de dados efetivamente coletados nos quatro cenários experimentais.

### 3.1. Gráfico 1 — Consumo de CPU por núcleo no gateway ao longo do tempo

**Tipo:** gráfico de linhas (*time series*).

**Eixos:**

- Eixo X: tempo de execução do experimento, em segundos.
- Eixo Y: percentual de utilização de CPU por núcleo.

**Séries:**

- Baseline (`off`).
- Netfilter (`iptables`).
- eBPF Stateless (`stateless`).
- eBPF Stateful (`dfa`).

**Objetivo:** comparar o custo computacional das estratégias de mitigação durante o ataque.

O gráfico deverá permitir verificar se a filtragem em XDP reduz o processamento em comparação com a estratégia convencional, sem comprometer o funcionamento dos clientes legítimos.

**Dados necessários:**

| Campo | Descrição |
|---|---|
| `tempo_s` | Tempo decorrido desde o início do experimento. |
| `cenario` | Identificador do cenário avaliado. |
| `cpu_core` | Núcleo da CPU monitorado. |
| `cpu_percent` | Percentual de utilização do núcleo. |

**Interpretação esperada:** se os dados confirmarem a hipótese, os cenários eBPF/XDP apresentarão menor consumo de CPU no gateway em comparação ao cenário `iptables`, para condições equivalentes de tráfego.

Essa diferença deve ser demonstrada pelos dados, e não presumida com base apenas na arquitetura.

### 3.2. Gráfico 2 — Entrega de mensagens legítimas

**Tipo:** gráfico de barras agrupadas.

**Eixos:**

- Eixo X: perfis de sensores (`sensor-evento`, `sensor-sub` e `sensor-jitter`).
- Eixo Y: taxa de entrega de mensagens legítimas bem-sucedidas, em porcentagem.

**Séries:**

- Baseline (`off`).
- Netfilter (`iptables`).
- eBPF Stateless (`stateless`).
- eBPF Stateful (`dfa`).

**Objetivo:** avaliar se os mecanismos de mitigação preservam a comunicação dos sensores legítimos durante o ataque.

A taxa de entrega pode ser calculada por:

\[
Taxa_{entrega} = \frac{M_{recebidas}}{M_{enviadas}} \times 100
\]

Em que:

- \(M_{recebidas}\): quantidade de mensagens legítimas recebidas corretamente pelo destino.
- \(M_{enviadas}\): quantidade de mensagens legítimas enviadas pelo sensor.

**Dados necessários:**

| Campo | Descrição |
|---|---|
| `cenario` | Estratégia de mitigação utilizada. |
| `sensor` | Perfil do sensor legítimo. |
| `mensagens_enviadas` | Total de mensagens enviadas. |
| `mensagens_recebidas` | Total de mensagens recebidas corretamente. |
| `taxa_entrega` | Percentual de mensagens entregues com sucesso. |

**Interpretação esperada:** verificar se o cenário eBPF Stateful/DFA preserva uma taxa elevada de entrega para todos os perfis legítimos, inclusive sensores com longos períodos de silêncio ou tráfego irregular.

A taxa de entrega não deve ser confundida com a FPR: a primeira mede o sucesso da comunicação; a segunda mede a proporção de casos legítimos classificados incorretamente.

### 3.3. Gráfico 3 — Ocupação da tabela de conexões do Mosquitto

**Tipo:** gráfico de linhas (*line chart*). Um gráfico de área pode ser utilizado como alternativa, desde que a representação não sugira categorias que não foram medidas.

**Eixos:**

- Eixo X: tempo de execução, em segundos.
- Eixo Y: número de conexões TCP estabelecidas no broker.

**Séries:**

- Baseline (`off`).
- Netfilter (`iptables`).
- eBPF Stateless (`stateless`).
- eBPF Stateful (`dfa`).

**Objetivo:** avaliar a evolução das conexões simultâneas durante o ataque e verificar se a mitigação impede que o broker alcance o limite de recursos.

**Dados necessários:**

| Campo | Descrição |
|---|---|
| `tempo_s` | Tempo decorrido desde o início do experimento. |
| `cenario` | Estratégia de mitigação utilizada. |
| `conexoes_established` | Número de conexões TCP no estado `ESTABLISHED`. |
| `conexoes_mqtt` | Número de sessões MQTT ativas, se disponível. |
| `limite_conexoes` | Limite efetivamente configurado para o recurso monitorado. |

**Interpretação esperada:** verificar se a solução proposta reduz a ocupação de recursos no broker e mantém capacidade para novas conexões legítimas.

> **Nota técnica:** o XDP descarta pacotes antes de eles alcançarem a pilha de rede do host, desde que o programa esteja anexado ao ponto apropriado e o tráfego percorra esse caminho. Se o descarte for eficaz, a contagem de conexões maliciosas no broker poderá deixar de crescer ou diminuir conforme o encerramento das conexões existentes. Não se deve pressupor que conexões já estabelecidas desapareçam imediatamente após o descarte de novos pacotes.

---

## 🔬 4. Organização dos Dados Experimentais

Para facilitar a geração dos gráficos, recomenda-se manter os resultados em arquivos CSV separados por métrica ou em um conjunto de dados unificado.

### 4.1. Exemplo de estrutura para consumo de CPU

```csv
tempo_s,cenario,cpu_core,cpu_percent
0,off,0,0.5
5,off,0,0.6
10,off,0,0.7
0,iptables,0,15.0
5,iptables,0,21.0
10,iptables,0,30.0
```

Os números são apenas ilustrativos. Substitua-os pelos valores medidos.

### 4.2. Exemplo de estrutura para entrega de mensagens

```csv
cenario,sensor,mensagens_enviadas,mensagens_recebidas,taxa_entrega
off,sensor-evento,1000,990,99.0
iptables,sensor-sub,1000,800,80.0
stateless,sensor-jitter,1000,950,95.0
dfa,sensor-evento,1000,1000,100.0
```

Os números são fictícios e servem somente para demonstrar a estrutura do arquivo.

### 4.3. Exemplo de estrutura para conexões do broker

```csv
tempo_s,cenario,conexoes_established,conexoes_mqtt,limite_conexoes
0,off,10,10,1024
5,off,250,250,1024
10,off,700,700,1024
0,dfa,10,10,1024
5,dfa,15,15,1024
10,dfa,12,12,1024
```

Os valores são ilustrativos. A coleta deve distinguir conexões TCP estabelecidas de sessões MQTT efetivamente ativas sempre que possível.

---

## 📚 5. Recomendações para a Apresentação Científica

Para tornar os resultados adequados a um artigo científico ou dissertação:

1. Registre as versões do kernel Linux, Docker, Containerlab e Mosquitto.
2. Descreva a máquina utilizada, incluindo CPU, memória e configuração de rede.
3. Execute repetições independentes de cada cenário.
4. Mantenha constantes os parâmetros do ataque e a carga legítima durante as comparações.
5. Documente a ferramenta de coleta e a frequência de amostragem de cada métrica.
6. Apresente valores médios e medidas de dispersão, quando apropriado.
7. Diferencie resultados medidos, estimativas preliminares e hipóteses.
8. Disponibilize os dados brutos e os scripts de análise para permitir a reprodução dos gráficos.

## Conclusão

A análise conjunta do consumo de CPU, da entrega de mensagens legítimas e da ocupação das conexões do broker permite avaliar três aspectos complementares da solução: custo computacional, preservação do serviço legítimo e eficácia da mitigação.

A conclusão sobre a superioridade do eBPF Stateful/DFA deverá ser sustentada por medições reproduzíveis, com os mesmos critérios de comparação em todos os cenários.
