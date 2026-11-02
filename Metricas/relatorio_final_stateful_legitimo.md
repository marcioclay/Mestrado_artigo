# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** STATEFUL | **Cenário:** LEGITIMO

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 3 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.05% | RAM: 26.22 MiB
* **Broker (Alvo):** CPU: 0.26% | RAM: 22.29 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** — (Sem ataque no cenário)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 38.89% (66 entregues de 108 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 2.92 ms | P95: 4.58 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 0.54 kbps
* **Pacotes por Segundo:** 0.68 pps
