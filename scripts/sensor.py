#!/usr/bin/env python3
import time
import random
import sys
import argparse
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{userdata['id']}] Conectado ao Broker MQTT com sucesso!")
        if userdata['perfil'] == 'sub':
            client.subscribe("iot/#")
            print(f"[{userdata['id']}] Inscreveu-se no tópico 'iot/#'")
    else:
        print(f"[{userdata['id']}] Falha na conexão. Código: {rc}")

def on_message(client, userdata, msg):
    print(f"[{userdata['id']}] [MENSAGEM RECEBIDA] {msg.topic}: {msg.payload.decode()}")

def executar_sensor_evento(client):
    topic = "iot/sensores/evento"
    
    # Contadores para métricas solicitadas pelo orientador
    total_enviadas = 0
    
    client.publish(topic, "STATUS: OK (Inicializado)")
    print("[sensor_evento] Mensagem inicial enviada. Entrando em modo standby...")
    
    ciclos = 0
    try:
        while True:
            time.sleep(30)
            ciclos += 1
            if ciclos % 2 == 0:
                print("[sensor_evento] ⚠️ EVENTO DETECTADO! Disparando rajada de alertas...")
                for i in range(1, 6):
                    payload = f"ALERTA_EMERGENCIA_INCENDIO_#{i}"
                    info = client.publish(topic, payload)
                    total_enviadas += 1
                    print(f"  -> Publicado [Total Enviadas: {total_enviadas}]: {payload}")
                    time.sleep(0.2)
            else:
                print("[sensor_evento] Mantendo sessão em silêncio (Keep-Alive)...")
    except KeyboardInterrupt:
        print(f"\n[Estatísticas Finais - sensor_evento]")
        print(f"Total de Mensagens Enviadas: {total_enviadas}")

def executar_sensor_jitter(client):
    topic = "iot/sensores/clima"
    contador = 1
    total_enviadas = 0
    
    try:
        while True:
            temp = round(random.uniform(22.0, 35.0), 2)
            umid = round(random.uniform(45.0, 85.0), 2)
            payload = f"temp={temp}C,umid={umid}%,seq={contador}"
            
            client.publish(topic, payload)
            total_enviadas += 1
            print(f"[sensor_jitter] [#{contador}] Publicado [Total Enviadas: {total_enviadas}]: {payload}")
            contador += 1
            
            atraso = random.randint(3, 18)
            print(f"  -> Jitter de rede: aguardando {atraso}s...")
            time.sleep(atraso)
    except KeyboardInterrupt:
        print(f"\n[Estatísticas Finais - sensor_jitter]")
        print(f"Total de Mensagens Enviadas: {total_enviadas}")

def main():
    parser = argparse.ArgumentParser(description="Cliente IoT MQTT Unificado com Métricas")
    parser.add_argument("--perfil", choices=["evento", "sub", "jitter"], required=True, help="Perfil de tráfego do sensor")
    args = parser.parse_args()

    client_id = f"sensor_{args.perfil}_01"
    client = mqtt.Client(client_id=client_id, clean_session=True, userdata={'id': client_id, 'perfil': args.perfil})
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        if args.perfil == "sub":
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            client.loop_forever()
        elif args.perfil == "evento":
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            client.loop_start()
            executar_sensor_evento(client)
        elif args.perfil == "jitter":
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
            client.loop_start()
            executar_sensor_jitter(client)

    except KeyboardInterrupt:
        print(f"\n[{client_id}] Encerrando conexao...")
        client.disconnect()
    except Exception as e:
        print(f"[{client_id}] Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
