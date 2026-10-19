# 📊 Relatório Experimental — Cenário 2: XDP Stateful (Autômato DFA MQTT)

**Data e Hora da Análise:** 2026-10-19 01:28:00
**Mecanismo de Defesa:** `XDP Stateful DFA` (`xdp_monitor_dfa.o` carregado na interface `eth2`)
**Arquivo de Captura Principal:** `/Mestrado/scripts/dfa.pcap`

---

## 1. Consumo de Recursos de Hardware (docker stats)
Métricas registradas nos contêineres sob mitigação ativa do autômato:

| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |
| :--- | :--- | :---: | :---: |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **1,16%** | **20,89 MiB** |
| `clab-seg-gateway` | Gateway eBPF/XDP | **0,02%** | **141,00 MiB** |

---

## 2. Métricas do Autômato DFA (`dfa_session_map` e `blocked_ips_map`)
Dados extraídos diretamente das tabelas Hash do Kernel Linux via `bpftool`:

* **Total de Sessões Monitoradas no Kernel:** 4 fluxos ativos
* **IPs Bloqueados em Fast-Path (`blocked_ips_map`):** 1 IP (Chave `335609866`)
* **Total de PINGREQs Maliciosos Interceptados:** 6 pacotes
* **Total de Mensagens PUBLISH Legítimas Processadas:** 74 pacotes (55 + 19)

### Distribuição dos Fluxos nos Estados do Autômato:
* **`STATE_INIT` (0 - Aguardando CONNECT):** 0 fluxos
* **`STATE_CONNECTED` (1 - Conectado / Subscrito):** 2 fluxos (`sensor_evento` e `sensor_sub`)
* **`STATE_SUBSCRIBED` (2 - Assinante Legítimo):** 0 fluxos
* **`STATE_ACTIVE_PUBLISH` (3 - Sensor Legítimo Ativo):** 1 fluxo (`sensor_jitter`)
* **`STATE_BLOCKED` (4 - Bloqueado por Violação DFA / SlowTT):** 1 fluxo (`atacante`)

---

## 3. Avaliação de Impacto e Métricas de Segurança

| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :---: | :--- |
| **Conexões Simultâneas no Broker ($N_{conn}$)** | **13 soquetes** | Tabela do Mosquitto completamente preservada. |
| **Verdadeiros Positivos ($TP$)** | **100,0%** | Descarte determinístico dos pacotes SlowTT via `XDP_DROP`. |
| **Falsos Positivos ($FP$)** | **0** | Dispositivos legítimos mantiveram a transmissão de telemetria. |
| **Desempenho do Gateway** | **0,02% CPU** | Inspeção L7 em tempo constante $O(1)$ sem overhead para o sistema. |

---

## 4. Conclusões do Cenário 2: XDP Stateful (Autômato DFA MQTT)
1. **Identificação e Mitigação L7 Eficiente:** O autômato eBPF monitorou com sucesso a gramática do protocolo MQTT. Ao identificar que o atacante acumulou 6 pacotes `PINGREQ` sem envio de payload útil, realizou a transição para `STATE_BLOCKED` e inseriu o IP no `blocked_ips_map`.
2. **Descarte em Nível de Driver:** Os pacotes subsequentes do atacante foram descartados diretamente na interface de rede (`eth2`) antes da alocação de memória no kernel (`sk_buff`), reduzindo as conexões no Broker de 1024 (Baseline) para apenas 13 soquetes legítimos.
3. **Ausência de Falsos Positivos:** Os sensores de evento e jitter acumularam 74 publicações com sucesso, confirmando que a validação de estados L7 impede a retenção indevida de conexões legítimas.
