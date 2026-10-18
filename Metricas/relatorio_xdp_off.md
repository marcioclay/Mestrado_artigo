# 📊 Relatório Experimental — Cenário 0: Baseline sem Proteção (XDP OFF)

**Data e Hora da Análise:** 2026-10-18 16:26:49
**Mecanismo de Defesa:** NENHUM (`OFF` - Gateway atuando via roteamento padrão)
**Arquivo de Captura Principal:** `/Mestrado/scripts/baseline_off.pcap`

---

## 1. Consumo de Recursos de Hardware (docker stats)
Métricas observadas nos contêineres durante o estado de DoS do ataque SlowTT:

| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |
| :--- | :--- | :--- | :--- |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **0,06** | **43,4** |
| `clab-seg-gateway` | Gateway eBPF/XDP | **0,00** | **15.64** |

---

## 2. Análise da Camada de Rede e Transporte (L3/L4 - PCAP)
Métricas extraídas da interface LAN `eth2` do Gateway:

* **Total de Pacotes Capturados:** 32499 pacotes
* **Pacotes com "TCP Zero Window" (Slow Read):** 1
* **Resumo Técnico da Captura (`capinfos`):**
```text
File name:           /Mestrado/scripts/baseline_off.pcap
Data size:           2243186 bytes
Capture duration:    857,047548 seconds
```

---

## 3. Análise da Camada de Aplicação (L7 - MQTT)
Detalhamento das mensagens do protocolo MQTT interceptadas:

* **Pacotes `CONNECT` (Solicitações de Sessão):** 1034
* **Pacotes `PUBLISH` (Telemetria Legítima):** 307
* **Pacotes `PINGREQ` (Manutenção Keep-Alive / SlowTT):** 8205
* **Mensagens Legítimas Entregues ao Subscriber:** 155

---

## 4. Avaliação de Impacto e Métricas de Segurança

| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :--- | :--- |
| **Conexões Retidas pelo Atacante** | ~[2026-10-18 14:50:26] [*] Encerrando conexões... soquetes | Tabela de soquetes do Mosquitto esgotada. |
| **Falsos Positivos ($FP$)** | **0** | Não aplicável (sem regras de descarte ativas). |
| **Verdadeiros Positivos ($TP$)** | **0** | Nenhum pacote malicioso foi descartado na borda. |
| **Taxa de Detecção ($TPR$)** | **0.0%** | Ataque passou integralmente pelo Gateway. |
| **Taxa de Falsos Positivos ($FPR$)** | **0.0%** | Nenhuma conexão legítima foi bloqueada ativamente. |

---

## 5. Conclusões do Cenário Baseline
1. **Exaustão Furtiva de Soquetes:** O ataque Slow DoS manteve ~1024 conexões presas consumindo 43,4 de RAM com uso de CPU próximo de zero (0,06), demonstrando a furtividade inerente aos ataques de baixa taxa.
2. **Degradação de Serviço Legítimo:** Com a tabela do Mosquitto lotada, novos clientes legítimos são rejeitados na camada de transporte.
3. **Ausência de Mitigação no Gateway:** O Gateway sem eBPF/XDP (0,00 CPU / 15.64 RAM) atua como mero repassador de tráfego, permitindo o colapso do Broker.