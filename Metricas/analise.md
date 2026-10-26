# 🧪 Bateria de Experimentos Isolados

| Cenário | Configuração experimental | Métricas avaliadas |
|---|---|---|
| **Cenário A — Apenas Tráfego Legítimo (Baseline Normal)** | Executar `sensor_evento`, `sensor_sub` e `sensor_jitter`, sem tráfego de ataque. | - Taxa de falsos positivos (FPR), com meta de 0,0%.<br>- Latência de referência (RTT).<br>- Consumo de CPU e RAM em repouso. |
| **Cenário B — Apenas Ataque SlowTT (Capacidade Bruta de Reação)** | Executar a botnet SlowTT simulada, com 31 IPs de origem e 310 conexões. | - Taxa de detecção (TPR), com meta de 100%.<br>- Tempo de detecção (\(T_{det}\)).<br>- Número de conexões retidas e estado dos soquetes. |
| **Cenário C — Tráfego Misto (Legítimos + Ataque Simultâneos)** | Executar os sensores legítimos e a botnet SlowTT simultaneamente, durante o mesmo intervalo experimental. | - Taxa de detecção (TPR) e taxa de falsos positivos (FPR).<br>- Dispersão do RTT dos sensores durante a mitigação.<br>- Continuidade da entrega de mensagens legítimas. | 


| Defesa | Cenário | RAM Gateway | $N_{conn}$ (Pico) | `CONNECT` | `PINGREQ` | Perda Telemetria | Disp. $S_{check}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OFF** | Legítimo | 4.41 MiB | 5 | 33 | 3 | 25.0% | 100.0% |
| **OFF** | Atacante | 4.27 MiB | **1025** | 1128 | 3091 | 0.0% | 47.3% |
| **OFF** | Todos | 4.32 MiB | **1025** | 1133 | 3066 | 50.0% | **45.0%** |
| **IPTables** | Legítimo | 4.34 MiB | 3 | 26 | 0 | 0.0% | 100.0% |
| **IPTables** | Atacante | 4.55 MiB | 158 | 181 | 0 | 0.0% | 100.0% |
| **IPTables** | Todos | 4.35 MiB | 160 | 162 | 58 | 10.0% | **33.3%** |
| **Stateful** | Legítimo | 4.52 MiB | 2 | 28 | 106 | 100.0% | 100.0% |
| **Stateful** | Atacante | 4.55 MiB | **1024** | 1128 | 155 | 0.0% | 100.0% |
| **Stateful** | Todos | 4.55 MiB | 183 | 208 | 178 | 38.9% | 100.0% |
| **DFA** | Legítimo | 6.07 MiB | 3 | 0 | 0 | 0.0% | 25.0% |
| **DFA** | Atacante | 5.91 MiB | **127** | 96 | 0 | 0.0% | 25.0% |
| **DFA** | Todos | 5.96 MiB | **129** | 125 | 3 | 40.9% | **100.0%** |
