#!/usr/bin/env python3
import os
import re
import sys
import csv
import struct
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# LEITOR NATIVO DE ARQUIVOS PCAP (SEM DEPENDÊNCIAS EXTERNAS)
# ==============================================================================
def parse_pcap_native(pcap_path):
    if not os.path.exists(pcap_path):
        return 0, 0, 0, 0, 0, 1.0, 0

    tamanho_bytes = os.path.getsize(pcap_path)
    if tamanho_bytes < 24:
        return 0, 0, 0, 0, 0, 1.0, tamanho_bytes

    total_pkts = 0
    connect_pkts = 0
    publish_pkts = 0
    pingreq_pkts = 0
    zero_win_pkts = 0
    first_ts = None
    last_ts = None

    try:
        with open(pcap_path, 'rb') as f:
            global_header = f.read(24)
            if len(global_header) < 24:
                return 0, 0, 0, 0, 0, 1.0, tamanho_bytes

            magic = global_header[:4]
            if magic in (b'\xd4\xc3\xb2\xa1', b'\x4d\x3c\xb2\xa1'):
                endian = '<'
            elif magic in (b'\xa1\xb2\xc3\xd4', b'\xa1\xb2\x3c\x4d'):
                endian = '>'
            else:
                return None

            link_type = struct.unpack(endian + 'I', global_header[20:24])[0]

            while True:
                pkt_hdr = f.read(16)
                if len(pkt_hdr) < 16:
                    break
                ts_sec, ts_usec, incl_len, orig_len = struct.unpack(endian + 'IIII', pkt_hdr)
                pkt_data = f.read(incl_len)
                if len(pkt_data) < incl_len:
                    break

                total_pkts += 1
                ts = ts_sec + (ts_usec / 1e6)
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

                eth_offset = 14
                if link_type in (0, 108):
                    eth_offset = 4
                elif link_type in (113, 276):
                    eth_offset = 16 if link_type == 113 else 20

                ip_data = None
                for offset in (eth_offset, 14, 16, 20, 4, 0):
                    if len(pkt_data) >= offset + 20:
                        if (pkt_data[offset] & 0xf0) == 0x40:
                            ip_data = pkt_data[offset:]
                            break

                if ip_data is None or len(ip_data) < 20:
                    continue

                ip_header_len = (ip_data[0] & 0x0f) * 4
                protocol = ip_data[9]

                if protocol == 6:  # TCP
                    tcp_data = ip_data[ip_header_len:]
                    if len(tcp_data) < 20:
                        continue

                    window_size = struct.unpack('>H', tcp_data[14:16])[0]
                    if window_size == 0:
                        zero_win_pkts += 1

                    tcp_header_len = ((tcp_data[12] >> 4) & 0x0f) * 4
                    payload = tcp_data[tcp_header_len:]

                    if len(payload) > 0:
                        msg_type = (payload[0] & 0xf0) >> 4
                        if msg_type == 1:
                            connect_pkts += 1
                        elif msg_type == 3:
                            publish_pkts += 1
                        elif msg_type == 12:
                            pingreq_pkts += 1

        duracao = (last_ts - first_ts) if (first_ts is not None and last_ts is not None and last_ts > first_ts) else 1.0
        return total_pkts, connect_pkts, publish_pkts, pingreq_pkts, zero_win_pkts, duracao, tamanho_bytes

    except Exception:
        return None

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def run_cmd(cmd):
    try:
        res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return res.strip()
    except Exception:
        return "0"

def get_docker_stats(container_name):
    try:
        cmd = f"docker stats --no-stream --format '{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}' {container_name}"
        out = run_cmd(cmd)
        if "|" in out:
            cpu, mem = out.split("|", 1)
            mem = mem.split("/")[0].strip()
            return cpu.strip(), mem
    except Exception:
        pass
    return "N/A", "N/A"

def get_mqtt_sockets():
    """Lê a quantidade de soquetes registada a meio do teste antes do pkill."""
    try:
        txt_path = os.path.join(SCRIPT_DIR, "soquetes_pico.txt")
        if os.path.exists(txt_path):
            with open(txt_path, 'r') as f:
                val = f.read().strip()
                if val:
                    return val
    except Exception:
        pass
    return "0"

def obter_duracao_e_tamanho(pcap):
    duracao = 0.0
    tamanho_bytes = 0

    out_cap = run_cmd(f"capinfos -u -s -d -i {pcap} 2>/dev/null")
    m_dur = re.search(r"Capture duration:\s+([\d\.]+)", out_cap)
    m_size = re.search(r"Data size:\s+(\d+)", out_cap)

    if m_dur: duracao = float(m_dur.group(1))
    if m_size: tamanho_bytes = int(m_size.group(1))

    if duracao == 0.0:
        t_start = run_cmd(f"tcpdump -tt -nn -r {pcap} 2>/dev/null | head -n 1 | cut -d' ' -f1")
        t_end = run_cmd(f"tcpdump -tt -nn -r {pcap} 2>/dev/null | tail -n 1 | cut -d' ' -f1")
        try: duracao = float(t_end) - float(t_start)
        except Exception: duracao = 1.0

    if tamanho_bytes == 0:
        try: tamanho_bytes = os.path.getsize(pcap)
        except Exception: tamanho_bytes = 1

    return duracao, tamanho_bytes

def processar_scheck(csv_path):
    if not os.path.exists(csv_path):
        return """\n### 📈 Métricas de Disponibilidade do $S_{check}$\n* **Status:** Nenhum dado do $S_{check}$ registrado para este ensaio.\n""", 0.0

    total, sucessos, falhas = 0, 0, 0
    latencias = []

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get("status") == "OK":
                sucessos += 1
                try: latencias.append(float(row["latencia_ms"]))
                except (ValueError, KeyError): pass
            else:
                falhas += 1

    taxa_disp = (sucessos / total) * 100.0 if total > 0 else 0.0
    lat_media = (sum(latencias) / len(latencias)) if latencias else 0.0
    lat_max = max(latencias) if latencias else 0.0

    texto_md = f"""
### 📈 Métricas de Disponibilidade e Latência em Tempo Real ($S_{{check}}$)
* **Total de Sondagens de Conexão Realizadas:** {total}
* **Taxa de Disponibilidade Real do Broker:** **{taxa_disp:.2f}%** ({sucessos} sucessos / {falhas} falhas)
* **Latência Média de Resposta (Legítimos):** {lat_media:.2f} ms
* **Latência Máxima Registrada:** {lat_max:.2f} ms
"""
    return texto_md, taxa_disp

# ==============================================================================
# CONSTRUÇÃO DO RELATÓRIO
# ==============================================================================
def gerar(defesa, cenario):
    mapeamento_defesa = {
        "off": "NENHUMA (`OFF` - Roteamento Padrão Linux)",
        "iptables": "Netfilter / iptables (Filtro por Limite de Conexões/Taxa)",
        "stateless": "eBPF/XDP Stateless (Sem Autômato / Contadores)",
        "stateful": "eBPF/XDP Stateful Heurístico (Contadores Sem Validação de Estados)",
        "dfa": "eBPF/XDP Stateful com Validação Formal via Autômato Finito Determinístico"
    }

    if defesa.lower() not in mapeamento_defesa:
        print(f"[X] Defesa '{defesa}' inválida! Opções: off, iptables, stateless, stateful, dfa")
        sys.exit(1)

    pcap_file = os.path.join(SCRIPT_DIR, f"captura_{defesa}_{cenario}.pcap")
    output_report = os.path.join(SCRIPT_DIR, f"relatorio_{defesa}_{cenario}.md")
    csv_scheck = os.path.join(SCRIPT_DIR, "s_check_metrics.csv")
    log_msg = os.path.join(SCRIPT_DIR, "mensagens_recebidas.log")
    
    titulo_cenario = f"Cenário: {cenario.upper()} | Defesa: {defesa.upper()}"
    mecanismo_defesa = mapeamento_defesa[defesa.lower()]

    print(f"[*] Processando métricas: {defesa.upper()} / {cenario.upper()}")

    broker_cpu, broker_ram = get_docker_stats("clab-seg-mqtt")
    gateway_cpu, gateway_ram = get_docker_stats("clab-seg-gateway")
    soquetes_ocupados = get_mqtt_sockets()

    res_native = parse_pcap_native(pcap_file) if os.path.exists(pcap_file) else None

    if res_native is not None:
        total_pacotes, connect_pkts, publish_pkts, pingreq_pkts, tcp_zero_win, duracao_s, tamanho_bytes = res_native
    else:
        total_pacotes = int(run_cmd(f"tcpdump -nn -r {pcap_file} 2>/dev/null | wc -l") or 0)
        connect_pkts = int(run_cmd(f"tcpdump -nn -r {pcap_file} 'tcp[((tcp[12:1] & 0xf0) >> 2):1] = 0x10' 2>/dev/null | wc -l") or 0)
        publish_pkts = int(run_cmd(f"tcpdump -nn -r {pcap_file} '(tcp[((tcp[12:1] & 0xf0) >> 2):1] & 0xf0) = 0x30' 2>/dev/null | wc -l") or 0)
        pingreq_pkts = int(run_cmd(f"tcpdump -nn -r {pcap_file} 'tcp[((tcp[12:1] & 0xf0) >> 2):1] = 0xc0' 2>/dev/null | wc -l") or 0)
        tcp_zero_win = int(run_cmd(f"tcpdump -nn -r {pcap_file} 'tcp[14:2] = 0' 2>/dev/null | wc -l") or 0)
        duracao_s, tamanho_bytes = obter_duracao_e_tamanho(pcap_file) if os.path.exists(pcap_file) else (1.0, 1)

    vazao_pps = total_pacotes / duracao_s if duracao_s > 0 else 0.0
    vazao_kbps = ((tamanho_bytes * 8) / (duracao_s * 1000)) if duracao_s > 0 else 0.0

    total_mqtt = connect_pkts + publish_pkts + pingreq_pkts
    r_payload = ((publish_pkts / total_mqtt) * 100.0) if total_mqtt > 0 else 0.0

    msgs_entregues = int(run_cmd(f"grep -c 'iot/' {log_msg}") or 0) if os.path.exists(log_msg) else 0
    taxa_perda_telemetria = (((publish_pkts - msgs_entregues) / publish_pkts) * 100.0) if publish_pkts > 0 else 0.0

    texto_scheck, taxa_disp_scheck = processar_scheck(csv_scheck)
    cap_info = run_cmd(f"capinfos -d -M -u {pcap_file} 2>/dev/null") if os.path.exists(pcap_file) else "Sem PCAP"
    data_hora = run_cmd("date '+%Y-%m-%d %H:%M:%S'")

    doc = []
    doc.append(f"# 📊 Relatório Experimental — {titulo_cenario}\n")
    doc.append(f"**Data e Hora da Análise:** {data_hora}")
    doc.append(f"**Mecanismo de Defesa:** {mecanismo_defesa}")
    doc.append(f"**Arquivo de Captura Principal:** `{pcap_file}`\n")
    doc.append("---\n")

    doc.append("## 1. Consumo de Recursos de Hardware (docker stats)")
    doc.append("Métricas observadas nos contêineres durante a execução do ensaio:\n")
    doc.append("| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |")
    doc.append("| :--- | :--- | :--- | :--- |")
    doc.append(f"| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **{broker_cpu}** | **{broker_ram}** |")
    doc.append(f"| `clab-seg-gateway` | Gateway eBPF/XDP | **{gateway_cpu}** | **{gateway_ram}** |\n")
    doc.append("---\n")

    doc.append("## 2. Análise da Camada de Rede e Transporte (L3/L4 - PCAP)")
    doc.append("Métricas extraídas da interface de rede do Gateway:\n")
    doc.append(f"* **Total de Pacotes Capturados:** {total_pacotes:,} pacotes")
    doc.append(f"* **Duração Média da Captura:** {duracao_s:.2f} segundos (~{duracao_s/60:.1f} minutos)")
    doc.append(f"* **Volume Total de Dados:** {tamanho_bytes:,} bytes (~{tamanho_bytes/(1024*1024):.2f} MB)")
    doc.append(f"* **Vazão Média de Pacotes:** **{vazao_pps:.2f} pps**")
    doc.append(f"* **Largura de Banda Média Consumida:** **{vazao_kbps:.2f} kbps**")
    doc.append(f'* **Pacotes com "TCP Zero Window" (Slow Read):** {tcp_zero_win}')
    doc.append("* **Resumo Técnico da Captura (`capinfos`):**")
    doc.append("```text\n" + str(cap_info) + "\n```\n")
    doc.append("---\n")

    doc.append("## 3. Análise da Camada de Aplicação (L7 - MQTT)")
    doc.append("Detalhamento das mensagens do protocolo MQTT interceptadas:\n")
    doc.append(f"* **Pacotes `CONNECT` (Solicitações de Sessão):** {connect_pkts:,}")
    doc.append(f"* **Pacotes `PUBLISH` (Telemetria Legítima):** {publish_pkts:,}")
    doc.append(f"* **Pacotes `PINGREQ` (Manutenção Keep-Alive / SlowTT):** {pingreq_pkts:,}")
    doc.append(f"* **Razão de Payload Útil ($R_{{payload}}$):** **{r_payload:.2f}%**")
    doc.append(f"* **Mensagens Legítimas Entregues ao Subscriber:** {msgs_entregues:,} de {publish_pkts:,} (Perda de **{taxa_perda_telemetria:.1f}%**)\n")
    doc.append("---\n")

    doc.append("## 4. Avaliação de Impacto e Disponibilidade Continuada")
    doc.append(texto_scheck)
    doc.append("| Métrica de Desempenho | Valor Observado | Impacto Técnico |")
    doc.append("| :--- | :--- | :--- |")
    doc.append(f"| **Conexões Simultâneas no Broker ($N_{{conn}}$)** | **{soquetes_ocupados} soquetes** | Estado da tabela de soquetes no Mosquitto. |")
    doc.append(f"| **Disponibilidade para Novos Clientes ($S_{{check}}$)** | **{taxa_disp_scheck:.1f}%** | Capacidade de processar novas conexões legítimas. |")
    doc.append(f"| **Taxa de Perda de Telemetria** | **{taxa_perda_telemetria:.1f}%** | Percentual de mensagens de sensores não entregues. |\n")
    doc.append("---\n")
    doc.append(f"*Relatório gerado automaticamente para o {titulo_cenario}.*")

    with open(output_report, "w", encoding="utf-8") as f:
        f.write("\n".join(doc))

    print(f"[✓] Salvo em: {output_report}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador Unificado de Relatórios por Cenário")
    parser.add_argument("defesa", help="Mecanismo de defesa (off, iptables, stateless, stateful, dfa)")
    parser.add_argument("cenario", help="Cenário do experimento (legitimo, atacante, todos)")
    args = parser.parse_args()
    gerar(args.defesa, args.cenario)
