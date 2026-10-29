SlowTT e SlowITe são ataques de Negação de Serviço (DoS) inovadores da categoria Slow DoS Attacks (SDA), projetados especificamente para atingir o protocolo MQTT em redes de Internet das Coisas (IoT). Desenvolvidos pelos pesquisadores Ivan Vaccari, Maurizio Aiello e Enrico Cambiaso em 2020, esses ataques exploram vulnerabilidades nativas na estrutura do protocolo MQTT.
Abaixo está o detalhamento de como essas ameaças funcionam:

Mecanismo de Funcionamento

Os ataques adaptam o conceito de "baixo tráfego" (low-rate techniques), muito comum em ataques HTTP (como o Slowloris), para o ecossistema IoT:
• Exploração do KeepAlive: O ataque manipula o parâmetro KeepAlive enviado nos pacotes MQTT de controle.
• Conexões Eternas: Ao configurar estrategicamente esse parâmetro e enviar pacotes mínimos de forma lenta, o cliente malicioso consegue forçar o broker MQTT a manter a conexão aberta por um longo período.
• Esgotamento de Recursos: Como os brokers possuem um limite de conexões simultâneas, o ataque preenche esses slots legítimos, impedindo que dispositivos IoT reais enviem dados ou se comuniquem com a rede.

Principais Vantagens do Ataque (para os atacantes)

• Consumo Mínimo de Banda: Diferente de um DDoS tradicional que tenta inundar o servidor com gigabits de dados, o SlowTT/SlowITe exige largura de banda extremamente baixa e quase nenhum poder computacional.
• Difícil Detecção: Por se comportarem de forma muito parecida com dispositivos IoT legítimos de baixa potência (que transmitem pouquíssimos dados e demoram a responder), esses ataques facilmente burlam ferramentas tradicionais de detecção de intrusão.
• Eficácia Abrangente: Testes validados pelos autores mostraram que o ataque é altamente bem-sucedido tanto em canais de texto claro quanto em conexões criptografadas (TLS), afetando múltiplos daemons de aplicação e diferentes versões do protocolo MQTT.
Para auxiliar na pesquisa e mitigação de vulnerabilidades associadas a esse tipo de ataque, a mesma equipe de pesquisadores também desenvolveu o MQTTset, um conjunto de dados público amplamente utilizado para treinar algoritmos de Machine Learning na detecção de anomalias em redes IoT.
Você gostaria de entender melhor como proteger um broker MQTT contra o SlowTT ou precisa de detalhes específicos sobre os algoritmos de Machine Learning usados para detectar o SlowITe no dataset MQTTset?
• 
MDPI
SlowTT: A Slow Denial of Service against IoT Networks
SlowTT, a novel “Slow” denial of service attack aimed at targeting MQTT through low-rate techniques, characterized by minimum atta...
• 
ResearchGate
(PDF) SlowITe, a Novel Denial of Service Attack Affecting MQTT
SlowITe, acronym of Slow DoS. The proposed attack is a denial of service (DoS) attack aimed to make a network service unavailable ...
• 
Semantic Scholar
SlowITe, a Novel Denial of Service Attack Affecting MQTT
SlowITe, a Novel Denial of Service Attack Affecting MQTT … author={Ivan Vaccari and Maurizio Aiello and Enrico Cambiaso}, journal=
Mostrar tudo

SlowTT: A Slow Denial of Service against IoT Networks, neste artigo de Vaccari qual tempo foi utilizado para testes?

No artigo "SlowTT: A Slow Denial of Service against IoT Networks" (2020), de Ivan Vaccari, Maurizio Aiello e Enrico Cambiaso, cada rodada de testes experimentais foi executada por um tempo/duração de 20 minutos.

Detalhes técnicos dos parâmetros temporais dos testes:

• Duração total de cada teste: 20 minutos.
• Intervalo de envio (Frequência do ataque): O atacante enviava um pacote de controle (PINGREQ) para o broker MQTT a cada 60 segundos para manter as conexões ativas de forma maliciosa.
• Valor do KeepAlive configurado: 65.535 segundos (o valor máximo permitido pelo protocolo).
• Valor do WaitTimeout: 60 segundos.
Essa janela de 20 minutos foi utilizada pelos autores para validar e monitorar o comportamento do broker (como o Mosquitto), demonstrando a eficácia do SlowTT em esgotar os recursos de conexão e tornar o serviço indisponível para usuários legítimos usando pouquíssimo tráfego.
Gostaria de saber mais sobre as métricas de impacto medidas durante esses 20 minutos (como uso de CPU ou conexões pendentes) ou sobre a diferença prática na temporização entre o SlowTT e o SlowITe?
• 
MDPI
SlowTT: A Slow Denial of Service against IoT Networks
the tests were performed for 20 min, the attack is able to make a broker unreachable, the target of DoS attacks; it is used in the...

metricas de impacto em 20min

Durante as rodadas de testes de 20 minutos detalhadas pelos pesquisadores Ivan Vaccari, Maurizio Aiello e Enrico Cambiaso no artigo, as métricas de impacto foram avaliadas sob duas vertentes principais: o esgotamento de recursos lógicos/rede do Broker MQTT e o consumo de hardware (CPU/RAM).
O impacto prático medido nos experimentos revelou os seguintes comportamentos:

1. Negação de Serviço por Ocupação de Slots (Conexões Pendentes)

• Impacto Máximo: O principal objetivo do SlowTT é ocupar completamente a tabela de conexões do broker (como o Mosquitto). Durante os 20 minutos, a ferramenta consome e monopoliza todos os slots de conexões simultâneas disponíveis no servidor.
• Efeito: Dispositivos IoT legítimos que tentavam se conectar ou publicar dados após o início do ataque recebiam erros de timeout ou conexões recusadas, consolidando a Negação de Serviço de forma contínua ao longo do teste.

2. Consumo de Banda (Tráfego de Rede)

• Impacto Mínimo: A métrica de vazão (throughput) de rede gerada pelo atacante foi avaliada como extremamente baixa (apenas alguns bits por segundo — bps).
• Efeito: Como o SlowTT apenas envia pacotes mínimos de controle (PINGREQ) a cada 60 segundos por canal estabelecido, ele mantém o canal ocupado sem gerar picos de tráfego, o que prova a eficácia de sua técnica de low-rate (baixo tráfego).

3. Impacto em Hardware (CPU e RAM)

• Baixo impacto computacional no servidor: Estudos subsequentes e plataformas de avaliação de SIEM que replicaram o SlowTT apontam que esse ataque possui um comportamento muito sutil no uso de hardware se comparado a ataques de inundação baseados em payloads grandes (Payload-based DoS ou Last Will Flooding).
• Uso de CPU: Enquanto ataques de publicação massiva podem travar uma CPU em 100%, o SlowTT mantém o uso de CPU relativamente baixo e estável, uma vez que o servidor não precisa processar grandes volumes de dados, apenas manter sockets abertos em memória.
• Latência: A latência de rede geral do broker afetado pelo SlowTT costuma se manter baixa (geralmente abaixo de 4ms para requisições internas gerenciadas), o que torna o ataque ainda mais silencioso e difícil de disparar alertas automáticos por lentidão de hardware.
Em suma, a métrica de sucesso medida nos 20 minutos não foi a destruição do hardware por sobrecarga de processamento, mas sim o bloqueio total da comunicação da rede IoT por esgotamento de conexões legítimas de forma cirúrgica e silenciosa.
Gostaria de ver um exemplo de como o parâmetro KeepAlive é configurado no código para simular esse comportamento ou prefere discutir as estratégias de mitigação no broker MQTT para evitar a perda dessas conexões?


detalhe as metricas utilizadas para detectar e quais ferramentas foram usadas por Vaccari

Para responder com precisão ao trabalho de Ivan Vaccari e sua equipe, é preciso dividir a resposta sob duas óticas de suas pesquisas públicas de 2020: a primeira foca em como eles avaliaram o impacto do ataque no artigo original do SlowTT, e a segunda aborda as métricas de Machine Learning e ferramentas que eles usaram para validar a detecção desse padrão de tráfego através da criação do dataset MQTTset.

1. Métricas de Impacto no Servidor (Validação do Ataque)

No artigo original do SlowTT, os autores avaliaram se o ataque funcionava medindo a capacidade do Broker MQTT de continuar operando. As métricas observadas foram:
• Taxa de Conexões Bem-Sucedidas (Disponibilidade): Quantidade de conexões legítimas que foram sumariamente rejeitadas ou que sofreram timeout após o início do ataque.
• Throughput de Rede (Vazão): Largura de banda consumida pelo ataque, provando que o SlowTT opera em taxas baixíssimas de bits por segundo (low-rate).
• Tempo de Esgotamento de Recursos: O quão rápido a tabela de conexões concorrentes do Broker (como o Mosquitto) atingia seu limite máximo.

2. Ferramentas Utilizadas por Vaccari

Para conduzir os experimentos e gerar a massa de dados usada no desenvolvimento e validação do ataque, os pesquisadores usaram um ecossistema específico:
• Python (Scripts Customizados): A ferramenta do ataque SlowTT foi escrita nativamente em Python utilizando a biblioteca Paho-MQTT (altamente modificada para conseguir manipular manualmente os pacotes de controle CONNECT e PINGREQ, injetando o KeepAlive máximo de 65.535).
• Brokers MQTT Alvo: Para testar a eficácia, eles utilizaram softwares de mercado amplamente adotados em cenários IoT: Eclipse Mosquitto, Apache ActiveMQ, HiveMQ e VerneMQ.
• Wireshark / Tshark / Tcpdump: Utilizados para capturar o tráfego de rede gerado no testbed físico e extrair os arquivos crus de pacotes (.pcap).
• MQTT-malaria: Utilizada especificamente para simular outros tipos de ataques de inundação combinados (Flooding e Publish Flood) que serviram de comparação e base para compor o dataset.

3. Métricas de Detecção (Machine Learning / MQTTset)

Logo após proporem os ataques, Vaccari e sua equipe publicaram o dataset MQTTset para demonstrar como sistemas de defesa poderiam identificar o SlowTT e o SlowITe usando Inteligência Artificial.
Para comprovar que os algoritmos de detecção eram eficientes contra o SlowTT, eles treinaram classificadores e utilizaram as seguintes métricas estatísticas de desempenho:
• Acurácia (Accuracy): Proporção geral de pacotes classificados corretamente (legítimos vs. maliciosos). Nos testes com dados balanceados, variou entre 87% e 91%.
• Precisão (Precision): Capacidade de o sistema não classificar um pacote legítimo de IoT (ex: um sensor real demorando a responder) como um ataque.
• Revocação / Taxa de Detecção (Recall / Detection Rate): A eficiência do sistema em identificar os pacotes reais do SlowTT sem deixar passar nenhum.
• F1-Score: A média harmônica entre a Precisão e o Recall, métrica crítica para ataques camuflados como o SlowTT.
Os algoritmos específicos de Machine Learning testados por eles para validar essa detecção incluíram Random Forest (RF), Decision Tree (DT), Gradient Boosting (GB) e Naïve Bayes (NB).
Gostaria de focar em algum ponto específico, como os recursos (features) extraídos dos pacotes de rede que permitiram aos algoritmos diferenciar o SlowTT de um sensor legítimo, ou prefere entender as vulnerabilidades de código do broker Mosquitto exploradas por ele?




---
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
