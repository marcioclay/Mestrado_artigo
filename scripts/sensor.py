import argparse
import random
import sys
import time
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883


def on_connect(client, userdata, flags, rc):
  if rc == 0:
    print(f"[{userdata['id']}] Conectado ao Broker MQTT com sucesso!")
    if userdata["perfil"] == "sub":
      client.subscribe("iot/#")
      print(f"[{userdata['id']}] Inscreveu-se no tópico 'iot/#'")
  else:
    print(f"[{userdata['id']}] Falha na conexão. Código: {rc}")


def on_message(client, userdata, msg):
  print(
      f"[{userdata['id']}] [MENSAGEM RECEBIDA] {msg.topic}:"
      f" {msg.payload.decode()}"
  )


def executar_sensor_evento(client, teste_disponibilidade=False):
  topic = "iot/sensores/evento"
  client.publish(topic, "STATUS: OK (Inicializado)")
  print("[sensor_evento] Mensagem inicial enviada.")

  if teste_disponibilidade:
    print(
        "[sensor_evento] Modo Teste de Disponibilidade ATIVO (envio periódico"
        " a cada 3s)..."
    )
    contador = 1
    while True:
      payload = f"DISPONIBILIDADE_PING_#{contador}"
      res = client.publish(topic, payload, qos=1)
      if res.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"[sensor_evento] [#{contador}] Teste de disponibilidade enviado:"
            f" {payload}"
        )
      else:
        print(
            f"[sensor_evento] [#{contador}] ❌ FALHA ao enviar (Broker"
            " indisponível / DoS)."
        )
      contador += 1
      time.sleep(3)
  else:
    print("[sensor_evento] Entrando em modo standby...")
    ciclos = 0
    while True:
      time.sleep(30)
      ciclos += 1
      if ciclos % 2 == 0:
        print(
            "[sensor_evento] ⚠️ EVENTO DETECTADO! Disparando rajada de"
            " alertas..."
        )
        for i in range(1, 6):
          payload = f"ALERTA_EMERGENCIA_INCENDIO_#{i}"
          client.publish(topic, payload)
          print(f"  -> Publicado: {payload}")
          time.sleep(0.2)
      else:
        print("[sensor_evento] Mantendo sessão em silêncio (Keep-Alive)...")


def executar_sensor_jitter(client):
  topic = "iot/sensores/clima"
  contador = 1
  while True:
    temp = round(random.uniform(22.0, 35.0), 2)
    umid = round(random.uniform(45.0, 85.0), 2)
    payload = f"temp={temp}C,umid={umid}%,seq={contador}"
    client.publish(topic, payload)
    print(f"[sensor_jitter] [#{contador}] Publicado: {payload}")
    contador += 1
    atraso = random.randint(3, 18)
    print(f"  -> Jitter de rede: aguardando {atraso}s...")
    time.sleep(atraso)


def main():
  parser = argparse.ArgumentParser(description="Cliente IoT MQTT Unificado")
  parser.add_argument(
      "--perfil",
      choices=["evento", "sub", "jitter"],
      required=True,
      help="Perfil de tráfego do sensor",
  )
  parser.add_argument(
      "--teste-disponibilidade",
      action="store_true",
      help="Ativa o modo de teste contínuo de disponibilidade de entrega",
  )
  args = parser.parse_args()

  client_id = f"sensor_{args.perfil}_01"
  user_data = {"id": client_id, "perfil": args.perfil}

  # Compatibilidade transparente para Paho-MQTT v1.x e v2.x (Evita DeprecationWarning)
  try:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1,
        client_id=client_id,
        clean_session=True,
        userdata=user_data,
    )
  except AttributeError:
    client = mqtt.Client(
        client_id=client_id, clean_session=True, userdata=user_data
    )

  client.on_connect = on_connect
  client.on_message = on_message

  try:
    if args.perfil == "sub":
      client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
      client.loop_forever()
    elif args.perfil == "evento":
      client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
      client.loop_start()
      executar_sensor_evento(
          client, teste_disponibilidade=args.teste_disponibilidade
      )
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
