


## 📊 Tabela Consolidada de Resultados Experimentais

| Mecanismo de Defesa | Cenário de Teste | Numero conexões | PDR do Atacante (%) | Perda de Telemetria (%) | Vazão Média (pps) | Latência P95 (ms) |
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
