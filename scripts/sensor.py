import paho.mqtt.client as mqtt
import time
import random
import sys

BROKER_IP = "10.0.3.10"
BROKER_PORT = 1883
KEEP_ALIVE = 60

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[✓] Sensor conectado com sucesso ao Broker ({BROKER_IP}:{BROKER_PORT})")
    else:
        print(f"[X] Falha na conexão. Código de erro: {rc}")

def on_disconnect(client, userdata, rc):
    print(f"[!] Desconectado do Broker (Código: {rc}). Tentando reconectar...")

# Inicializa o cliente MQTT
client = mqtt.Client(client_id="sensor_iot_01")
client.on_connect = on_connect
client.on_disconnect = on_disconnect

print(f"[*] Estabelecendo conexão com o Broker via Gateway...")

try:
    client.connect(BROKER_IP, BROKER_PORT, keepalive=KEEP_ALIVE)
    client.loop_start()

    while True:
        # Simula leitura de telemetria
        temperatura = round(random.uniform(21.0, 28.5), 2)
        payload = f'{{"sensor_id": "temp_01", "valor": {temperatura}}}'
        
        info = client.publish("iot/telemetria", payload, qos=1)
        
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[+] Dado enviado: {payload}")
        else:
            print(f"[-] Erro ao enviar pacote. Broker pode estar inacessível (DoS).")
            
        time.sleep(3)

except KeyboardInterrupt:
    print("\n[*] Parando o sensor...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"[-] Erro de rede: {e}")
