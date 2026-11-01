#!/usr/bin/env python3
"""
gerar_relatorio.py (v3)

Novidades em relação à v2:
  1. Lê latencia_mensagens.csv (gerado pelo sensor.py v2, perfil "sub") e
     calcula latência P50/P95/P99 real, ponta a ponta, por mensagem.
  2. Calcula PDR (Packet/Message Delivery Ratio) por SEQUÊNCIA, não mais por
     contagem de pacotes PUBLISH do PCAP vs linhas de log. Por tópico,
     PDR = mensagens com seq única recebidas / maior seq observada.
     Isso corrige a limitação apontada na v2 (perda calculada comparando
     unidades diferentes: pacotes TCP do PCAP vs linhas de log).
  3. Mantém a métrica antiga (pacotes PUBLISH vs log) rotulada como legado,
     para comparação, até a migração completa ser validada em campo.

Herdado da v2:
  - Parser MQTT via tshark -Y mqtt (remontagem real de TCP).
  - CPU/RAM/Nconn lidos da série temporal (metricas_tempo_real_*.csv).
  - TCP Zero Window via tshark.

ATENCAO - ACAO NECESSARIA EM rodar_experimento.sh:
  sensor.py so cria latencia_mensagens.csv se o arquivo ainda nao existir
  (os.path.exists). Isso significa que, se esse arquivo nao for apagado
  entre execucoes, dados de execucoes anteriores (outra defesa/cenario)
  ficam MISTURADOS no mesmo CSV, contaminando a latencia e o PDR calculados
  aqui. Adicione ao bloco de limpeza do rodar_experimento.sh (passo 1):
      rm -f "${SCRIPT_DIR}/latencia_mensagens.csv"
  Sem essa linha, os numeros de latencia/PDR deste relatorio NAO sao
  confiaveis para comparar defesas diferentes.
"""
import os
import re
import sys
import csv
import math
import statistics
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def run_cmd(cmd):
    try:
        res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return res.strip()
    except Exception:
        return ""

def tshark_disponivel():
    return run_cmd("command -v tshark") != ""

def obter_duracao_e_tamanho(pcap):
    """Duração da captura e tamanho em bytes, via capinfos (fallback: tcpdump/os.path)."""
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

def contar_total_pacotes(pcap):
    total = run_cmd(f"tshark -r {pcap} -T fields -e frame.number 2>/dev/null | wc -l")
    try:
        return int(total)
    except Exception:
        return 0

def contar_zero_window(pcap):
    """Conta pacotes com TCP Zero Window via análise nativa do tshark (tcp.analysis.zero_window)."""
    out = run_cmd(f"tshark -r {pcap} -Y 'tcp.analysis.zero_window' -T fields -e frame.number 2>/dev/null | wc -l")
    try:
        return int(out)
    except Exception:
        return 0

def parse_mqtt_pcap(pcap):
    """
    Dissecção real de MQTT via tshark, com remontagem de segmentos TCP.
    Tipos (mqtt.msgtype): 1=CONNECT, 3=PUBLISH, 8=SUBSCRIBE, 12=PINGREQ, 13=PINGRESP.
    Retorna (connect, publish, subscribe, pingreq, primeiro_ts, ultimo_ts).
    """
    saida = run_cmd(
        f"tshark -r {pcap} -Y mqtt -T fields -e frame.time_epoch -e mqtt.msgtype 2>/dev/null"
    )
    connect = publish = subscribe = pingreq = 0
    primeiro_ts = None
    ultimo_ts = None

    for linha in saida.splitlines():
        partes = linha.split("\t")
        if len(partes) < 2:
            continue
        ts_str, tipo_str = partes[0].strip(), partes[1].strip()
        if not tipo_str:
            continue
        try:
            ts = float(ts_str)
        except ValueError:
            continue
        if primeiro_ts is None:
            primeiro_ts = ts
        ultimo_ts = ts

        for tipo in tipo_str.split(","):
            try:
                tipo_val = int(tipo)
            except ValueError:
                continue
            if tipo_val == 1:
                connect += 1
            elif tipo_val == 3:
                publish += 1
            elif tipo_val == 8:
                subscribe += 1
            elif tipo_val == 12:
                pingreq += 1

    return connect, publish, subscribe, pingreq, primeiro_ts, ultimo_ts

def parse_mem_to_mb(valor):
    """Converte string de memória do docker (ex: '15.2MiB', '1.1GiB', '512KiB') para float em MB."""
    if not valor or valor in ("N/A", ""):
        return None
    m = re.match(r"([\d\.]+)\s*([KMG]i?B)", valor.strip())
    if not m:
        return None
    num = float(m.group(1))
    unidade = m.group(2)
    if unidade.startswith("G"):
        return num * 1024
    if unidade.startswith("M"):
        return num
    if unidade.startswith("K"):
        return num / 1024
    return num

def parse_cpu_pct(valor):
    if not valor or valor in ("N/A", ""):
        return None
    try:
        return float(valor.strip().rstrip("%"))
    except ValueError:
        return None

def processar_serie_temporal(csv_path):
    """
    Lê metricas_tempo_real_<defesa>_<cenario>.csv (1 amostra/s, gerado pelo
    rodar_experimento.sh) e calcula média, pico e desvio-padrão de CPU/RAM
    do broker e do gateway, e de Nconn (conexões ESTAB).
    """
    campos = {
        "cpu_broker": [], "ram_broker": [],
        "cpu_gateway": [], "ram_gateway": [],
        "nconn": [],
    }

    if not os.path.exists(csv_path):
        return None

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cpu_b = parse_cpu_pct(row.get("cpu_broker"))
            ram_b = parse_mem_to_mb(row.get("ram_broker"))
            cpu_g = parse_cpu_pct(row.get("cpu_gateway"))
            ram_g = parse_mem_to_mb(row.get("ram_gateway"))
            try:
                nconn = int(row.get("nconn_estab", "").strip())
            except (ValueError, AttributeError):
                nconn = None

            if cpu_b is not None: campos["cpu_broker"].append(cpu_b)
            if ram_b is not None: campos["ram_broker"].append(ram_b)
            if cpu_g is not None: campos["cpu_gateway"].append(cpu_g)
            if ram_g is not None: campos["ram_gateway"].append(ram_g)
            if nconn is not None: campos["nconn"].append(nconn)

    def resumo(lista):
        if not lista:
            return {"media": 0.0, "pico": 0.0, "desvio": 0.0, "n": 0}
        media = statistics.mean(lista)
        desvio = statistics.pstdev(lista) if len(lista) > 1 else 0.0
        return {"media": media, "pico": max(lista), "desvio": desvio, "n": len(lista)}

    return {chave: resumo(valores) for chave, valores in campos.items()}

def percentil(lista_ordenada, p):
    """Percentil com interpolação linear (método comum, equivalente a numpy 'linear')."""
    if not lista_ordenada:
        return 0.0
    if len(lista_ordenada) == 1:
        return lista_ordenada[0]
    k = (len(lista_ordenada) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return lista_ordenada[int(k)]
    d0 = lista_ordenada[f] * (c - k)
    d1 = lista_ordenada[c] * (k - f)
    return d0 + d1

def processar_latencia_pdr(csv_path):
    """
    Lê latencia_mensagens.csv (gerado pelo sensor.py v2, perfil "sub") e
    calcula:
      - Latência P50/P95/P99 e média, sobre todas as mensagens recebidas.
      - PDR por tópico: mensagens com seq únicas recebidas / maior seq
        observada naquele tópico (assume seq iniciando em 1, incremento 1).
        Ressalva: se a ÚLTIMA mensagem enviada for perdida, a maior seq
        observada subestima o total enviado, e o PDR fica otimista nesse
        caso-limite. Ainda assim é mais preciso que comparar pacotes do
        PCAP com linhas de log (unidades diferentes).
    """
    if not os.path.exists(csv_path):
        return None

    latencias = []
    por_topico = {}

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["latencia_ms"])
                seq = int(row["seq"])
                topico = row["topico"]
            except (KeyError, ValueError, TypeError):
                continue

            latencias.append(lat)
            info = por_topico.setdefault(topico, {"seqs": set(), "seq_max": 0})
            info["seqs"].add(seq)
            if seq > info["seq_max"]:
                info["seq_max"] = seq

    if not latencias and not por_topico:
        return None

    latencias.sort()

    topicos_resultado = {}
    total_recebidas = 0
    total_esperadas = 0
    for topico, info in por_topico.items():
        recebidas = len(info["seqs"])
        esperadas = info["seq_max"]
        perda_pct = ((esperadas - recebidas) / esperadas * 100.0) if esperadas > 0 else 0.0
        pdr_pct = 100.0 - perda_pct
        topicos_resultado[topico] = {
            "recebidas": recebidas,
            "esperadas": esperadas,
            "perda_pct": perda_pct,
            "pdr_pct": pdr_pct,
        }
        total_recebidas += recebidas
        total_esperadas += esperadas

    pdr_global = (total_recebidas / total_esperadas * 100.0) if total_esperadas > 0 else 0.0

    return {
        "n": len(latencias),
        "media": statistics.mean(latencias) if latencias else 0.0,
        "p50": percentil(latencias, 50),
        "p95": percentil(latencias, 95),
        "p99": percentil(latencias, 99),
        "topicos": topicos_resultado,
        "pdr_global_pct": pdr_global,
        "perda_global_pct": 100.0 - pdr_global,
        "total_recebidas": total_recebidas,
        "total_esperadas": total_esperadas,
    }

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

    if not tshark_disponivel():
        print("[X] tshark não encontrado. Instale com: apt-get install -y tshark")
        sys.exit(1)

    pcap_file = os.path.join(SCRIPT_DIR, f"captura_{defesa}_{cenario}.pcap")
    output_report = os.path.join(SCRIPT_DIR, f"relatorio_{defesa}_{cenario}.md")
    csv_scheck = os.path.join(SCRIPT_DIR, "s_check_metrics.csv")
    csv_serie_temporal = os.path.join(SCRIPT_DIR, f"metricas_tempo_real_{defesa}_{cenario}.csv")
    csv_latencia = os.path.join(SCRIPT_DIR, "latencia_mensagens.csv")
    log_msg = os.path.join(SCRIPT_DIR, "mensagens_recebidas.log")

    titulo_cenario = f"Cenário: {cenario.upper()} | Defesa: {defesa.upper()}"
    mecanismo_defesa = mapeamento_defesa[defesa.lower()]

    print(f"[*] Processando métricas: {defesa.upper()} / {cenario.upper()}")

    # --- Série temporal (CPU/RAM/Nconn) ---
    serie = processar_serie_temporal(csv_serie_temporal)
    if serie is None:
        print(f"[!] Aviso: {csv_serie_temporal} não encontrado. CPU/RAM/Nconn ficarão zerados.")
        serie = {k: {"media": 0.0, "pico": 0.0, "desvio": 0.0, "n": 0}
                 for k in ("cpu_broker", "ram_broker", "cpu_gateway", "ram_gateway", "nconn")}

    # --- PCAP: duração, tamanho, total de pacotes, zero window ---
    if os.path.exists(pcap_file):
        duracao_s, tamanho_bytes = obter_duracao_e_tamanho(pcap_file)
        total_pacotes = contar_total_pacotes(pcap_file)
        tcp_zero_win = contar_zero_window(pcap_file)
        connect_pkts, publish_pkts, subscribe_pkts, pingreq_pkts, _, _ = parse_mqtt_pcap(pcap_file)
    else:
        print(f"[!] Aviso: {pcap_file} não encontrado.")
        duracao_s, tamanho_bytes = 1.0, 1
        total_pacotes = connect_pkts = publish_pkts = subscribe_pkts = pingreq_pkts = tcp_zero_win = 0

    vazao_pps = total_pacotes / duracao_s if duracao_s > 0 else 0.0
    vazao_kbps = ((tamanho_bytes * 8) / (duracao_s * 1000)) if duracao_s > 0 else 0.0

    total_mqtt = connect_pkts + publish_pkts + pingreq_pkts
    r_payload = ((publish_pkts / total_mqtt) * 100.0) if total_mqtt > 0 else 0.0

    throughput_publish = publish_pkts / duracao_s if duracao_s > 0 else 0.0

    # --- Perda legada (pacotes PUBLISH do PCAP vs linhas de log) ---
    msgs_entregues = int(run_cmd(f"grep -c 'iot/' {log_msg}") or 0) if os.path.exists(log_msg) else 0
    taxa_perda_legado = (((publish_pkts - msgs_entregues) / publish_pkts) * 100.0) if publish_pkts > 0 else 0.0

    # --- Latência e PDR reais, por sequência ---
    lat_pdr = processar_latencia_pdr(csv_latencia)

    texto_scheck, taxa_disp_scheck = processar_scheck(csv_scheck)
    cap_info = run_cmd(f"capinfos -d -M -u {pcap_file} 2>/dev/null") if os.path.exists(pcap_file) else "Sem PCAP"
    data_hora = run_cmd("date '+%Y-%m-%d %H:%M:%S'")

    def fmt_metrica(d, unidade, casas=2):
        if d["n"] == 0:
            return "— (sem amostras)"
        return f"média {d['media']:.{casas}f}{unidade} | pico {d['pico']:.{casas}f}{unidade} | σ {d['desvio']:.{casas}f}{unidade} (n={d['n']})"

    doc = []
    doc.append(f"# 📊 Relatório Experimental — {titulo_cenario}\n")
    doc.append(f"**Data e Hora da Análise:** {data_hora}")
    doc.append(f"**Mecanismo de Defesa:** {mecanismo_defesa}")
    doc.append(f"**Arquivo de Captura Principal:** `{pcap_file}`")
    doc.append(f"**Série Temporal (CPU/RAM/Nconn):** `{csv_serie_temporal}`")
    doc.append(f"**Latência/PDR (seq):** `{csv_latencia}`\n")
    doc.append("---\n")

    doc.append("## 1. Consumo de Recursos de Hardware (amostragem contínua, 1 amostra/s)")
    doc.append("Estatísticas calculadas sobre toda a janela do ensaio, não um valor pontual:\n")
    doc.append("| Contêiner | Função | CPU | RAM |")
    doc.append("| :--- | :--- | :--- | :--- |")
    doc.append(f"| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | {fmt_metrica(serie['cpu_broker'], '%')} | {fmt_metrica(serie['ram_broker'], ' MB')} |")
    doc.append(f"| `clab-seg-gateway` | Gateway eBPF/XDP | {fmt_metrica(serie['cpu_gateway'], '%')} | {fmt_metrica(serie['ram_gateway'], ' MB')} |\n")
    doc.append("---\n")

    doc.append("## 2. Ocupação de Conexões no Broker (Nconn)")
    doc.append("Calculado sobre a série temporal completa, não mais uma amostra única no meio do teste:\n")
    doc.append(f"* **Pico de Conexões Simultâneas (ESTAB):** **{serie['nconn']['pico']:.0f}**")
    doc.append(f"* **Média de Conexões Simultâneas:** {serie['nconn']['media']:.1f}")
    doc.append(f"* **Desvio-Padrão:** {serie['nconn']['desvio']:.1f}")
    doc.append(f"* **Amostras Coletadas:** {serie['nconn']['n']}\n")
    doc.append("---\n")

    doc.append("## 3. Análise da Camada de Rede e Transporte (L3/L4 - PCAP)")
    doc.append("Métricas extraídas da interface de rede do Gateway:\n")
    doc.append(f"* **Total de Pacotes Capturados:** {total_pacotes:,} pacotes")
    doc.append(f"* **Duração da Captura:** {duracao_s:.2f} segundos (~{duracao_s/60:.1f} minutos)")
    doc.append(f"* **Volume Total de Dados:** {tamanho_bytes:,} bytes (~{tamanho_bytes/(1024*1024):.2f} MB)")
    doc.append(f"* **Vazão Média de Pacotes:** **{vazao_pps:.2f} pps**")
    doc.append(f"* **Largura de Banda Média Consumida:** **{vazao_kbps:.2f} kbps**")
    doc.append(f'* **Pacotes com "TCP Zero Window" (Slow Read, via tshark):** {tcp_zero_win}')
    doc.append("* **Resumo Técnico da Captura (`capinfos`):**")
    doc.append("```text\n" + str(cap_info) + "\n```\n")
    doc.append("---\n")

    doc.append("## 4. Análise da Camada de Aplicação (L7 - MQTT, dissecção via tshark)")
    doc.append("Contagem feita com remontagem real de segmentos TCP (`tshark -Y mqtt`):\n")
    doc.append(f"* **Pacotes `CONNECT`:** {connect_pkts:,}")
    doc.append(f"* **Pacotes `SUBSCRIBE`:** {subscribe_pkts:,}")
    doc.append(f"* **Pacotes `PUBLISH` (Telemetria Legítima):** {publish_pkts:,}")
    doc.append(f"* **Pacotes `PINGREQ` (Manutenção Keep-Alive / SlowTT):** {pingreq_pkts:,}")
    doc.append(f"* **Razão de Payload Útil ($R_{{payload}}$):** **{r_payload:.2f}%**")
    doc.append(f"* **Throughput de PUBLISH (medido no PCAP):** **{throughput_publish:.3f} msg/s**\n")
    doc.append("---\n")

    doc.append("## 5. Latência e PDR por Sequência (métrica recomendada)")
    if lat_pdr is None:
        doc.append("* **Status:** Nenhum dado de `latencia_mensagens.csv` encontrado para este ensaio.")
        doc.append("  Confirme se o `sensor_sub` rodou (perfil `sub`) e se o arquivo foi limpo entre execuções.\n")
    else:
        doc.append(f"* **Mensagens Recebidas Processadas:** {lat_pdr['n']}")
        doc.append(f"* **Latência Média:** {lat_pdr['media']:.2f} ms")
        doc.append(f"* **Latência P50:** {lat_pdr['p50']:.2f} ms")
        doc.append(f"* **Latência P95:** **{lat_pdr['p95']:.2f} ms**")
        doc.append(f"* **Latência P99:** {lat_pdr['p99']:.2f} ms")
        doc.append(f"* **PDR Global (por sequência):** **{lat_pdr['pdr_global_pct']:.2f}%** "
                    f"(Perda: {lat_pdr['perda_global_pct']:.2f}%)")
        doc.append(f"* **Total Recebidas / Maior Seq. Observada:** {lat_pdr['total_recebidas']} / {lat_pdr['total_esperadas']}\n")
        doc.append("| Tópico | Recebidas | Maior Seq. Observada | PDR (%) | Perda (%) |")
        doc.append("| :--- | :--- | :--- | :--- | :--- |")
        for topico, info in lat_pdr['topicos'].items():
            doc.append(f"| `{topico}` | {info['recebidas']} | {info['esperadas']} | {info['pdr_pct']:.2f}% | {info['perda_pct']:.2f}% |")
        doc.append("")
        doc.append("> ⚠️ PDR por sequência assume seq iniciando em 1 e incrementando de 1 em 1 por tópico.")
        doc.append("> Se a ÚLTIMA mensagem enviada for justamente a perdida, a maior seq. observada subestima")
        doc.append("> o total enviado, e o PDR fica levemente otimista nesse caso-limite.\n")
    doc.append("---\n")

    doc.append("## 6. Métrica de Perda Legada (pacotes PCAP vs. log — mantida para comparação)")
    doc.append(f"* **Mensagens Legítimas Entregues (log) / Pacotes PUBLISH (PCAP):** {msgs_entregues:,} de {publish_pkts:,}")
    doc.append(f"* **Perda Legada:** {taxa_perda_legado:.1f}%")
    doc.append("> ⚠️ Esta métrica compara unidades diferentes (pacote TCP no PCAP vs. linha de log do subscriber)")
    doc.append("> e deve ser substituída pela Seção 5 (PDR por sequência) assim que validada em campo.\n")
    doc.append("---\n")

    doc.append("## 7. Avaliação de Impacto e Disponibilidade Continuada")
    doc.append(texto_scheck)
    doc.append("| Métrica de Desempenho | Valor Observado | Impacto Técnico |")
    doc.append("| :--- | :--- | :--- |")
    doc.append(f"| **Pico de Conexões Simultâneas ($N_{{conn}}$)** | **{serie['nconn']['pico']:.0f}** | Máximo real observado na série temporal. |")
    doc.append(f"| **Disponibilidade para Novos Clientes ($S_{{check}}$)** | **{taxa_disp_scheck:.1f}%** | Capacidade de processar novas conexões legítimas. |")
    if lat_pdr is not None:
        doc.append(f"| **PDR Global (por sequência)** | **{lat_pdr['pdr_global_pct']:.2f}%** | Fração real de mensagens legítimas entregues. |")
        doc.append(f"| **Latência P95** | **{lat_pdr['p95']:.2f} ms** | Degradação da comunicação legítima sob ataque. |")
    doc.append("")
    doc.append("---\n")
    doc.append(f"*Relatório gerado automaticamente para o {titulo_cenario}.*")

    with open(output_report, "w", encoding="utf-8") as f:
        f.write("\n".join(doc))

    print(f"[✓] Salvo em: {output_report}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador Unificado de Relatórios por Cenário (v3 - latência P95 + PDR por sequência)")
    parser.add_argument("defesa", help="Mecanismo de defesa (off, iptables, stateless, stateful, dfa)")
    parser.add_argument("cenario", help="Cenário do experimento (legitimo, atacante, todos)")
    args = parser.parse_args()
    gerar(args.defesa, args.cenario)
