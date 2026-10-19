# 📊 Relatório Experimental — Cenário 1: XDP Stateless (Filtro por Limiar)

**Data e Hora da Análise:** 2026-10-18 23:26:00
**Mecanismo de Defesa:** `XDP Stateless` (Programa eBPF `xdp_stateless.o` ativo na eth2)
**Arquivo de Captura Principal:** `/Mestrado/scripts/stateless.pcap`

---

## 1. Consumo de Recursos de Hardware (docker stats)
Métricas observadas nos contêineres durante o estado de ataque sob mitigação por limiar:

| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |
| :--- | :--- | :---: | :---: |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **0,94%** | **23,99 MiB** |
| `clab-seg-gateway` | Gateway eBPF/XDP | **0,02%** | **139,10 MiB** |

---

## 2. Métricas Extraídas do Kernel Linux (bpftool ip_rate_map)
Métricas obtidas diretamente da tabela hash de rastreio por IP no driver de rede:

* **Endereços IP Monitorizados no Mapa:** 4 fluxos activos
* **Contagem total de pacotes avaliados pelo eBPF:** 24 pacotes
* **Distribuição de Pacotes por Fluxo:**
  * IP `167.83.77.06` (Chave `167837706`): **5 pacotes**
  * IP `335.60.98.66` (Chave `335609866`): **10 pacotes**
  * IP `201.39.21.38` (Chave `201392138`): **2 pacotes**
  * IP `184.61.49.22` (Chave `184614922`): **7 pacotes**

---

## 3. Avaliação de Impacto e Métricas de Segurança

| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :---: | :--- |
| **Conexões Simultâneas no Broker ($N_{conn}$)** | **231 a 401 soquetes** | Redução substancial face ao colapso do Baseline (1024 conexões). |
| **Ação do eBPF/XDP** | **RATE-LIMITING** | Descarte na borda de pacotes que excedam 30 pps por IP. |
| **Impacto no Processamento do Gateway** | **< 0,02% CPU** | Inspeção ultraleve realizada antes da alocação de `sk_buff`. |
| **Falsos Positivos ($FP$)** | **0** | Dispositivos legítimos dentro do limite mantêm operação. |

---

## 4. Conclusões do Cenário XDP Stateless
1. **Contenção Parcial do Ataque:** O filtro por limiar estático (`MAX_PACKETS_PER_SEC = 30`) impediu que o atacante preenchesse totalmente a tabela do Mosquitto, mantendo as conexões presas oscilando entre 231 e 401 soquetes.
2. **Eficiência no Kernel:** O descarte de pacotes excedentes na camada de driver manteve o uso de CPU do Gateway em 0,02%.
3. **Necessidade do Autómato (DFA):** Como o filtro Stateless opera apenas na L3/L4, pacotes do ataque enviados dentro da cota de 30 pps ainda conseguem abrir soquetes. Este comportamento valida a necessidade do **Cenário 2 (XDP Stateful / DFA)** para inspecionar a gramática MQTT e zerar os soquetes maliciosos.
