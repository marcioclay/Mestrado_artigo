# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** OFF | **Cenário:** TODOS

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 1024 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.12% | RAM: 23.79 MiB
* **Broker (Alvo):** CPU: 2.22% | RAM: 30.25 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** 92.82% (1021 conexões de 1100 tentativas)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 0.97% (102 entregues de 103 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 6.36 ms | P95: 3.23 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 49.55 kbps
* **Pacotes por Segundo:** 73.50 pps
