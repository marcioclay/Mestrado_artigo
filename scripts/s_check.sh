#!/usr/bin/env python3
import time
import sys
import csv
import os
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
TOPIC = "iot/monitor/s_check"
CLIENT_ID_PREFIX = "S_check"
TIMEOUT = 3.0    # Tempo máximo de espera (segundos)
INTERVALO = 2.0  # Frequência de checagem (segundos)
LOG_FILE = "/scripts/s_check_metrics.csv"  # Salvo no diretório compartilhado /scripts/

def init_csv():
    # Inicializa/reinicia o arquivo CSV no início da execução
    with open(LOG_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "ciclo", "status", "latencia_ms", "erro"])

def run_s_check():
    init_csv()
    print(f"[*] Iniciando S_check - Monitoramento Contínuo")
    print(f"[*] Métrica registradas em: {LOG_FILE}\n")
    
    ciclo = 1
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        client_id = f"{CLIENT_ID_PREFIX}_{ciclo}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        
        inicio = time.time()
        status = "FALHA"
        latencia = 0.0
        erro_msg = ""
        
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=5)
            client.loop_start()
            
            res = client.publish(TOPIC, f"PING_{ciclo}", qos=1)
            res.wait_for_publish(timeout=TIMEOUT)
            
            if res.is_published():
                latencia = (time.time() - inicio) * 1000
                status = "OK"
                print(f"[✓] {timestamp} | Ciclo {ciclo:04d} | DISPONÍVEL | Latência: {latencia:.2f} ms")
            else:
                erro_msg = "TIMEOUT_QOS1"
                print(f"[!] {timestamp} | Ciclo {ciclo:04d} | LENTIDÃO: Timeout de {TIMEOUT}s")
                
            client.loop_stop()
            client.disconnect()
            
        except Exception as e:
            status = "FALHA"
            erro_msg = str(e).replace(',', ';')
            print(f"[X] {timestamp} | Ciclo {ciclo:04d} | INDISPONÍVEL: {e}")
            
        # Registra o resultado do ciclo no arquivo CSV
        with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, ciclo, status, f"{latencia:.2f}", erro_msg])
            
        ciclo += 1
        tempo_gasto = time.time() - inicio
        if tempo_gasto < INTERVALO:
            time.sleep(INTERVALO - tempo_gasto)

if __name__ == "__main__":
    try:
        run_s_check()
    except KeyboardInterrupt:
        print("\n[*] Script S_check finalizado.")
        sys.exit(0)
