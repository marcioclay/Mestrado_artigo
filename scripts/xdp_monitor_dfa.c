#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <netinet/in.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_helpers.h>

// Definições dos Estados do Autômato DFA
#define STATE_INIT           0
#define STATE_CONNECTED      1
#define STATE_SUBSCRIBED     2
#define STATE_ACTIVE_PUBLISH 3
#define STATE_BLOCKED        4

// Tipos de Pacotes MQTT (Header Control Byte)
#define MQTT_MSG_CONNECT    0x10
#define MQTT_MSG_PUBLISH    0x30
#define MQTT_MSG_SUBSCRIBE  0x82
#define MQTT_MSG_PINGREQ    0xC0

// Limite configurável de PINGREQ sem mensagens de dados para gatilho de ataque SlowTT
#define MAX_PING_WITHOUT_DATA 5

// Estrutura armazenada na memória do Kernel (BPF Map)
struct session_state {
    __u32 state;                  // Estado atual do autômato (q0..q4)
    __u64 last_seen;              // Timestamp em nanossegundos
    __u32 ping_count;             // Contagem acumulada de PINGREQs consecutivos
    __u32 publish_count;          // Contagem de pacotes de dados PUBLISH
};

// Mapa 1: Tabela de Estado dos Clientes (Stateful Session Tracking)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 8192);
    __type(key, __u32);                 // IP de origem
    __type(value, struct session_state);
} dfa_session_map SEC(".maps");

// Mapa 2: Tabela de Filtro Rápido para Negação (XDP_DROP)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 8192);
    __type(key, __u32);                 // IP de Origem Bloqueado
    __type(value, __u8);
} blocked_ips_map SEC(".maps");

SEC("xdp")
int xdp_mqtt_dfa_filter(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    // 1. Validação Ethernet (L2)
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return XDP_PASS;

    // 2. Validação IPv4 (L3)
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) return XDP_PASS;
    if (iph->protocol != IPPROTO_TCP) return XDP_PASS;

    __u32 src_ip = iph->saddr;

    // 3. Verificação de Bloqueio Efetivo Antecipado (Fast-Path DROP)
    __u8 *blocked = bpf_map_lookup_elem(&blocked_ips_map, &src_ip);
    if (blocked) {
        return XDP_DROP; // Descarte no nível do driver NIC
    }

    // 4. Validação TCP (L4)
    struct tcphdr *tcph = (void *)iph + (iph->ihl * 4);
    if ((void *)(tcph + 1) > data_end) return XDP_PASS;

    // Aplica a inspeção apenas para o tráfego direcionado à porta 1883 do Broker
    if (tcph->dest != bpf_htons(1883)) return XDP_PASS;

    // Cálculo do Offset para o Payload da Camada de Aplicação (L7 MQTT)
    unsigned char *payload = (unsigned char *)tcph + (tcph->doff * 4);
    if ((void *)(payload + 1) > data_end) return XDP_PASS;

    __u8 mqtt_msg_type = payload[0] & 0xF0; // Máscara para ler o Nibble superior (Header Type)

    // Consulta ou inicializa a sessão no Mapa do DFA
    struct session_state *session = bpf_map_lookup_elem(&dfa_session_map, &src_ip);
    struct session_state new_session = {};
    __u64 now = bpf_ktime_get_ns();

    if (!session) {
        new_session.state = STATE_INIT;
        new_session.last_seen = now;
        new_session.ping_count = 0;
        new_session.publish_count = 0;
        bpf_map_update_elem(&dfa_session_map, &src_ip, &new_session, BPF_ANY);
        session = bpf_map_lookup_elem(&dfa_session_map, &src_ip);
        if (!session) return XDP_PASS;
    }

    // --- TRANSIÇÕES DA MÁQUINA DE ESTADOS (DFA) ---
    switch (mqtt_msg_type) {

        case MQTT_MSG_CONNECT:
            session->state = STATE_CONNECTED;
            session->ping_count = 0;
            break;

        case MQTT_MSG_SUBSCRIBE:
            // Permite que o 'sensor_sub.py' permaneça em estado legítimo de escuta sem ser bloqueado
            if (session->state == STATE_CONNECTED || session->state == STATE_INIT) {
                session->state = STATE_SUBSCRIBED;
            }
            break;

        case MQTT_MSG_PUBLISH:
            // Dispositivos que enviam dados reais de telemetria ('sensor_jitter' e 'sensor_evento')
            session->state = STATE_ACTIVE_PUBLISH;
            session->publish_count++;
            session->ping_count = 0; // Reinicia o contador de pings suspeitos
            break;

        case MQTT_MSG_PINGREQ:
            session->ping_count++;

            // Se o IP está enviando recorrentes PINGREQ sem ter transitado para dados/subscrição válida,
            // ou se excedeu o limiar seguro, transita para STATE_BLOCKED
            if (session->state == STATE_CONNECTED && session->ping_count > MAX_PING_WITHOUT_DATA) {
                session->state = STATE_BLOCKED;
                __u8 drop_flag = 1;
                bpf_map_update_elem(&blocked_ips_map, &src_ip, &drop_flag, BPF_ANY);
                return XDP_DROP;
            }
            break;

        default:
            break;
    }

    session->last_seen = now;
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
