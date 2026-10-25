# 🧪 Bateria de Experimentos Isolados

| Cenário | Configuração experimental | Métricas avaliadas |
|---|---|---|
| **Cenário A — Apenas Tráfego Legítimo (Baseline Normal)** | Executar `sensor_evento`, `sensor_sub` e `sensor_jitter`, sem tráfego de ataque. | - Taxa de falsos positivos (FPR), com meta de 0,0%.<br>- Latência de referência (RTT).<br>- Consumo de CPU e RAM em repouso. |
| **Cenário B — Apenas Ataque SlowTT (Capacidade Bruta de Reação)** | Executar a botnet SlowTT simulada, com 31 IPs de origem e 310 conexões. | - Taxa de detecção (TPR), com meta de 100%.<br>- Tempo de detecção (\(T_{det}\)).<br>- Número de conexões retidas e estado dos soquetes. |
| **Cenário C — Tráfego Misto (Legítimos + Ataque Simultâneos)** | Executar os sensores legítimos e a botnet SlowTT simultaneamente, durante o mesmo intervalo experimental. | - Taxa de detecção (TPR) e taxa de falsos positivos (FPR).<br>- Dispersão do RTT dos sensores durante a mitigação.<br>- Continuidade da entrega de mensagens legítimas. | 


| Defesa | Cenário | RAM Gateway | $N_{conn}$ (Pico) | `CONNECT` | `PINGREQ` | Perda Telemetria | Disp. $S_{check}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OFF** | Legítimo | 22.32 MiB | 6 | 30 | 4 | 48.1% | 100.0% |
| **OFF** | Atacante | 22.84 MiB | **312** | 336 | 949 | 0.0% | 100.0% |
| **OFF** | Todos | 23.53 MiB | **316** | 342 | 992 | **50.0%** | 100.0% |
| **IPTables** | Legítimo | 23.43 MiB | 3 | 25 | 0 | 0.0% | 100.0% |
| **IPTables** | Atacante | 23.60 MiB | **158** | 183 | 0 | 0.0% | 100.0% |
| **IPTables** | Todos | 23.84 MiB | **160** | 162 | 15 | 43.8% | 30.8% |
| **Stateful** | Legítimo | 23.86 MiB | 3 | 25 | 0 | 100.0% | 100.0% |
| **Stateful** | Atacante | 24.29 MiB | **313** | 338 | 155 | 0.0% | 100.0% |
| **Stateful** | Todos | 24.43 MiB | **316** | 342 | 189 | **50.0%** | 100.0% |
| **DFA** | Legítimo | 25.82 MiB | 3 | 2 | 103 | 0.0% | 25.0% |
| **DFA** | Atacante | 26.08 MiB | **127** | 95 | 0 | 0.0% | 25.0% |
| **DFA** | Todos | 25.98 MiB | **130** | 125 | 46 | **8.3%** | 100.0% |
