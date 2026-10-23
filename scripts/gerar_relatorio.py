#!/usr/bin/env python3
import os
import re
import sys
import argparse
import subprocess
import csv

# ==============================================================================
# FUNÇÕES DE SUPORTE E EXECUÇÃO DE COMANDOS
# ==============================================================================
def run_cmd(cmd):
    """Executa um comando no shell e retorna a saída formatada."""
    try:
        res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return res.strip()
    except Exception:
        return "0"

def obter_duracao_e_tamanho(pcap):
    """Extrai a duração (s) e tamanho (bytes) do arquivo PCAP via capinfos ou tshark."""
    duracao = 0.0
    tamanho_bytes = 0

    out_cap = run_cmd(f"capinfos -u -s -d -i {pcap} 2>/dev/null")
    m_dur = re.search(r"Capture duration:\s+([\d\.]+)", out_cap)
    m_size = re.search(r"Data size:\s+(\d+)", out_cap)

    if m_dur:
        duracao = float(m_dur.group(1))
    if m_size:
        tamanho_bytes = int(m_size.group(1))

    if duracao == 0.0:
        t_start = run_cmd(f"tshark -r {pcap} -T fields -e frame.time_epoch | head -n 1")
        t_end = run_cmd(f"tshark -r {pcap} -T fields -e frame.time_epoch | tail -n 1")
        try:
            duracao = float(t_end) - float(t_start)
        except Exception:
            duracao = 1.0

    if tamanho_bytes == 0:
        try:
            tamanho_bytes = os.path.getsize(pcap)
        except Exception:
            tamanho_bytes = 1

    return duracao, tamanho_bytes

def processar_scheck(csv_path="/Mestrado/scripts/s_check_metrics.csv"):
    """Lê as métricas de tempo real gravadas pelo script s_check.py."""
    if not os.path.exists(csv_path):
        return """
### 📈 Métricas de Disponibilidade do $S_{check}$
* **Status:** Nenhum dado do $S_{check}$ registrado para este ensaio.
""", 0.0

    total = 0
    sucessos = 0
    falhas = 0
    latencias = []

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row["status"] == "OK":
                sucessos += 1
                try:
                    latencias.append(float(row["latencia_ms"]))
                except ValueError:
                    pass
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
# PROCESSAMENTO DO RELATÓRIO POR CENÁRIO
# ==============================================================================
def gerar(cenario):
    mapeamento = {
        "off": {
            "pcap": "/Mestrado/scripts/baseline_off.pcap",
            "out": "/Mestrado/scripts/relatorio_xdp_off.md",
            "titulo": "Cenário 0: Baseline sem Proteção (XDP OFF)",
            "defesa": "NENHUMA (`OFF` - Roteamento Padrão Linux)"
        },
        "iptables": {
            "pcap": "/Mestrado/scripts/iptables.pcap",
            "out": "/Mestrado/scripts/relatorio_iptables.md",
            "titulo": "Cenário 1: Mitigação L4 (iptables)",
            "defesa": "Netfilter / iptables (Filtro por Limite de Conexões/Taxa)"
        },
        "heuristic": {
            "pcap": "/Mestrado/scripts/heuristic.pcap",
            "out": "/Mestrado/scripts/relatorio_xdp_heuristic.md",
            "titulo": "Cenário 2: Mitigação eBPF/XDP Heurística (Sem DFA)",
            "defesa": "eBPF/XDP Stateful Heurístico (Contadores Sem Validação de Estados)"
        },
        "dfa": {
            "pcap": "/Mestrado/scripts/dfa.pcap",
            "out": "/Mestrado/scripts/relatorio_xdp_dfa.md",
            "titulo": "Cenário 3: Mitigação eBPF/XDP Proposta (Com Autômato DFA)",
            "defesa": "eBPF/XDP Stateful com Validação Formal via Autômato Finito Determinístico"
        }
    }

    config = mapeamento.get(cenario.lower())
    if not config:
        print(f"[X] Cenário '{cenario}' inválido! Opções válidas: off, iptables, heuristic, dfa")
        sys.exit(1)

    pcap_file = config["pcap"]
    output_report = config["out"]
    titulo_cenario = config["titulo"]
    mecanismo_defesa = config["defesa"]

    print("==================================================================")
    print(f" 📊 GERADOR DE RELATÓRIO EXPERIMENTAL — {cenario.upper()} ")
    print("==================================================================")

    # Inputs para Recursos do Hardware (docker stats)
    print("\n[+] Digite as métricas observadas no 'docker stats' durante o teste.")
    print("    (Pressione ENTER para aceitar os valores padrão do print)\n")

    broker_cpu_def = "0.23%"
    broker_ram_def = "26.33 MiB"
    gateway_cpu_def = "0.00%"
    gateway_ram_def = "17.12 MiB"
    soquetes_def = "1024" if cenario == "off" else "3"

    broker_cpu = input(f"-> CPU do Broker Mosquitto [{broker_cpu_def}]: ").strip() or broker_cpu_def
    broker_ram = input(f"-> RAM do Broker Mosquitto [{broker_ram_def}]: ").strip() or broker_ram_def
    gateway_cpu = input(f"-> CPU do Gateway [{gateway_cpu_def}]: ").strip() or gateway_cpu_def
    gateway_ram = input(f"-> RAM do Gateway [{gateway_ram_def}]: ").strip() or gateway_ram_def
    soquetes_ocupados = input(f"-> Soquetes ocupados no Broker (ss -tna) [{soquetes_def}]: ").strip() or soquetes_def

    if not broker_cpu.endswith("%"): broker_cpu += "%"
    if not gateway_cpu.endswith("%"): gateway_cpu += "%"
    if "MiB" not in broker_ram and "MB" not in broker_ram: broker_ram += " MiB"
    if "MiB" not in gateway_ram and "MB" not in gateway_ram: gateway_ram += " MiB"

    print("\n[*] Extraindo e calculando métricas do PCAP, logs e S_check...")

    if not os.path.exists(pcap_file):
        print(f"[X] AVISO: Arquivo de captura {pcap_file} não encontrado. Gerando com dados parciais.")

    # 1. Extração de Métricas L3/L4 via tshark
    total_pacotes = int(run_cmd(f"tshark -r {pcap_file} | wc -l") or 0)
    connect_pkts = int(run_cmd(f"tshark -r {pcap_file} -Y 'mqtt.msgtype == 1' | wc -l") or 0)
    publish_pkts = int(run_cmd(f"tshark -r {pcap_file} -Y 'mqtt.msgtype == 3' | wc -l") or 0)
    pingreq_pkts = int(run_cmd(f"tshark -r {pcap_file} -Y 'mqtt.msgtype == 12' | wc -l") or 0)
    tcp_zero_win = int(run_cmd(f"tshark -r {pcap_file} -Y 'tcp.window_size == 0' | wc -l") or 0)

    # 2. Cálculos Matemáticos Automáticos de Vazão e Bandwidth
    duracao_s, tamanho_bytes = obter_duracao_e_tamanho(pcap_file) if os.path.exists(pcap_file) else (1.0, 1)
    vazao_pps = total_pacotes / duracao_s if duracao_s > 0 else 0.0
    vazao_kbps = ((tamanho_bytes * 8) / (duracao_s * 1000)) if duracao_s > 0 else 0.0

    total_mqtt = connect_pkts + publish_pkts + pingreq_pkts
    r_payload = ((publish_pkts / total_mqtt) * 100.0) if total_mqtt > 0 else 0.0

    # 3. Métricas do Log de Mensagens Recebidas (Subscriber)
    log_msg = "/Mestrado/scripts/mensagens_recebidas.log"
    msgs_entregues = int(run_cmd(f"grep -c 'iot/' {log_msg}") or 0) if os.path.exists(log_msg) else 0
    taxa_perda_telemetria = (((publish_pkts - msgs_entregues) / publish_pkts) * 100.0) if publish_pkts > 0 else 0.0

    # 4. Leitura do S_check
    texto_scheck, taxa_disp_scheck = processar_scheck()

    cap_info = run_cmd(f"capinfos -d -M -u {pcap_file} 2>/dev/null") if os.path.exists(pcap_file) else "Sem PCAP"
    data_hora = run_cmd("date '+%Y-%m-%d %H:%M:%S'")

    # 5. Construção do Documento em Markdown
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
    doc.append("```text")
    doc.append(str(cap_info))
    doc.append("```\n")
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

    print(f"[✓] Relatório gerado com SUCESSO em: {output_report}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador Unificado de Relatórios por Cenário")
    parser.add_argument("--cenario", choices=["off", "iptables", "heuristic", "dfa"], default="off",
                        help="Cenário do experimento (off, iptables, heuristic, dfa)")
    args = parser.parse_args()

    gerar(args.cenario)
