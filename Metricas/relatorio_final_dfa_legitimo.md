# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** DFA | **Cenário:** LEGITIMO

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 3 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.10% | RAM: 27.63 MiB
* **Broker (Alvo):** CPU: 0.19% | RAM: 27.26 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** — (Sem ataque no cenário)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 0.00% (99 entregues de 99 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 2.65 ms | P95: 6.87 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 2.97 kbps
* **Pacotes por Segundo:** 4.37 pps
