

Família de ataques Slow DoS focados no protocolo MQTT.

- SlowTT (Slow Topic Transfer / Slow Publish): O atacante estabelece a conexão normalmente, mas ao publicar uma mensagem, envia os bytes do cabeçalho, do tópico ou do payload de forma extremamente lenta (ex: 1 byte a cada 10 segundos). Isso prende o buffer e a thread de leitura do Broker aguardando o término do pacote.

- Slow Read Attack (Slow Receiver): O atacante se conecta, assina tópicos de alto volume de dados e reduz propositalmente a janela de recepção TCP (TCP Window Size). O Broker é forçado a reter todas as mensagens pendentes na memória RAM para não perdê-las, levando à exaustão de memória.

- Slow ACK (QoS 1 / QoS 2 Hold): O atacante assina tópicos com garantia de entrega (QoS 1 ou QoS 2) e retém intencionalmente os pacotes de confirmação (PUBACK, PUBREC ou PUBCOMP). Isso força o Broker a armazenar as mensagens em filas de retransmissão em memória (in-flight message buffer).

- Slow CONNECT (Incomplete Header): Inicia a conexão TCP e envia o pacote inicial CONNECT fragmentado em bytes individuais com longos intervalos entre eles. Isso esgota o pool de conexões que ficam aguardando a finalização do handshake.

- Slow Ping (PINGREQ Drift): Envia pacotes de keep-alive (PINGREQ) de forma incompleta ou no limite milimétrico de expiração do temporizador, mantendo a tabela de estados de sessão ocupada sem trafegar telemetria real.
