# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** IPTABLES | **Cenário:** ATACANTE

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** 155 soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: 0.02% | RAM: 23.74 MiB
* **Broker (Alvo):** CPU: 1.76% | RAM: 26.12 MiB

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** 14.09% (155 conexões de 1100 tentativas)
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** — (Sem sensores no cenário)

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** —

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** 169.43 kbps
* **Pacotes por Segundo:** 246.11 pps
