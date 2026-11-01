#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define MAX_PING_THRESHOLD 5
#define MQTT_PORT 1883

struct stats_info {
    __u32 ping_count;
    __u32 publish_count;
};

// Mapa para contadores por IP
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, struct stats_info);
} stateful_map SEC(".maps");

// Mapa de bloqueio em Fast-Path
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u32);
} blocked_ips_map SEC(".maps");

SEC("xdp")
int xdp_stateful_filter(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    // 1. Parsing Ethernet
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return XDP_PASS;

    // 2. Parsing IP
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) return XDP_PASS;
    if (iph->protocol != IPPROTO_TCP) return XDP_PASS;

    __u32 ip_src = iph->saddr;

    // 3. Fast-Path: Consulta se IP já está bloqueado
    __u32 *is_blocked = bpf_map_lookup_elem(&blocked_ips_map, &ip_src);
    if (is_blocked) {
        return XDP_DROP;
    }

    // 4. Parsing TCP
    struct tcphdr *tcph = (void *)(iph + 1);
    if ((void *)(tcph + 1) > data_end) return XDP_PASS;

    if (bpf_ntohs(tcph->dest) != MQTT_PORT) return XDP_PASS;

    // 5. Acesso ao Payload MQTT (Camada 7)
    unsigned char *mqtt_payload = (unsigned char *)tcph + (tcph->doff * 4);
    if ((void *)(mqtt_payload + 1) > data_end) return XDP_PASS;

    unsigned char mqtt_type = mqtt_payload[0] & 0xF0;

    // 6. Atualização dos Contadores no BPF Map (Sem validação gramatical de DFA)
    struct stats_info *stats = bpf_map_lookup_elem(&stateful_map, &ip_src);
    if (!stats) {
        struct stats_info new_stats = {.ping_count = 0, .publish_count = 0};
        bpf_map_update_elem(&stateful_map, &ip_src, &new_stats, BPF_ANY);
        return XDP_PASS;
    }

    // Regra Heurística Sem DFA: Apenas compara contadores brutos
    if (mqtt_type == 0xC0) { // PINGREQ
        stats->ping_count++;
        // Se acumulou pings sem nunca publicar, aplica bloqueio
        if (stats->ping_count > MAX_PING_THRESHOLD && stats->publish_count == 0) {
            __u32 drop_flag = 1;
            bpf_map_update_elem(&blocked_ips_map, &ip_src, &drop_flag, BPF_ANY);
            return XDP_DROP;
        }
    } else if (mqtt_type == 0x30) { // PUBLISH
        stats->publish_count++;
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
