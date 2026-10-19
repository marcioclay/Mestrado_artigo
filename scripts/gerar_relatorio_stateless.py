#!/usr/bin/env python3
import json
import os
import subprocess
import sys

# ==============================================================================
# CONFIGURAÇÕES DO CENÁRIO 1: XDP STATELESS
# ==============================================================================
PCAP_FILE = "/Mestrado/scripts/stateless.pcap"
LOG_MSG = "/Mestrado/scripts/mensagens_stateless.log"
OUTPUT_REPORT = "/Mestrado/scripts/relatorio_xdp_stateless.md"


def run_cmd(cmd):
  """Executa um comando no shell e retorna a saída."""
  try:
    res = subprocess.check_output(
        cmd, shell=True, text=True, stderr=subprocess.DEVNULL
    )
    return res.strip()
  except Exception:
    return "0"


def ler_metricas_ebpf_stateless():
  """Lê o mapa eBPF 'ip_rate_map' do programa XDP Stateless e extrai as contagens."""
  cmd = "docker exec clab-seg-gateway bpftool -p map dump name ip_rate_map 2>/dev/null"
  total_pacotes_mapa = 0
  ips_registrados = 0

  try:
    saida = subprocess.check_output(cmd, shell=True, text=True)
    if saida:
      dados = json.loads(saida)
      ips_registrados = len(dados)
      for item in dados:
        valor = item.get("value", {})
        if isinstance(valor, dict):
          total_pacotes_mapa += valor.get("count", 0)
  except Exception as e:
    print(f"[!] Aviso ao ler o mapa eBPF ip_rate_map: {e}")

  return ips_registrados, total_pacotes_mapa


def analisar():
  print("==================================================================")
  print(" 📊 GERADOR DE RELATÓRIO — CENÁRIO 1: XDP STATELESS ")
  print("==================================================================")

  # Entrada dos dados de hardware (docker stats)
  broker_cpu = input("-> CPU do Broker Mosquitto [ex: 0.94%]: ").strip() or "0.94%"
  broker_ram = (
      input("-> RAM do Broker Mosquitto [ex: 23.99 MiB]: ").strip()
      or "23.99 MiB"
  )
  gateway_cpu = input("-> CPU do Gateway [ex: 0.02%]: ").strip() or "0.02%"
  gateway_ram = (
      input("-> RAM do Gateway [ex: 139.1 MiB]: ").strip() or "139.1 MiB"
  )
  soquetes_ocupados = (
      input("-> Conexões no Broker (ss -tna) [ex: 231]: ").strip() or "231"
  )

  # Leitura dos dados do Kernel
  ips_registrados, pacotes_mapa = ler_metricas_ebpf_stateless()

  total_pacotes = "0"
  if os.path.exists(PCAP_FILE):
    total_pacotes = run_cmd(f"tshark -r {PCAP_FILE} | wc -l")

  data_hora = run_cmd("date '+%Y-%m-%d %H:%M:%S'")

  relatorio = f"""# 📊 Relatório Experimental — Cenário 1: XDP Stateless (Filtro por Limiar)

**Data e Hora da Análise:** {data_hora}
**Mecanismo de Defesa:** `XDP Stateless` (Programa eBPF `xdp_stateless.o`)
**Arquivo de Captura Principal:** `{PCAP_FILE}`

---

## 1. Consumo de Recursos de Hardware (docker stats)
| Contêiner | Função no Experimento | Uso de CPU | Uso de Memória RAM |
| :--- | :--- | :---: | :---: |
| `clab-seg-mqtt` | Broker Mosquitto (Alvo) | **{broker_cpu}** | **{broker_ram}** |
| `clab-seg-gateway` | Gateway eBPF/XDP | **{gateway_cpu}** | **{gateway_ram}** |

---

## 2. Métricas Extraídas do Kernel Linux (bpftool ip_rate_map)
* **Endereços IP Monitorados no Mapa:** {ips_registrados}
* **Total de Pacotes Processados pelo eBPF:** {pacotes_mapa}
* **Pacotes Capturados no PCAP:** {total_pacotes}

---

## 3. Avaliação de Impacto e Métricas de Segurança
| Métrica de Desempenho | Valor Observado | Impacto Técnico |
| :--- | :---: | :--- |
| **Conexões Simultâneas no Broker ($N_{{conn}}$)** | **{soquetes_ocupados} soquetes** | Taxa limitada por IP no driver XDP (vs. 1024 no Baseline). |
| **Ação do eBPF/XDP** | **RATE-LIMITING** | Descarte de pacotes excedentes a 30 pps por IP. |

---

## 4. Conclusões do Cenário XDP Stateless
1. **Mitigação Parcial em Borda:** O eBPF limitou a taxa de entrada de pacotes por IP, reduzindo o total de conexões mantidas no Mosquitto de 1024 para {soquetes_ocupados}.
2. **Uso Eficiente do Gateway:** O Gateway operou com uso mínimo de CPU ({gateway_cpu}) e {gateway_ram} de RAM.
"""

  with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
    f.write(relatorio)

  print(f"\n[✓] Relatório do Cenário 1 gerado com SUCESSO em: {OUTPUT_REPORT}\n")


if __name__ == "__main__":
  analisar()
