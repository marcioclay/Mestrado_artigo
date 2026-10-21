#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_helpers.h>

// Definições dos Estados do Autômato DFA (q0..q4)
#define STATE_INIT           0
#define STATE_CONNECTED      1
#define STATE_SUBSCRIBED     2
#define STATE_ACTIVE_PUBLISH 3
#define STATE_BLOCKED        4

// Tipos de Pacotes MQTT (Header Control Byte - Nibble Superior)
#define MQTT_MSG_CONNECT    0x10
#define MQTT_MSG_PUBLISH    0x30
#define MQTT_MSG_SUBSCRIBE  0x82
#define MQTT_MSG_PINGREQ    0xC0

// Limite configurável de PINGREQ sem subscrição/publicação para detecção de SlowTT
#define MAX_PING_WITHOUT_DATA 5

// Estrutura de Estado de Sessão
struct session_state {
    __u32 state;                  // Estado do autômato (q0..q4)
    __u64 last_seen;              // Timestamp em nanossegundos
    __u32 ping_count;             // Contagem acumulada de PINGREQs no estado CONNECTED
    __u32 publish_count;          // Contagem de pacotes PUBLISH
    __u32 connect_count;          // Contagem de tentativas de re-conexão
};

// Mapa 1: Tabela de Estado dos Clientes (Stateful Session Tracking)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 8192);
    __type(key, __u32);                 // IP de Origem
    __type(value, struct session_state);
} dfa_session_map SEC(".maps");

// Mapa 2: Tabela de Fast-Path para Descarte Imediato (XDP_DROP)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 8192);
    __type(key, __u32);                 // IP Bloqueado
    __type(value, __u8);
} blocked_ips_map SEC(".maps");

SEC("xdp")
int xdp_mqtt_dfa_filter(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    // 1. Validação Ethernet (L2)
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    // 2. Validação IPv4 (L3)
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end)
        return XDP_PASS;
    if (iph->protocol != IPPROTO_TCP)
        return XDP_PASS;

    __u32 src_ip = iph->saddr;

    // 3. Fast-Path: Verifica se o IP já está bloqueado
    __u8 *blocked = bpf_map_lookup_elem(&blocked_ips_map, &src_ip);
    if (blocked) {
        return XDP_DROP; // Descarte direto no nível da placa de rede
    }

    if (iph->ihl < 5)
        return XDP_PASS;

    // 4. Validação TCP (L4)
    struct tcphdr *tcph = (void *)iph + (iph->ihl * 4);
    if ((void *)(tcph + 1) > data_end)
        return XDP_PASS;

    // Inspeciona apenas tráfego direcionado à porta do Broker MQTT (1883)
    if (tcph->dest != bpf_htons(1883))
        return XDP_PASS;

    // Validação estrita do tamanho do cabeçalho TCP para o eBPF Verifier
    __u32 tcp_hdr_len = tcph->doff * 4;
    if (tcp_hdr_len < sizeof(struct tcphdr) || tcp_hdr_len > 60)
        return XDP_PASS;

    // Cálculo do offset para a Camada 7 (Payload MQTT)
    unsigned char *payload = (unsigned char *)tcph + tcp_hdr_len;
    if ((void *)(payload + 1) > data_end)
        return XDP_PASS; // Pacotes de controle TCP puros (SYN, ACK) passam

    __u8 mqtt_msg_type = payload[0] & 0xF0; // Extrai o tipo de mensagem MQTT

    __u64 now = bpf_ktime_get_ns();
    struct session_state *session = bpf_map_lookup_elem(&dfa_session_map, &src_ip);

    if (!session) {
        struct session_state new_session = {};
        new_session.state = STATE_INIT;
        new_session.last_seen = now;
        new_session.ping_count = 0;
        new_session.publish_count = 0;
        new_session.connect_count = 0;
        bpf_map_update_elem(&dfa_session_map, &src_ip, &new_session, BPF_ANY);
        session = bpf_map_lookup_elem(&dfa_session_map, &src_ip);
        if (!session)
            return XDP_PASS;
    }

    // --- TRANSIÇÕES DA MÁQUINA DE ESTADOS (DFA) ---
    switch (mqtt_msg_type) {

        case MQTT_MSG_CONNECT:
            session->connect_count++;
            // Detecta e bloqueia rajadas anômalas de re-conexão sem atividade de dados
            if (session->state == STATE_CONNECTED && session->connect_count > 3 && session->publish_count == 0) {
                session->state = STATE_BLOCKED;
                __u8 drop_flag = 1;
                bpf_map_update_elem(&blocked_ips_map, &src_ip, &drop_flag, BPF_ANY);
                return XDP_DROP;
            }
            session->state = STATE_CONNECTED;
            session->ping_count = 0;
            break;

        case MQTT_MSG_SUBSCRIBE:
            // Transição legítima de assinante (sensor_sub) - Impede falso positivo no PINGREQ
            if (session->state == STATE_CONNECTED || session->state == STATE_INIT) {
                session->state = STATE_SUBSCRIBED;
            }
            break;

        case MQTT_MSG_PUBLISH:
            // Transição de publicador (sensor_evento / sensor_jitter)
            session->state = STATE_ACTIVE_PUBLISH;
            session->publish_count++;
            session->ping_count = 0;
            break;

        case MQTT_MSG_PINGREQ:
            // No estado apenas CONNECTED (sem SUBSCRIBE nem PUBLISH), PINGREQs em excesso disparam a mitigação SlowTT
            if (session->state == STATE_CONNECTED) {
                session->ping_count++;
                if (session->ping_count > MAX_PING_WITHOUT_DATA) {
                    session->state = STATE_BLOCKED;
                    __u8 drop_flag = 1;
                    bpf_map_update_elem(&blocked_ips_map, &src_ip, &drop_flag, BPF_ANY);
                    return XDP_DROP;
                }
            }
            break;

        default:
            break;
    }

    session->last_seen = now;
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
