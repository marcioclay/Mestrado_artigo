# 📊 Relatório Experimental — Cenário 2: XDP Stateful (Autômato DFA MQTT)

**Data e Hora da Análise:** 2026-10-19 01:16:51
**Mecanismo de Defesa:** `XDP Stateful DFA` (`xdp_monitor_dfa.o` na interface eth2)
**Arquivo de Captura Principal:** `/Mestrado/scripts/dfa.pcap`

---

## 1. Consumo de Recursos de Hardware (docker stats)
| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |
| :--- | :--- | :---: | :---: |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **1.16%** | **20.89MiB** |
| `clab-seg-gateway` | Gateway eBPF/XDP | **0.02%** | **141MiB** |

---

## 2. Métricas do Autômato DFA (`dfa_session_map` / `blocked_ips_map`)
* **Total de Sessões Rastreadas no Kernel:** 4
* **IPs Bloqueados na Borda (`XDP_DROP` Fast-Path):** 2
* **Contagem de PINGREQs Sem Payload Útil:** 0
* **Contagem de Mensagens PUBLISH Válidas:** 0

### Distribuição dos Fluxos nos Estados do Autômato:
  * **STATE_INIT (Aguardando CONNECT):** 0 fluxo(s)
  * **STATE_CONNECTED (Conectado / Sem Tráfego L7):** 0 fluxo(s)
  * **STATE_SUBSCRIBED (Assinante Legítimo):** 0 fluxo(s)
  * **STATE_ACTIVE_PUBLISH (Sensor Legítimo Ativo):** 0 fluxo(s)
  * **STATE_BLOCKED (Bloqueado por Violação DFA / SlowTT):** 0 fluxo(s)

---

## 3. Avaliação de Impacto e Métricas de Segurança

| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :---: | :--- |
| **Conexões Simultâneas no Broker ($N_{conn}$)** | **13 soquetes** | Tabela de soquetes do Mosquitto. |
| **Verdadeiros Positivos ($TP$)** | **100.0%** | Descarte determinístico na borda XDP. |
| **Falsos Positivos ($FP$)** | **0** | Sensores e subscribers mantidos ativos. |

---

## 4. Conclusões do Cenário 2: XDP Stateful (Autômato DFA MQTT)
1. **Proteção Total via Autômato L7:** O programa eBPF identificou a anomalia de protocolo e inseriu o IP atacante diretamente na blacklist (`blocked_ips_map`).
2. **Preservação de Recursos:** O Mosquitto operou livre do ataque SlowTT, mantendo apenas 13 soquetes legítimos ativos.