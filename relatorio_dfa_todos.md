# 📊 Relatório Experimental — Cenário: TODOS | Defesa: DFA

**Data e Hora da Análise:** 2026-11-01 18:57:07
**Mecanismo de Defesa:** eBPF/XDP Stateful com Validação Formal via Autômato Finito Determinístico
**Arquivo de Captura Principal:** `/Mestrado/scripts/captura_dfa_todos.pcap`
**Série Temporal (CPU/RAM/Nconn):** `/Mestrado/scripts/metricas_tempo_real_dfa_todos.csv`
**Latência/PDR (seq):** `/Mestrado/scripts/latencia_mensagens.csv`

---

## 1. Consumo de Recursos de Hardware (amostragem contínua, 1 amostra/s)
Estatísticas calculadas sobre toda a janela do ensaio, não um valor pontual:

| Contêiner | Função | CPU | RAM |
| :--- | :--- | :--- | :--- |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | média 0.09% | pico 0.45% | σ 0.06% (n=128) | média 18.89 MB | pico 19.57 MB | σ 0.20 MB (n=128) |
| `clab-seg-gateway` | Gateway eBPF/XDP | média 0.01% | pico 0.23% | σ 0.02% (n=128) | média 13.97 MB | pico 14.21 MB | σ 0.06 MB (n=128) |

---

## 2. Ocupação de Conexões no Broker (Nconn)
Calculado sobre a série temporal completa, não mais uma amostra única no meio do teste:

* **Pico de Conexões Simultâneas (ESTAB):** **129**
* **Média de Conexões Simultâneas:** 20.7
* **Desvio-Padrão:** 39.7
* **Amostras Coletadas:** 128

---

## 3. Análise da Camada de Rede e Transporte (L3/L4 - PCAP)
Métricas extraídas da interface de rede do Gateway:

* **Total de Pacotes Capturados:** 726 pacotes
* **Duração da Captura:** 601.77 segundos (~10.0 minutos)
* **Volume Total de Dados:** 69,857 bytes (~0.07 MB)
* **Vazão Média de Pacotes:** **1.21 pps**
* **Largura de Banda Média Consumida:** **0.93 kbps**
* **Pacotes com "TCP Zero Window" (Slow Read, via tshark):** 0
* **Resumo Técnico da Captura (`capinfos`):**
```text
File name:           /Mestrado/scripts/captura_dfa_todos.pcap
Data size:           58217 bytes
Capture duration:    601.771882 seconds
```

---

## 4. Análise da Camada de Aplicação (L7 - MQTT, dissecção via tshark)
Contagem feita com remontagem real de segmentos TCP (`tshark -Y mqtt`):

* **Pacotes TCP na Porta 1883 (independente do dissector MQTT):** 726
* **Pacotes `CONNECT`:** 0
* **Pacotes `SUBSCRIBE`:** 0
* **Pacotes `PUBLISH` (Telemetria Legítima):** 107
* **Pacotes `PINGREQ` (Manutenção Keep-Alive / SlowTT):** 0
* **Razão de Payload Útil ($R_{payload}$):** **100.00%**
* **Throughput de PUBLISH (medido no PCAP):** **0.178 msg/s**

---

## 5. Latência e PDR por Sequência (métrica recomendada)
* **Mensagens Recebidas Processadas:** 107
* **Latência Média:** 1.74 ms
* **Latência P50:** 1.44 ms
* **Latência P95:** **3.01 ms**
* **Latência P99:** 5.35 ms
* **PDR Global (por sequência):** **100.00%** (Perda: 0.00%)
* **Total Recebidas / Maior Seq. Observada:** 107 / 107

| Tópico | Recebidas | Maior Seq. Observada | PDR (%) | Perda (%) |
| :--- | :--- | :--- | :--- | :--- |
| `iot/sensores/clima` | 61 | 61 | 100.00% | 0.00% |
| `iot/sensores/evento` | 46 | 46 | 100.00% | 0.00% |

> ⚠️ PDR por sequência assume seq iniciando em 1 e incrementando de 1 em 1 por tópico.
> Se a ÚLTIMA mensagem enviada for justamente a perdida, a maior seq. observada subestima
> o total enviado, e o PDR fica levemente otimista nesse caso-limite.

---

## 6. Métrica de Perda Legada (pacotes PCAP vs. log — mantida para comparação)
* **Mensagens Legítimas Entregues (log) / Pacotes PUBLISH (PCAP):** 107 de 107
* **Perda Legada:** 0.0%
> ⚠️ Esta métrica compara unidades diferentes (pacote TCP no PCAP vs. linha de log do subscriber)
> e deve ser substituída pela Seção 5 (PDR por sequência) assim que validada em campo.

---

## 7. Avaliação de Impacto e Disponibilidade Continuada

### 📈 Métricas de Disponibilidade do $S_{check}$
* **Status:** Nenhum dado do $S_{check}$ registrado para este ensaio.

| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :--- | :--- |
| **Pico de Conexões Simultâneas ($N_{conn}$)** | **129** | Máximo real observado na série temporal. |
| **Disponibilidade para Novos Clientes ($S_{check}$)** | **0.0%** | Capacidade de processar novas conexões legítimas. |
| **PDR Global (por sequência)** | **100.00%** | Fração real de mensagens legítimas entregues. |
| **Latência P95** | **3.01 ms** | Degradação da comunicação legítima sob ataque. |

---

*Relatório gerado automaticamente para o Cenário: TODOS | Defesa: DFA.*