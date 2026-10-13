# Guia de Testes e Validação do Ataque SlowTTe no MQTT

Este documento descreve o procedimento passo a passo para reproduzir o ataque SlowTT (Slow Denial of Service against MQTT) em uma topologia virtualizada via Containerlab. O objetivo é simular o impacto do esgotamento de conexões (Socket Exhaustion) em um Broker MQTT intermediado por um Gateway de Borda IoT.

---

## 1. Mapeamento da Rede

| Nó | Container Docker | IP na Rede | Função |
| :--- | :--- | :--- | :--- |
| **Gateway** | `clab-seg-gateway` | `10.0.1.1` (LAN) / `10.0.2.1` (DMZ) | Roteador / Filtro eBPF |
| **MQTT Broker** | `clab-seg-mqtt` | `10.0.2.10` | Servidor Mosquitto (`max_connections: 1024`) |
| **Sensor** | `clab-seg-sensor` | `10.0.1.10` | Dispositivo IoT Legítimo (Telemetria) |
| **Atacante** | `clab-seg-atacante` | `10.0.1.20` | Botnet / Gerador do ataque SlowITe |

---

## 2. Pré-requisitos

Certifique-se de ter implantado o ambiente via script de automação `setup.sh`:

```
chmod +x setup.sh
./setup.sh
```

Verifique se todos os contêineres estão em execução:

```
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## 3. Procedimento de Execução do Teste (3 Terminais)
Para observar a falha de serviço em tempo real, divida sua execução em três terminais distintos:

Terminal 1: Monitoramento no Broker MQTT
Inicie a escuta contínua de todas as mensagens que chegam ao broker: 

```
docker exec -it clab-seg-mqtt mosquitto_sub -h 10.0.2.10 -t "iot/#" -v
```


> O terminal ficará em estado de espera aguardando publicações.

Terminal 2: Sensor Legítimo
Inicie a publicação contínua de dados de telemetria (temperatura) a cada 3 segundos:

```
docker exec -it clab-seg-sensor python3 /scripts/sensor.py
```

> Observe que no Terminal 1 os dados de telemetria começarão a aparecer imediatamente.

Terminal 3: Disparo do Ataque SlowTT
No terceiro terminal, execute o script do ataque SlowTT. Este script estabelece múltiplas conexões MQTT (CONNECT) com valor de Keep-Alive configurado e envia periodicamente pacotes de manutenção (PINGREQ) em um intervalo ajustado (Wait Timeout) antes que o servidor encerre a sessão:

```
docker exec -it clab-seg-atacante python3 /scripts/slowtt_attack.py
```

## 4. Validação e Prova do DoS (Denial of Service)

A. Quantificação de Conexões Retidas no Broker
Abra uma nova janela de terminal no host e execute o comando abaixo para verificar o número de soquetes TCP em estado ESTABLISHED na porta 1883 do Broker:

```
docker exec -it clab-seg-mqtt ss -tna | grep :1883 | grep -i ESTAB | wc -l
```

Resultado Esperado: Aproximadamente 1025 conexões (1024 conexões mantidas pelo SlowTT + conexões ativas do sensor legítimo/subcritor).


B. Teste de Bloqueio de Novos Dispositivos
Com o ataque SlowTT ativo no Terminal 3:

- Vá até o Terminal 2 (Sensor) e interrompa o script pressionando Ctrl + C.

- Tente reconectar o sensor executando o script novamente:

```
docker exec -it clab-seg-sensor python3 /scripts/sensor.py
```

* Resultado Observado: O sensor legítimo não conseguirá completar o handshake do protocolo com o Broker, retornando erro de Timeout ou Connection Refused devido ao esgotamento das tabelas de soquetes no servidor.


## 5. Análise Técnica dos Resultados

- Diferencial do SlowTT: Diferente de ataques de inundação volumétrica (DDoS L3/L4), o SlowTT mantém conexões presas por tempo indeterminado utilizando uma taxa mínima de pacotes PINGREQ (low-rate).

- Persistência das Sessões Antigas: Se um dispositivo legítimo abriu uma conexão antes do disparo do ataque, ele continuará publicando enquanto a soquete não for encerrada.

- Negação de Serviço para Novas Conexões: O SlowTT preenche 100% dos slots de conexão gerenciáveis pelo processo do Mosquitto (limite padrão de 1024 conexões simultâneas). Qualquer nova tentativa de conexão de um dispositivo legítimo na camada de aplicação será rejeitada.

