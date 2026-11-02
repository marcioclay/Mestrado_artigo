# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** OFF | **Cenário:** LEGITIMO

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 3 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.02% | RAM: 23.41 MiB
* **Broker (Alvo):** CPU: 0.20% | RAM: 25.73 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** — (Sem ataque no cenário)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 0.00% (102 entregues de 102 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 1.47 ms | P95: 3.83 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 0.42 kbps
* **Pacotes por Segundo:** 0.47 pps
