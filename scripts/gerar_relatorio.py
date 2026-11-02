#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import subprocess
import statistics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def processar_nconn():
    csv_path = os.path.join(SCRIPT_DIR, "nconn_series.csv")
    pico = 0
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    pico = max(pico, int(row["nconn_estab"]))
                except: pass
    return pico

def processar_recursos():
    csv_path = os.path.join(SCRIPT_DIR, "recursos_series.csv")
    cpu_gw = []
    ram_gw = []
    cpu_br = []
    ram_br = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cpu_gw.append(float(row["cpu_gateway"].replace('%','')))
                    cpu_br.append(float(row["cpu_broker"].replace('%','')))
                    # Pegando os números da RAM (ex: '25.4MiB')
                    ram_g = ''.join(c for c in row["ram_gateway"] if c.isdigit() or c=='.')
                    ram_b = ''.join(c for c in row["ram_broker"] if c.isdigit() or c=='.')
                    if ram_g: ram_gw.append(float(ram_g))
                    if ram_b: ram_br.append(float(ram_b))
                except: pass
                
    def format_max(lista, sufixo):
        return f"{max(lista):.2f}{sufixo}" if lista else "N/A"
        
    return {
        "gw_cpu": format_max(cpu_gw, "%"), "gw_ram": format_max(ram_gw, " MiB"),
        "br_cpu": format_max(cpu_br, "%"), "br_ram": format_max(ram_br, " MiB")
    }

def processar_pdr_atacante():
    csv_path = os.path.join(SCRIPT_DIR, "ataque_tentativas.csv")
    tentativas = 0
    sucessos = 0
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tentativas += 1
                if row["resultado"] == "OK":
                    sucessos += 1
    pdr = (sucessos / tentativas * 100.0) if tentativas > 0 else 0.0
    return tentativas, sucessos, pdr

def processar_telemetria_e_latencia():
    lat_csv = os.path.join(SCRIPT_DIR, "latencia_mensagens.csv")
    evt_csv = os.path.join(SCRIPT_DIR, "envios_evento.csv")
    jit_csv = os.path.join(SCRIPT_DIR, "envios_jitter.csv")
    
    enviados = 0
    for path in [evt_csv, jit_csv]:
        if os.path.exists(path):
            enviados += sum(1 for line in open(path)) - 1 # Ignora header
    enviados = max(0, enviados)

    recebidos = 0
    latencias = []
    if os.path.exists(lat_csv):
        with open(lat_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                recebidos += 1
                try: latencias.append(float(row["latencia_ms"]))
                except: pass
                
    perda_telemetria = ((enviados - recebidos) / enviados * 100.0) if enviados > 0 else 0.0
    lat_media = statistics.mean(latencias) if latencias else 0.0
    
    latencias.sort()
    idx_p95 = int(0.95 * len(latencias)) if latencias else 0
    lat_p95 = latencias[idx_p95] if latencias else 0.0

    return enviados, recebidos, perda_telemetria, lat_media, lat_p95

def processar_vazao(pcap_file):
    duracao, tamanho_bytes = 1.0, 0
    if os.path.exists(pcap_file):
        try: tamanho_bytes = os.path.getsize(pcap_file)
        except: pass
        
        t_start = run_cmd(f"tcpdump -tt -nn -r {pcap_file} 2>/dev/null | head -n 1 | cut -d' ' -f1")
        t_end = run_cmd(f"tcpdump -tt -nn -r {pcap_file} 2>/dev/null | tail -n 1 | cut -d' ' -f1")
        try: duracao = max(float(t_end) - float(t_start), 1.0)
        except: duracao = 1.0

    vazao_pps = int(run_cmd(f"tcpdump -nn -r {pcap_file} 2>/dev/null | wc -l") or 0) / duracao
    vazao_kbps = (tamanho_bytes * 8) / (duracao * 1000)
    return vazao_pps, vazao_kbps

def gerar(defesa, cenario):
    pcap_file = os.path.join(SCRIPT_DIR, f"captura_{defesa}_{cenario}.pcap")
    relatorio_file = os.path.join(SCRIPT_DIR, f"relatorio_final_{defesa}_{cenario}.md")

    nconn_pico = processar_nconn()
    rec = processar_recursos()
    tentativas_atq, sucessos_atq, pdr_atq = processar_pdr_atacante()
    telemetria_env, telemetria_rec, perda_telemetria, lat_media, lat_p95 = processar_telemetria_e_latencia()
    vazao_pps, vazao_kbps = processar_vazao(pcap_file)

    # Formatação baseada no cenário (Se não houver atacante ou sensor no cenário, marca com "—")
    texto_pdr_atq = f"{pdr_atq:.2f}% ({sucessos_atq} conexões de {tentativas_atq} tentativas)" if cenario in ["atacante", "todos"] else "— (Sem ataque no cenário)"
    texto_perda_tel = f"{perda_telemetria:.2f}% ({telemetria_rec} entregues de {telemetria_env} enviadas)" if cenario in ["legitimo", "todos"] else "— (Sem sensores no cenário)"
    texto_latencia = f"Média: {lat_media:.2f} ms | P95: {lat_p95:.2f} ms" if cenario in ["legitimo", "todos"] else "—"

    doc = f"""# 📊 Relatório das 6 Métricas Essenciais
**Defesa:** {defesa.upper()} | **Cenário:** {cenario.upper()}

### 1. Nconn (Exaustão de Soquetes)
* **Pico de Conexões no Broker:** {nconn_pico} soquetes estabelecidos

### 2. Uso de CPU e RAM (Pico do Hardware)
* **Gateway (Filtro):** CPU: {rec["gw_cpu"]} | RAM: {rec["gw_ram"]}
* **Broker (Alvo):** CPU: {rec["br_cpu"]} | RAM: {rec["br_ram"]}

### 3. PDR do Atacante (Eficiência do Filtro)
* **Sucesso do Ataque (O que chegou vs Tentou):** {texto_pdr_atq}
*(Taxas próximas a 0% indicam que a defesa XDP descartou o ataque).*

### 4. Perda de Telemetria dos Sensores (Dano Colateral)
* **Perda de Dados Legítimos:** {texto_perda_tel}

### 5. Latência (Atraso na Rede)
* **Tempo de Resposta MQTT (Fim-a-Fim):** {texto_latencia}

### 6. Vazão (Throughput na Interface)
* **Largura de Banda:** {vazao_kbps:.2f} kbps
* **Pacotes por Segundo:** {vazao_pps:.2f} pps
"""

    with open(relatorio_file, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f"[✓] Relatório puro gerado em: {relatorio_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("defesa")
    parser.add_argument("cenario")
    args = parser.parse_args()
    gerar(args.defesa, args.cenario)
