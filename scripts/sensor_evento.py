import time
import sys
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
TOPIC = "iot/sensores/evento"
CLIENT_ID = "sensor_fumaca_01"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{CLIENT_ID}] Conectado ao Broker MQTT com sucesso!")
    else:
        print(f"[{CLIENT_ID}] Falha na conexão. Código: {rc}")

client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
client.on_connect = on_connect

try:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    # Envia mensagem inicial
    client.publish(TOPIC, "STATUS: OK (Inicializado)")
    print(f"[{CLIENT_ID}] Enviado estado inicial. Entrando em modo de espera/silêncio...")

    ciclos = 0
    while True:
        # Simula período em silêncio prolongado (apenas PINGREQ de Keep-Alive)
        time.sleep(30)
        ciclos += 1
        
        # A cada 2 ciclos (60s), simula a detecção de um evento de emergência (Rajada)
        if ciclos % 2 == 0:
            print(f"[{CLIENT_ID}] ⚠️ EVENTO DETECTADO! Disparando rajada de alertas...")
            for i in range(1, 6):
                payload = f"ALERTA_EMERGENCIA_INCENDIO_#{i}"
                client.publish(TOPIC, payload)
                print(f"  -> Publicado: {payload}")
                time.sleep(0.2)
        else:
            print(f"[{CLIENT_ID}] Mantendo sessão em silêncio (Standby)...")

except KeyboardInterrupt:
    print(f"\n[{CLIENT_ID}] Encerrando sensor...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"[{CLIENT_ID}] Erro: {e}")
    sys.exit(1)
