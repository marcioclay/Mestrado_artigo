#!/usr/bin/env python3
"""
sensor.py (v3)

Novidade em relação à v2:
  - Cada perfil publicador (evento, jitter) agora loga TODA mensagem que
    ENVIA em seu próprio CSV (envios_evento.csv / envios_jitter.csv),
    com topico, seq e timestamp de envio. Antes, só o assinante (perfil
    sub) logava o que RECEBIA, e o PDR era estimado assumindo que a maior
    seq recebida == total enviado - uma aproximação que fica otimista se
    exatamente a ÚLTIMA mensagem enviada for a perdida.
  - Com o log de envios, o cálculo de PDR em gerar_relatorio.py passa a
    ser exato: PDR = mensagens únicas recebidas / mensagens únicas
    enviadas, sem precisar estimar nada a partir da maior seq observada.
  - Cada perfil grava em seu PRÓPRIO arquivo (nunca um arquivo
    compartilhado entre processos/containers diferentes), evitando
    qualquer risco de escrita concorrente corromper o CSV.

Herdado da v2:
  - Payload com seq=<N>;ts=<epoch>;data=<conteúdo original>.
  - Perfil "sub" loga latência por mensagem recebida em
    latencia_mensagens.csv (timestamp_recebimento, topico, seq, ts_envio,
    latencia_ms).
  - CSVs sempre truncados no início da execução (nunca acumulam dados de
    uma execução anterior).
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
ENVIOS_CSV_POR_PERFIL = {
    "evento": "/scripts/envios_evento.csv",
    "jitter": "/scripts/envios_jitter.csv",
}


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


def init_csv_com_header(caminho, header):
    """Sempre trunca e recria o CSV no início da execução (mesmo padrão em
    todos os CSVs deste pipeline: s_check.py, sensor.py, slowtt_attack.py).
    Cada execução reflete só o ensaio atual, nunca dados acumulados."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def log_latencia(topico, seq, ts_envio, latencia_ms):
    with open(LATENCIA_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([f"{time.time():.6f}", topico, seq, ts_envio, f"{latencia_ms:.3f}"])


def log_envio(perfil, topico, seq, ts_envio):
    caminho = ENVIOS_CSV_POR_PERFIL[perfil]
    with open(caminho, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([topico, seq, f"{ts_envio:.6f}"])


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
    perfil = "evento"

    total_enviadas = 0
    seq = 0

    seq += 1
    ts = time.time()
    client.publish(topic, montar_payload(seq, "STATUS: OK (Inicializado)"))
    log_envio(perfil, topic, seq, ts)
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
                    ts = time.time()
                    payload = montar_payload(seq, conteudo)
                    client.publish(topic, payload)
                    log_envio(perfil, topic, seq, ts)
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
    perfil = "jitter"
    seq = 0
    total_enviadas = 0

    try:
        while True:
            temp = round(random.uniform(22.0, 35.0), 2)
            umid = round(random.uniform(45.0, 85.0), 2)
            seq += 1
            conteudo = f"temp={temp}C,umid={umid}%"
            ts = time.time()
            payload = montar_payload(seq, conteudo)

            client.publish(topic, payload)
            log_envio(perfil, topic, seq, ts)
            total_enviadas += 1
            print(f"[sensor_jitter] [seq={seq}] Publicado [Total Enviadas: {total_enviadas}]: {conteudo}")

            atraso = random.randint(3, 18)
            print(f"  -> Jitter de rede: aguardando {atraso}s...")
            time.sleep(atraso)
    except KeyboardInterrupt:
        print(f"\n[Estatísticas Finais - sensor_jitter]")
        print(f"Total de Mensagens Enviadas: {total_enviadas} (última seq={seq})")


def main():
    parser = argparse.ArgumentParser(description="Cliente IoT MQTT Unificado com Métricas (v3 - PDR real por envio/recebimento)")
    parser.add_argument("--perfil", choices=["evento", "sub", "jitter"], required=True, help="Perfil de tráfego do sensor")
    args = parser.parse_args()

    if args.perfil == "sub":
        init_csv_com_header(LATENCIA_CSV, ["timestamp_recebimento", "topico", "seq", "ts_envio", "latencia_ms"])
    else:
        init_csv_com_header(ENVIOS_CSV_POR_PERFIL[args.perfil], ["topico", "seq", "ts_envio"])

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
