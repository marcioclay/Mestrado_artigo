import time
import random
import sys
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
TOPIC = "iot/sensores/clima"
CLIENT_ID = "estacao_meteorologica_01"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{CLIENT_ID}] Conectado ao Broker MQTT com sucesso!")
    else:
        print(f"[{CLIENT_ID}] Falha na conexão. Código: {rc}")

client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
client.on_connect = on_connect

try:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    client.loop_start()

    contador = 1
    while True:
        # Gera telemetria
        temp = round(random.uniform(22.0, 35.0), 2)
        umid = round(random.uniform(45.0, 85.0), 2)
        payload = f"temp={temp}C,umid={umid}%,seq={contador}"
        
        client.publish(TOPIC, payload)
        print(f"[{CLIENT_ID}] [# {contador}] Publicado: {payload}")
        contador += 1
        
        # Simula variação/jitter do enlace sem fio (atraso entre 3s e 18s)
        atraso = random.randint(3, 18)
        print(f"  -> Aguardando próximo ciclo (Jitter de rede: {atraso}s)...")
        time.sleep(atraso)

except KeyboardInterrupt:
    print(f"\n[{CLIENT_ID}] Encerrando estação meteorológica...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"[{CLIENT_ID}] Erro: {e}")
    sys.exit(1)
