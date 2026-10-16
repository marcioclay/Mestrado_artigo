#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <netinet/in.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_helpers.h>

#define MAX_PACKETS_PER_SEC 30

struct pkt_stats {
    __u64 last_time;
    __u32 count;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 8192);
    __type(key, __u32);
    __type(value, struct pkt_stats);
} ip_rate_map SEC(".maps");

SEC("xdp")
int xdp_stateless_filter(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return XDP_PASS;

    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end) return XDP_PASS;
    if (iph->protocol != IPPROTO_TCP) return XDP_PASS;

    __u32 src_ip = iph->saddr;
    __u64 now = bpf_ktime_get_ns();

    struct pkt_stats *stats = bpf_map_lookup_elem(&ip_rate_map, &src_ip);
    if (!stats) {
        struct pkt_stats new_stat = {.last_time = now, .count = 1};
        bpf_map_update_elem(&ip_rate_map, &src_ip, &new_stat, BPF_ANY);
        return XDP_PASS;
    }

    // Janela de 1 segundo (1.000.000.000 ns)
    if (now - stats->last_time > 1000000000ULL) {
        stats->last_time = now;
        stats->count = 1;
        return XDP_PASS;
    }

    stats->count++;
    // Se ultrapassar o limiar volumétrico estatístico, descarta (sem validar o estado L7 do protocolo)
    if (stats->count > MAX_PACKETS_PER_SEC) {
        return XDP_DROP;
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
