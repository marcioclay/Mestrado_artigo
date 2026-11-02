# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** OFF | **Cenário:** ATACANTE

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 1024 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.16% | RAM: 23.70 MiB
* **Broker (Alvo):** CPU: 3.24% | RAM: 30.56 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** 93.09% (1024 conexões de 1100 tentativas)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** — (Sem sensores no cenário)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** —

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 49.68 kbps
* **Pacotes por Segundo:** 73.86 pps
