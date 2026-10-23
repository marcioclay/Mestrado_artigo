#!/usr/bin/env python3
import time
import sys
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
TOPIC = "iot/monitor/s_check"
CLIENT_ID_PREFIX = "S_check"
TIMEOUT = 3.0    # Tempo máximo de espera pela conexão/publicação (segundos)
INTERVALO = 2.0  # Frequência de checagem contínua (segundos)

def run_s_check():
    print(f"[*] Iniciando S_check - Monitoramento Contínuo do Broker {BROKER_HOST}:{BROKER_PORT}")
    print(f"[*] Timeout: {TIMEOUT}s | Frequência: {INTERVALO}s. Pressione Ctrl+C para parar.\n")
    
    ciclo = 1
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        # Gera um ID de cliente único a cada ciclo para forçar a criação de um novo soquete TCP
        client_id = f"{CLIENT_ID_PREFIX}_{ciclo}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        
        inicio = time.time()
        
        try:
            # 1. Tenta estabelecer a conexão TCP/MQTT com o Broker
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=5)
            client.loop_start()
            
            # 2. Publica uma mensagem com QoS 1 (exigindo confirmação do Broker)
            res = client.publish(TOPIC, f"PING_{ciclo}", qos=1)
            res.wait_for_publish(timeout=TIMEOUT)
            
            # 3. Avalia o resultado e calcula a latência
            if res.is_published():
                latencia = (time.time() - inicio) * 1000
                print(f"[✓] {timestamp} | Ciclo {ciclo:04d} | Broker DISPONÍVEL | Latência: {latencia:.2f} ms")
            else:
                print(f"[!] {timestamp} | Ciclo {ciclo:04d} | LENTIDÃO: Confirmação estourou o limite de {TIMEOUT}s")
                
            client.loop_stop()
            client.disconnect()
            
        except Exception as e:
            # 4. Falha na conexão (Broker fora do ar, Socket Exausto ou Timeout de Rede)
            print(f"[X] {timestamp} | Ciclo {ciclo:04d} | Broker INDISPONÍVEL: {e}")
            
        # Aguarda o período restante para manter a consistência do intervalo do próximo ciclo
        ciclo += 1
        tempo_gasto = time.time() - inicio
        if tempo_gasto < INTERVALO:
            time.sleep(INTERVALO - tempo_gasto)

if __name__ == "__main__":
    try:
        run_s_check()
    except KeyboardInterrupt:
        print("\n[*] Script S_check finalizado pelo usuário.")
        sys.exit(0)
