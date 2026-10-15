import time
import sys
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
TOPIC = "iot/#"
CLIENT_ID = "dashboard_atuador_01"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{CLIENT_ID}] Conectado ao Broker! Inscrevendo no tópico '{TOPIC}'...")
        client.subscribe(TOPIC)
    else:
        print(f"[{CLIENT_ID}] Falha na conexão. Código: {rc}")

def on_message(client, userdata, msg):
    print(f"[{CLIENT_ID}] [MENSAGEM RECEBIDA] Tópico: '{msg.topic}' | Payload: '{msg.payload.decode()}'")

client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"[{CLIENT_ID}] Conectando ao Broker {BROKER_HOST}:{BROKER_PORT}...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    
    # Mantém a execução escutando mensagens ativamente
    client.loop_forever()

except KeyboardInterrupt:
    print(f"\n[{CLIENT_ID}] Encerrando dashboard...")
    client.disconnect()
except Exception as e:
    print(f"[{CLIENT_ID}] Erro: {e}")
    sys.exit(1)
