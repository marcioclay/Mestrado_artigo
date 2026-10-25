#!/usr/bin/env python3
import time
import csv
import argparse
import os
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
CSV_FILE = "/scripts/s_check_metrics.csv"
CLIENT_ID = "monitor_scheck"

conectado = False
latencia_inicio = 0
latencia_ms = 0

def on_connect(client, userdata, flags, rc):
    global conectado, latencia_ms, latencia_inicio
    if rc == 0:
        conectado = True
        latencia_ms = (time.time() - latencia_inicio) * 1000
    else:
        conectado = False

def init_csv():
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["ciclo", "timestamp", "status", "latencia_ms"])

def log_csv(ciclo, status, latencia):
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([ciclo, time.strftime('%Y-%m-%d %H:%M:%S'), status, f"{latencia:.2f}"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duracao", type=int, default=60, help="Tempo total em segundos")
    args = parser.parse_args()

    init_csv()
    tempo_inicio = time.time()
    ciclo = 1

    while (time.time() - tempo_inicio) < args.duracao:
        global conectado, latencia_inicio, latencia_ms
        conectado = False
        latencia_ms = 0.0
        latencia_inicio = time.time()

        try:
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=f"{CLIENT_ID}_{ciclo}", clean_session=True)
            except AttributeError:
                client = mqtt.Client(client_id=f"{CLIENT_ID}_{ciclo}", clean_session=True)

            client.on_connect = on_connect
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=10)
            client.loop_start()
            
            espera = 0
            while not conectado and espera < 2.0:
                time.sleep(0.1)
                espera += 0.1
            
            client.loop_stop()
            client.disconnect()
        except Exception:
            conectado = False

        if conectado:
            status = "OK"
        else:
            status = "FALHA"
            latencia_ms = 0.0

        log_csv(ciclo, status, latencia_ms)
        ciclo += 1
        time.sleep(1)

if __name__ == "__main__":
    main()
