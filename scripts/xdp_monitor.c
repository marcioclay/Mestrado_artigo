#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_helpers.h>

// Estrutura para métricas de tráfego
struct metricas_host {
    __u64 total_pacotes;
    __u64 total_bytes;
};

// Mapa 1: Estatísticas globais de tráfego monitorado
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 2); 
    __type(key, __u32);
    __type(value, struct metricas_host);
} estatisticas SEC(".maps");

// Mapa 2: Tabela de rastreamento de IPs de origem
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 8192); 
    __type(key, __u32);        
    __type(value, __u64);      
} ips_detectados SEC(".maps");

SEC("xdp")
int programa_monitor_xdp(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;

    // 1. Validação da Camada Ethernet (L2)
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return XDP_PASS;
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return XDP_PASS;

    // 2. Validação da Camada IPv4 (L3)
    struct iphdr *iph = data + sizeof(struct ethhdr);
    if ((void *)(iph + 1) > data_end) return XDP_PASS;

    // Filtra apenas tráfego TCP (protocolo 6)
    if (iph->protocol != IPPROTO_TCP) return XDP_PASS;

    // 3. Validação da Camada TCP (L4)
    struct tcphdr *tcph = (void *)iph + (iph->ihl * 4);
    if ((void *)(tcph + 1) > data_end) return XDP_PASS;

    // Verifica se o destino ou a origem é a porta do Broker MQTT (1883)
    if (tcph->dest == bpf_htons(1883) || tcph->source == bpf_htons(1883)) {
        __u32 ip_origem = iph->saddr;
        __u64 tamanho_pacote = data_end - data;
        __u32 chave = 0; // Chave 0 do array de estatísticas

        // Atualiza contadores globais
        struct metricas_host *metricas = bpf_map_lookup_elem(&estatisticas, &chave);
        if (metricas) {
            __sync_fetch_and_add(&metricas->total_pacotes, 1);
            __sync_fetch_and_add(&metricas->total_bytes, tamanho_pacote);
        }

        // Registra/atualiza o timestamp do IP no mapa de rastreamento
        __u64 ts = bpf_ktime_get_ns();
        bpf_map_update_elem(&ips_detectados, &ip_origem, &ts, BPF_ANY);
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
