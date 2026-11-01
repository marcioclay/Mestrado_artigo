#!/usr/bin/env python3
"""
sensor.py (v2)

Corrige, em relação à versão anterior:
  1. Toda mensagem PUBLISH passa a carregar seq=<N> e ts=<epoch> no payload,
     permitindo calcular PDR real por sequência (não mais por contagem bruta
     de pacotes) e latência ponta a ponta.
  2. O perfil "sub" (único que recebe e nunca publica) passa a logar, por
     mensagem recebida, o número de sequência, o timestamp de envio e a
     latência calculada, em /scripts/latencia_mensagens.csv. Esse log é a
     base para a métrica de PDR por sequência e para latência P50/P95/P99
     que a auditoria pediu.
  3. Mantém compatibilidade com mensagens_recebidas.log (gerado por
     mosquitto_sub no container do broker) para contagem agregada.

Formato do payload de dados: "seq=<N>;ts=<epoch_float>;data=<conteudo original>"
"""
import time
import random
import sys
import os
import csv
import argparse
import paho.mqtt.client as mqtt

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
LATENCIA_CSV = "/scripts/latencia_mensagens.csv"


def montar_payload(seq, conteudo):
    return f"seq={seq};ts={time.time():.6f};data={conteudo}"


def parsear_payload(payload_str):
    """Extrai seq (int), ts_envio (float) e data (str) de um payload no formato
    'seq=<N>;ts=<epoch>;data=<conteudo>'. Retorna (None, None, payload_str) se
    o payload não seguir o formato esperado (ex.: mensagens de outra origem)."""
    try:
        partes = dict(p.split("=", 1) for p in payload_str.split(";", 2) if "=" in p)
        seq = int(partes.get("seq")) if "seq" in partes else None
        ts = float(partes.get("ts")) if "ts" in partes else None
        data = partes.get("data", payload_str)
        return seq, ts, data
    except Exception:
        return None, None, payload_str


def init_latencia_csv():
    """Sempre trunca e recria o CSV no início da execução (mesmo padrão de
    s_check.py::init_csv). Cada chamada de rodar_experimento.sh via
    run_all.sh dispara um novo processo sensor.py --perfil sub, então
    truncar aqui garante que o arquivo reflete SOMENTE a execução atual
    (defesa/cenário em curso), nunca dados acumulados de execuções
    anteriores da bateria completa."""
    os.makedirs(os.path.dirname(LATENCIA_CSV), exist_ok=True)
    with open(LATENCIA_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_recebimento", "topico", "seq", "ts_envio", "latencia_ms"])


def log_latencia(topico, seq, ts_envio, latencia_ms):
    with open(LATENCIA_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([f"{time.time():.6f}", topico, seq, ts_envio, f"{latencia_ms:.3f}"])


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{userdata['id']}] Conectado ao Broker MQTT com sucesso!")
        if userdata['perfil'] == 'sub':
            client.subscribe("iot/#")
            print(f"[{userdata['id']}] Inscreveu-se no tópico 'iot/#'")
    else:
        print(f"[{userdata['id']}] Falha na conexão. Código: {rc}")


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode(errors="replace")
    print(f"[{userdata['id']}] [MENSAGEM RECEBIDA] {msg.topic}: {payload_str}")

    if userdata['perfil'] != 'sub':
        return

    seq, ts_envio, _dado = parsear_payload(payload_str)
    if seq is None or ts_envio is None:
        # Mensagem sem o formato seq/ts (ex.: tráfego de outra origem) - não entra na métrica
        return

    ts_recebimento = time.time()
    latencia_ms = (ts_recebimento - ts_envio) * 1000.0
    log_latencia(msg.topic, seq, ts_envio, latencia_ms)


def executar_sensor_evento(client):
    topic = "iot/sensores/evento"

    total_enviadas = 0
    seq = 0

    seq += 1
    client.publish(topic, montar_payload(seq, "STATUS: OK (Inicializado)"))
    print(f"[sensor_evento] Mensagem inicial enviada [seq={seq}]. Entrando em modo standby...")

    ciclos = 0
    try:
        while True:
            time.sleep(30)
            ciclos += 1
            if ciclos % 2 == 0:
                print("[sensor_evento] ⚠️ EVENTO DETECTADO! Disparando rajada de alertas...")
                for i in range(1, 6):
                    seq += 1
                    conteudo = f"ALERTA_EMERGENCIA_INCENDIO_#{i}"
                    payload = montar_payload(seq, conteudo)
                    client.publish(topic, payload)
                    total_enviadas += 1
                    print(f"  -> Publicado [seq={seq}, Total Enviadas: {total_enviadas}]: {conteudo}")
                    time.sleep(0.2)
            else:
                print("[sensor_evento] Mantendo sessão em silêncio (Keep-Alive)...")
    except KeyboardInterrupt:
        print(f"\n[Estatísticas Finais - sensor_evento]")
        print(f"Total de Mensagens Enviadas: {total_enviadas} (última seq={seq})")


def executar_sensor_jitter(client):
    topic = "iot/sensores/clima"
    seq = 0
    total_enviadas = 0

    try:
        while True:
            temp = round(random.uniform(22.0, 35.0), 2)
            umid = round(random.uniform(45.0, 85.0), 2)
            seq += 1
            conteudo = f"temp={temp}C,umid={umid}%"
            payload = montar_payload(seq, conteudo)

            client.publish(topic, payload)
            total_enviadas += 1
            print(f"[sensor_jitter] [seq={seq}] Publicado [Total Enviadas: {total_enviadas}]: {conteudo}")

            atraso = random.randint(3, 18)
            print(f"  -> Jitter de rede: aguardando {atraso}s...")
            time.sleep(atraso)
    except KeyboardInterrupt:
        print(f"\n[Estatísticas Finais - sensor_jitter]")
        print(f"Total de Mensagens Enviadas: {total_enviadas} (última seq={seq})")


def main():
    parser = argparse.ArgumentParser(description="Cliente IoT MQTT Unificado com Métricas (v2 - seq + ts)")
    parser.add_argument("--perfil", choices=["evento", "sub", "jitter"], required=True, help="Perfil de tráfego do sensor")
    args = parser.parse_args()

    if args.perfil == "sub":
        init_latencia_csv()

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