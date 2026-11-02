# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** DFA | **Cenário:** TODOS

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 127 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.14% | RAM: 27.83 MiB
* **Broker (Alvo):** CPU: 1.60% | RAM: 22.74 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** 8.45% (93 conexões de 1100 tentativas)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 0.00% (101 entregues de 101 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 3.36 ms | P95: 7.23 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 0.91 kbps
* **Pacotes por Segundo:** 1.19 pps
