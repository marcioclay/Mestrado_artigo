# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** STATEFUL | **Cenário:** TODOS

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 1024 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.23% | RAM: 26.24 MiB
* **Broker (Alvo):** CPU: 2.36% | RAM: 29.26 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** 92.82% (1021 conexões de 1100 tentativas)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 40.19% (64 entregues de 107 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 2.65 ms | P95: 4.76 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 7.77 kbps
* **Pacotes por Segundo:** 11.46 pps
