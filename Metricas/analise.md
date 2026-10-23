# 🧪 Bateria de Experimentos Isolados

| Cenário | Configuração experimental | Métricas avaliadas |
|---|---|---|
| **Cenário A — Apenas Tráfego Legítimo (Baseline Normal)** | Executar `sensor_evento`, `sensor_sub` e `sensor_jitter`, sem tráfego de ataque. | - Taxa de falsos positivos (FPR), com meta de 0,0%.<br>- Latência de referência (RTT).<br>- Consumo de CPU e RAM em repouso. |
| **Cenário B — Apenas Ataque SlowTT (Capacidade Bruta de Reação)** | Executar a botnet SlowTT simulada, com 31 IPs de origem e 310 conexões. | - Taxa de detecção (TPR), com meta de 100%.<br>- Tempo de detecção (\(T_{det}\)).<br>- Número de conexões retidas e estado dos soquetes. |
| **Cenário C — Tráfego Misto (Legítimos + Ataque Simultâneos)** | Executar os sensores legítimos e a botnet SlowTT simultaneamente, durante o mesmo intervalo experimental. | - Taxa de detecção (TPR) e taxa de falsos positivos (FPR).<br>- Dispersão do RTT dos sensores durante a mitigação.<br>- Continuidade da entrega de mensagens legítimas. |
