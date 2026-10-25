#!/usr/bin/env python3
import time
import csv
import argparse
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
CSV_FILE = "/scripts/s_check_metrics.csv"
CLIENT_ID = "monitor_scheck"
TOPIC = "iot/monitoramento/scheck"

# Variáveis globais para controle
conectado = False
latencia_inicio = 0
latencia_ms = 0
falhas_consecutivas = 0

def on_connect(client, userdata, flags, rc):
    global conectado, latencia_ms, latencia_inicio
    if rc == 0:
        conectado = True
        latencia_ms = (time.time() - latencia_inicio) * 1000
    else:
        conectado = False

def on_disconnect(client, userdata, rc):
    global conectado
    conectado = False

def init_csv():
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["ciclo", "timestamp", "status", "latencia_ms"])

def log_csv(ciclo, status, latencia):
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([ciclo, time.strftime('%Y-%m-%d %H:%M:%S'), status, f"{latencia:.2f}"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duracao", type=int, default=60, help="Tempo total de monitoramento em segundos")
    args = parser.parse_args()

    print(f"[*] Iniciando S_check. Monitorando o broker {BROKER_HOST}:{BROKER_PORT} por {args.duracao}s...")
    init_csv()

    tempo_inicio = time.time()
    ciclo = 1

    while (time.time() - tempo_inicio) < args.duracao:
        global conectado, latencia_inicio, latencia_ms
        conectado = False
        latencia_ms = 0
        latencia_inicio = time.time()

        try:
            client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            
            # Timeout curto para detectar indisponibilidade rápido
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=5)
            client.loop_start()
            
            # Aguarda até 2 segundos pela conexão
            espera = 0
            while not conectado and espera < 2.0:
                time.sleep(0.1)
                espera += 0.1
            
            client.loop_stop()
            client.disconnect()

        except Exception as e:
            conectado = False

        if conectado:
            status = "OK"
            falhas_consecutivas = 0
            print(f"[✓] Ciclo {ciclo:04d} | Broker DISPONÍVEL | Latência: {latencia_ms:.2f} ms")
        else:
            status = "FALHA"
            falhas_consecutivas += 1
            latencia_ms = 0
            print(f"[X] Ciclo {ciclo:04d} | Broker INDISPONÍVEL | Falha de conexão.")

        log_csv(ciclo, status, latencia_ms)
        ciclo += 1
        time.sleep(1) # Testa a cada 1 segundo

    print("[*] S_check finalizado.")

if __name__ == "__main__":
    main()
