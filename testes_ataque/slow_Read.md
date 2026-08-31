

# Teste 2: Ataque Slow Read (Esgotamento de Memória por TCP Zero Window)

Conceito
O Slow Read estabelece conexões e se inscreve em tópicos de telemetria via pacote SUBSCRIBE. 
O atacante reduz propositalmente o buffer de recepção do socket (SO_RCVBUF) para o tamanho mínimo e interrompe as chamadas de leitura (recv()).
Isso obriga o protocolo TCP a enviar avisos de Zero Window, forçando o Broker a reter todas as mensagens pendentes na memória RAM.

Execução

Inicie o Sensor Legítimo para gerar tráfego contínuo no tópico iot/#:

```
docker exec -it clab-seg-sensor python3 /scripts/sensor.py
```

Dispare o Ataque Slow Read a partir do Atacante:

```
docker exec -it clab-seg-atacante python3 /scripts/slow_read_attack.py
```

Validação e Evidência no Gateway
Para capturar as evidências da Janela TCP Zerada transitando através do Gateway, execute o tcpdump na interface de monitoramento:

```
docker exec -it clab-seg-gateway tcpdump -i eth1 -n "tcp src port 1883 or tcp dst port 1883" | grep -i "win 0"
```

Saída Esperada (Evidência experimental de Janela Zerada):

```
19:09:22.618644 IP 10.0.1.20.55272 > 10.0.2.10.1883: Flags [.], ack 1088, win 0, options [nop,nop,TS val 1562185898 ecr 3273772049], length 0
19:09:22.618649 IP 10.0.1.20.55278 > 10.0.2.10.1883: Flags [.], ack 1088, win 0, options [nop,nop,TS val 1562185898 ecr 3273772049], length 0
19:09:22.618655 IP 10.0.1.20.55286 > 10.0.2.10.1883: Flags [.], ack 1088, win 0, options [nop,nop,TS val 1562185898 ecr 3273772049], length 0
```

## Matriz de Detecção e Mitigação via eBPF/XDP no Gateway

A tabela abaixo sumariza como o filtro eBPF/XDP implantado no **Gateway** atuará na identificação e mitigação prévia dos dois vetores de ataque antes que atinjam o **Broker MQTT**.

| **Ataque** | **Camada Alvo** | **Indicador Crítico (Telemetry)** | **Estratégia de Mitigação eBPF/XDP** |
|---|---|---|---|
| **SlowITe** | L7 (MQTT) | Alta taxa de `CONNECT` com *Keep-Alive* elevado sem envio de `PUBLISH`. | Mapeamento de estado em `BPF_MAP_TYPE_HASH` e bloqueio do IP (`XDP_DROP`). |
| **Slow Read** | L4 (TCP) | Sinalização recorrente do parâmetro `win 0` no cabeçalho TCP (`tcphdr->window`). | Leitura direta do campo `tcphdr->window == 0` com descarte imediato no XDP. |
