#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/in.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_helpers.h>

/* ============================================================================
 * xdp_monitor_dfa.c (v2)
 *
 * Corrige, em relação à versão anterior:
 *
 *   1. [BUG CRÍTICO] MQTT_MSG_SUBSCRIBE estava definido como 0x82, mas
 *      mqtt_msg_type é extraído com "payload[0] & 0xF0" (mascara o nibble
 *      baixo). O valor mascarado NUNCA pode ser 0x82 (máximo possível é
 *      0x80), então o "case MQTT_MSG_SUBSCRIBE" era código morto: nenhum
 *      cliente saía do estado CONNECTED ao assinar um tópico. Isso fazia
 *      com que um assinante legítimo e ocioso (ex.: sensor-sub) fosse
 *      estatisticamente indistinguível de um bot SlowTT para este próprio
 *      autômato, pois o estado SUBSCRIBED que deveria protegê-lo nunca era
 *      alcançado. Corrigido para 0x80 (valor mascarado correto).
 *
 *   2. [MELHORIA] blocked_ips_map passa de "flag __u8" para uma struct com
 *      timestamp do bloqueio e motivo (CONNECT flood vs PINGREQ flood).
 *      Isso dá rastreabilidade para a métrica de "tempo até mitigação"
 *      (quando o bloqueio ocorreu, relativo ao início do ataque) e permite
 *      diferenciar, na análise, qual heurística disparou cada bloqueio.
 *
 *   3. [MELHORIA] Bloqueio passa a ter expiração (TTL). Na versão anterior,
 *      uma vez bloqueado, o IP ficava bloqueado pelo resto do teste inteiro
 *      (sem TTL), diferente do caminho iptables (--seconds 3600, embora na
 *      prática maior que a duração do teste). Um TTL curto e documentado
 *      (BLOCK_TTL_NS) dá uma janela de recuperação e torna o comportamento
 *      comparável entre defesas.
 *
 *   4. [DECISÃO DE DESIGN DOCUMENTADA, SEM MUDANÇA DE CÓDIGO] O estado do
 *      autômato (dfa_session_map) continua chaveado por IP de origem, e
 *      não por tupla (IP, porta). Isso é intencional e válido NESTA
 *      topologia: cada dispositivo legítimo (sensor-evento, sensor-sub,
 *      sensor-jitter, monitor-scheck) tem um IP exclusivo, nunca
 *      compartilhado. Só o pool do atacante compartilha IPs entre vários
 *      bots (~35 conexões por IP, 31 IPs), e bloquear por IP nesse caso é
 *      exatamente o comportamento desejado: qualquer bot malicioso naquele
 *      IP já justifica tratar o IP inteiro como comprometido. Se no futuro
 *      um cenário atribuir IPs compartilhados também a clientes legítimos,
 *      esta decisão precisa ser revisitada (chave por tupla IP+porta).
 *
 *   5. <linux/in.h> incluído explicitamente para declarar IPPROTO_TCP, em
 *      vez de depender de inclusão transitiva por outro header.
 * ============================================================================
 */

// Estados do Autômato DFA (q0..q4)
#define STATE_INIT           0
#define STATE_CONNECTED      1
#define STATE_SUBSCRIBED     2
#define STATE_ACTIVE_PUBLISH 3
#define STATE_BLOCKED        4

// Tipos de Pacotes MQTT, já mascarados com "& 0xF0" (nibble superior do
// Control Packet Byte). Os quatro valores abaixo são os únicos que esse
// mascaramento pode produzir para os tipos que este programa distingue:
//   CONNECT    = 0b0001 xxxx -> mascarado: 0x10
//   SUBSCRIBE  = 0b1000 xxxx -> mascarado: 0x80 (flags obrigatórias 0010
//                                descartadas pela máscara; por isso 0x82
//                                nunca aparece aqui - bug da v1)
//   PUBLISH    = 0b0011 xxxx -> mascarado: 0x30
//   PINGREQ    = 0b1100 0000 -> mascarado: 0xC0
#define MQTT_MSG_CONNECT    0x10
#define MQTT_MSG_PUBLISH    0x30
#define MQTT_MSG_SUBSCRIBE  0x80   // CORRIGIDO: era 0x82 (inalcançável após a máscara)
#define MQTT_MSG_PINGREQ    0xC0

// Limite de PINGREQ sem subscrição/publicação para detecção de SlowTT
#define MAX_PING_WITHOUT_DATA 5

// Limite de reconexões (CONNECT) sem publicação, no estado CONNECTED
#define MAX_RECONNECT_WITHOUT_DATA 3

// Janela de bloqueio (TTL): 60 segundos. Ajustável conforme a duração do
// ensaio; deve ser documentada no artigo como parâmetro do experimento.
#define BLOCK_TTL_NS (60ULL * 1000000000ULL)

// Motivos de bloqueio, para rastreabilidade/telemetria
#define BLOCK_REASON_CONNECT_FLOOD 1
#define BLOCK_REASON_PINGREQ_FLOOD 2

// Estrutura de Estado de Sessão (chaveada por IP de origem - ver nota de
// design #4 acima)
struct session_state {
    __u32 state;                  // Estado do autômato (q0..q4)
    __u64 last_seen;              // Timestamp em nanossegundos
    __u32 ping_count;             // Contagem acumulada de PINGREQs no estado CONNECTED
    __u32 publish_count;          // Contagem de pacotes PUBLISH
    __u32 connect_count;          // Contagem de tentativas de (re)conexão
};

// Informação de bloqueio: timestamp (para TTL e para a métrica de tempo
// até mitigação) e motivo (para diferenciar heurísticas na análise)
struct block_info {
    __u64 block_ts_ns;
    __u32 reason;
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
    __type(value, struct block_info);
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
    __u64 now = bpf_ktime_get_ns();

    // 3. Fast-Path: Verifica se o IP já está bloqueado, com expiração (TTL)
    struct block_info *blocked = bpf_map_lookup_elem(&blocked_ips_map, &src_ip);
    if (blocked) {
        if (now - blocked->block_ts_ns > BLOCK_TTL_NS) {
            // TTL expirado: remove o bloqueio e segue para processamento
            // normal abaixo, dando ao IP uma janela de recuperação.
            bpf_map_delete_elem(&blocked_ips_map, &src_ip);
        } else {
            return XDP_DROP; // Descarte direto no nível da placa de rede
        }
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
            // Detecta e bloqueia rajadas anômalas de (re)conexão sem
            // atividade de dados. Válido tanto para reconexões repetidas
            // de um único cliente quanto para múltiplos bots que
            // compartilham o mesmo IP de origem (ver nota de design #4).
            if (session->state == STATE_CONNECTED &&
                session->connect_count > MAX_RECONNECT_WITHOUT_DATA &&
                session->publish_count == 0) {
                session->state = STATE_BLOCKED;
                struct block_info new_block = {};
                new_block.block_ts_ns = now;
                new_block.reason = BLOCK_REASON_CONNECT_FLOOD;
                bpf_map_update_elem(&blocked_ips_map, &src_ip, &new_block, BPF_ANY);
                return XDP_DROP;
            }
            session->state = STATE_CONNECTED;
            session->ping_count = 0;
            break;

        case MQTT_MSG_SUBSCRIBE:
            // Transição legítima de assinante (sensor_sub) - Impede falso
            // positivo no PINGREQ. CORRIGIDO: antes nunca disparava (ver
            // nota #1 no cabeçalho do arquivo).
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
            // No estado apenas CONNECTED (sem SUBSCRIBE nem PUBLISH),
            // PINGREQs em excesso disparam a mitigação SlowTT. Com a
            // correção #1, um assinante legítimo já transitou para
            // STATE_SUBSCRIBED antes de chegar aqui e não é penalizado.
            if (session->state == STATE_CONNECTED) {
                session->ping_count++;
                if (session->ping_count > MAX_PING_WITHOUT_DATA) {
                    session->state = STATE_BLOCKED;
                    struct block_info new_block = {};
                    new_block.block_ts_ns = now;
                    new_block.reason = BLOCK_REASON_PINGREQ_FLOOD;
                    bpf_map_update_elem(&blocked_ips_map, &src_ip, &new_block, BPF_ANY);
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