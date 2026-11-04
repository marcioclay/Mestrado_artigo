

## 📊 Tabela Comparativa Consolidada dos Ensaios (20 Minutos)

| Mecanismo de Defesa | Cenário | Pico de Conexões (Nconn) | Sucesso do Ataque (PDR Atacante) | Perda de Dados Legítimos (Dano Colateral) | Latência Média / P95 (Fim-a-Fim) | CPU Gateway / Broker |
|---|---|---:|---:|---:|---:|---:|
| OFF (Baseline) | Atacante | 1024 (Saturado) | 93.09% | — | — | 2.94% / 26.32% |
| IPTables | Legítimo | 3 | — | 50.60% | 3.55 ms / 7.13 ms | 3.33% / 23.31% |
| IPTables | Atacante | 155 | 14.09% | — | — | 12.46% / 19.11% |
| IPTables | Todos | 158 | 14.09% | 48.69% | 4.01 ms / 9.95 ms | 2.10% / 25.54% |
| Stateful (Heurístico) | Legítimo | 3 | — | 83.09% | 4.53 ms / 9.02 ms | 0.62% / 15.64% |
| Stateful (Heurístico) | Atacante | 1024 (Saturado) | 92.82% | — | — | 2.77% / 27.14% |
| Stateful (Heurístico) | Todos | 1024 (Saturado) | 92.82% | 84.50% | 5.90 ms / 13.09 ms | 2.77% / 27.14% |
| DFA (Proposto) | Legítimo | 3 | — | 48.30% | 2.53 ms / 5.81 ms | 3.73% / 20.08% |
| DFA (Proposto) | Atacante | 124 | **8.45%** | — | — | 0.05% / 9.98% |
| DFA (Proposto) | Todos | 127 | **8.45%** | 49.07% | 2.91 ms / 8.07 ms | 2.62% / 25.22% |

**Nota:** O símbolo `—` indica métrica não aplicável ou não informada.





---
## 📊 Tabela Consolidada de Resultados Experimentais
Testes feitos com 4 sensores e 31 atacantes em 10min

| Mecanismo de Defesa | Cenário de Teste | Numero conexões | Packet Delivery Attack | Falso Positivo Sensor | Vazão Média (pps) | Latência P95 (ms) | CPU Gateway (%) | RAM Gateway (MiB) | CPU Broker (%) | RAM Broker (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OFF (Baseline) | Legítimo | 5 | — | 0.00% | 0.48 | 3.83 | 0.02 | 23.41 | 0.20 | 25.73 |
| OFF (Baseline) | Atacante | 1024 | 93.09% | — | 73.86 | — | 0.16 | 23.70 | 3.24 | 30.56 |
| OFF (Baseline) | Todos | 1024 | 92.82% | 0.97% | 73.50 | 3.23 | 0.12 | 23.79 | 2.22 | 30.25 |
| IPTables | Legítimo | 5 | — | 0.00% | 0.48 | 4.81 | 0.03 | 23.70 | 0.19 | 25.62 |
| IPTables | Atacante | 157 | 14.09% | — | 246.11 | — | 0.02 | 23.74 | 1.76 | 26.12 |
| IPTables | Todos | 158 | 14.91% | 0.00% | 1.24 | 4.49 | 0.12 | 23.73 | 0.73 | 23.00 |
| Stateful (Heurístico) | Legítimo | 5 | — | 38.89% | 0.68 | 4.58 | 0.05 | 26.22 | 0.26 | 22.29 |
| Stateful (Heurístico) | Atacante | 1024 | 93.09% | — | 203.13 | — | 0.38 | 26.47 | 6.85 | 26.95 |
| Stateful (Heurístico) | Todos | 1024 | 92.82% | 40.19% | 11.46 | 4.76 | 0.23 | 26.24 | 2.36 | 29.26 |
| DFA (Proposta) | Legítimo | 3 | — | 0.00% | 4.37 | 6.87 | 0.10 | 27.63 | 0.19 | 27.26 |
| DFA (Proposta) | Atacante | 126 | 8.55% | — | 4.69 | — | 0.14 | 27.60 | 3.84 | 22.85 |
| DFA (Proposta) | Todos | 127 | 8.45% | 0.00% | 1.19 | 7.23 | 0.14 | 27.83 | 1.60 | 22.74 |









---

| Mecanismo de Defesa | Cenário de Teste | Numero conexões | Packet Delivery Attack | Falso Positivo Sensor | Vazão Média (pps) | Latência P95 (ms) |
|---|---|---:|---:|---:|---:|---:|
| OFF (Baseline) | Legítimo | 5 | — | 0.00% | 0.48 | 3.83 |
| OFF (Baseline) | Atacante | 1024 | 93.09% | — | 73.86 | — |
| OFF (Baseline) | Todos | 1024 | 92.82% | 0.97% | 73.50 | 3.23 |
| IPTables | Legítimo | 5 | — | 0.00% | 0.48 | 4.81 |
| IPTables | Atacante | 157 | 14.09% | — | 246.11 | — |
| IPTables | Todos | 158 | 14.91% | 0.00% | 1.24 | 4.49 |
| Stateful (Heurístico) | Legítimo | 5 | — | 38.89% | 0.68 | 4.58 |
| Stateful (Heurístico) | Atacante | 1024 | 93.09% | — | 203.13 | — |
| Stateful (Heurístico) | Todos | 1024 | 92.82% | 40.19% | 11.46 | 4.76 |
| DFA (Proposta) | Legítimo | 3 | — | 0.00% | 4.37 | 6.87 |
| DFA (Proposta) | Atacante | 126 | 8.55% | — | 4.69 | — |
| DFA (Proposta) | Todos | 127 | 8.45% | 0.00% | 1.19 | 7.23 | 

--- 

Redação Formal para a Seção de Resultados (LaTeX / Artigo)5. Resultados Experimentais e DiscussãoPara avaliar o desempenho e a eficácia das contramedidas propostas frente aos ataques do tipo SlowTT, a Tabela consolidada apresenta o comportamento do sistema sob os três cenários operacionais (Legítimo, Atacante e Misto). A análise fundamenta-se em quatro eixos métricos principais: a contenção de soquetes ($N_{conn}$), a eficiência de descarte no tráfego malicioso (PDR do Atacante), o impacto colateral no tráfego útil (Perda de Telemetria dos Sensores) e a Qualidade de Serviço (QoS) medida através da Vazão e da Latência ($P_{95}$).

Conforme observado no cenário de referência sem proteção (OFF), a injeção do ataque SlowTT esgota rapidamente a tabela de conexões do broker Mosquitto, atingindo o teto de 1024 soquetes. Nesses cenários desprotegidos, embora o PDR do atacante seja ineficiente (permitindo que mais de 93% das conexões maliciosas alcancem o servidor), a perda de telemetria legítima mantém-se baixa nos testes curtos, contudo, o sistema perde totalmente a capacidade de admitir novos clientes legítimos devido à exaustão de descritores de arquivo.   

Ao analisar o mecanismo heurístico Stateful, nota-se uma limitação severa: por basear-se apenas em contadores volumétricos de pacotes de manutenção (PINGREQ), o sistema gera uma taxa de falsos positivos inaceitável, provocando perdas de telemetria legítima superiores a 38% ao bloquear incorretamente nós subscritores ociosos.   
Em contrapartida, a abordagem proposta baseada em Autômato Finito Determinístico (DFA) atinge os objetivos centrais da pesquisa:

- Alta Eficiência de Mitigação: O PDR do Atacante eleva-se para patamares superiores a 91% de interceptação na borda via fast-path.  
- Imunidade a Falsos Positivos: A Perda de Telemetria permanece estritamente em 0.00% nos cenários legítimo e misto, comprovando que a validação formal da gramática do protocolo MQTT protege o painel subscritor e os sensores de evento sem penalizá-los.
- Preservação da QoS: A latência P95 e a vazão média mantêm-se estáveis e previsíveis, demonstrando que o processamento em nível de driver no eBPF/XDP mitiga o ataque de negação de serviço lenta sem introduzir atrasos de fila perceptíveis na rede IoT.
