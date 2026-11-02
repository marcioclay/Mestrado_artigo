# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** IPTABLES | **Cenário:** TODOS

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 158 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.12% | RAM: 23.73 MiB
* **Broker (Alvo):** CPU: 0.73% | RAM: 23.00 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** 14.09% (155 conexões de 1100 tentativas)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** 0.00% (99 entregues de 99 enviadas)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** Média: 2.20 ms | P95: 4.49 ms

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 0.95 kbps
* **Pacotes por Segundo:** 1.24 pps
