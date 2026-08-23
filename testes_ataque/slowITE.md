# Guia de Testes e Validação do Ataque SlowITe no MQTT

Este documento descreve o procedimento passo a passo para reproduzir o ataque **SlowITe** (Slow DoS against Internet of Things Environments) em uma topologia virtualizada via Containerlab, simulando o impacto de exaustão de conexões em um Broker MQTT intermediado por um Gateway IoT.

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

Terminal 3: Disparo do Ataque SlowITe
No terceiro terminal, inicie o script de exaustão de conexões com Keep-Alive estendido (65535s):

```
docker exec -it clab-seg-atacante python3 /scripts/slowite_attack.py
```

## 4. Validação e Prova do DoS (Denial of Service)

A. Quantificação de Conexões Presas
Abra uma nova janela no terminal do host e execute o comando abaixo para contar as conexões TCP ativas na porta 1883 do Broker:

```
docker exec -it clab-seg-mqtt ss -tna | grep :1883 | grep -i ESTAB | wc -l
```

Resultado Esperado: Aproximadamente 1025 conexões (1022 do ataque + conexões legítimas ativas).


B. Teste de Bloqueio de Novos Dispositivos
Com o ataque ativo no Terminal 3, vá até o Terminal 2 (Sensor) e interrompa o script pressionando Ctrl + C.

Tente reconectar o Sensor executando o script novamente:

```
docker exec -it clab-seg-sensor python3 /scripts/sensor.py
```

Resultado Observado: O Sensor não conseguirá abrir uma nova sessão TCP com o Broker, retornando erro de timed out ou recusa de conexão.


## 5. Análise Técnica dos Resultados

Persistência de Conexões Antigas: Se o Sensor foi iniciado antes do ataque, suas mensagens continuarão chegando ao Broker porque a sua sessão TCP já estava estabelecida.

Bloqueio de Novas Sessões: O ataque SlowITe preenche 100% da tabela de conexões (sockets) do Mosquitto. Qualquer novo dispositivo que tentar se conectar durante o ataque será impedido, concretizando o estado de Negação de Serviço na camada de aplicação.


