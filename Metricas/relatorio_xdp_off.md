# 📊 Relatório Experimental — Cenário 0: Baseline sem Proteção (XDP OFF)

**Data e Hora da Análise:** 2026-10-18 17:54:54  
**Mecanismo de Defesa:** NENHUM (`OFF` - Gateway atuando via roteamento padrão)  
**Arquivo de Captura Principal:** `/Mestrado/scripts/baseline_off.pcap`  

---

## 1. Consumo de Recursos de Hardware (docker stats)
Métricas observadas nos contêineres durante a exaustão do ataque SlowTT:

| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |
| :--- | :--- | :--- | :--- |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **0.23%** | **26.33 MiB** |
| `clab-seg-gateway` | Gateway eBPF/XDP | **0.00%** | **17.12 MiB** |

---

## 2. Análise da Camada de Rede e Transporte (L3/L4 - PCAP)
Métricas extraídas da interface LAN `eth2` do Gateway:

* **Total de Pacotes Capturados:** 63.117 pacotes
* **Duração da Captura:** 763,09 segundos (~12,7 minutos)
* **Tamanho Total dos Dados:** 4.372.070 bytes (~4,37 MB)
* **Taxa Média de Pacotes:** **82,71 pps** (pacotes/s)
* **Largura de Banda Média:** **45,84 kbps**
* **Pacotes com "TCP Zero Window" (Slow Read):** 391

---

## 3. Análise da Camada de Aplicação (L7 - MQTT)
Detalhamento das mensagens do protocolo MQTT interceptadas:

* **Pacotes `CONNECT` (Solicitações de Sessão):** 3.101
* **Pacotes `PUBLISH` (Telemetria Legítima):** 259
* **Pacotes `PINGREQ` (Manutenção Keep-Alive / SlowTT):** 14.286
* **Razão de Payload Útil ($R_{payload}$):** **1,47%**
* **Mensagens Legítimas Entregues ao Subscriber:** 130 de 259 (Perda/bloqueio de **49,8%**)

---

## 4. Avaliação de Impacto e Métricas de Segurança

| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :--- | :--- |
| **Conexões Simultâneas no Broker ($N_{conn}$)** | **1024 soquetes** | Limite máximo de conexões atingido. |
| **Disponibilidade para Novo Cliente** | **Timed Out** | Negação de Serviço confirmada na aplicação. |
| **Falsos Positivos ($FP$)** | **0** | Não aplicável (sem regras de descarte ativas). |
| **Verdadeiros Positivos ($TP$)** | **0** | Nenhum pacote malicioso foi descartado na borda. |
| **Taxa de Detecção ($TPR$)** | **0.0%** | Ataque passou integralmente pelo Gateway. |
| **Taxa de Falsos Positivos ($FPR$)** | **0.0%** | Nenhuma conexão legítima foi bloqueada ativamente. |

---

## 5. Conclusões do Cenário Baseline
1. **Exaustão de Soquetes:** O ataque SlowTT ocupou 1024 conexões no Mosquitto, consumindo 26.33 MiB de RAM com uso de CPU de 0.23%.
2. **Bloqueio e Perda de Telemetria:** O teste de disponibilidade para novos clientes resultou em `Timed Out` e 49,8% das mensagens dos sensores ativos não foram entregues.
3. **Comportamento do Gateway:** O Gateway sem eBPF/XDP (0.00% CPU / 17.12 MiB RAM) repassou 100% do tráfego malicioso a uma taxa de 45,84 kbps, incapaz de conter o DoS.
