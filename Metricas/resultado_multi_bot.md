# 📊 Avaliação Experimental: Mitigação do Ataque SlowTT via eBPF/XDP e Netfilter

Este relatório apresenta os resultados empíricos obtidos na avaliação de mecanismos de defesa contra o ataque **SlowTT** (*Low-and-Slow Denial of Service* em MQTT), em um cenário de **botnet distribuída com 31 endereços IP de origem simulados**.

---

## 1. Tabela Comparativa de Desempenho

| Métrica / Recurso | XDP Stateful DFA (Proposto) | XDP Stateful Heurístico | Netfilter / iptables Tradicional |
|---|:---:|:---:|:---:|
| **Mecanismo / Arquivo** | `xdp_monitor_dfa.o` | `xdp_stateful.o` | `connlimit/recent/hashlimit` |
| **Taxa de Detecção (TPR)** | **100,0%** | **100,0%** | **0,0%** |
| **Falsos Positivos (FPR)** | **0,0%** | **> 0%** | **0,0%** |
| **Tempo de Detecção (\(T_{det}\))** | **3,0 s** | **3,2 s** | **2,0 s** |
| **Conexões Retidas (\(N_{conn}\))** | **127** | **3** | **158** |
| **Uso de CPU do Gateway** | 0,00% | 0,00% | 0,00% |
| **Uso de RAM do Gateway** | 14,40 MiB | 13,15 MiB | 13,05 MiB |
| **Uso de CPU do Broker** | 0,07% | 0,07% | 0,17% |
| **Uso de RAM do Broker** | 74,16 MiB | 73,85 MiB | 74,32 MiB |

---

## 2. Gráficos Comparativos das Métricas Principais

### A. Taxa de Detecção do Ataque (TPR)

*Quanto maior, melhor.*

```text
XDP Stateful DFA (Proposto) : [████████████████████████████████] 100,0%
XDP Stateful Heurístico     : [████████████████████████████████] 100,0%
Netfilter / iptables        : [                                ]   0,0%
```

**Interpretação:** nos resultados reportados, os dois mecanismos XDP detectaram o ataque, enquanto o Netfilter/iptables não registrou detecções segundo o critério adotado.

### B. Taxa de Falsos Positivos (FPR)

*Indica a proporção de tráfego legítimo classificado incorretamente como malicioso.*

```text
XDP Stateful Heurístico     : [████████████████████████████████] > 0% — valor não especificado
XDP Stateful DFA (Proposto) : [                                ] 0,0%
Netfilter / iptables        : [                                ] 0,0%
```

**Interpretação:** o mecanismo heurístico apresentou bloqueio indevido do `sensor_sub`. Os outros dois mecanismos registraram FPR de 0,0% nos testes apresentados.

> **Nota:** a barra do mecanismo heurístico é apenas ilustrativa, pois o valor numérico exato do FPR não foi informado.

### C. Tempo de Detecção (\(T_{det}\))

*Menor tempo indica detecção mais rápida, desde que medido com o mesmo critério e nas mesmas condições.*

```text
Netfilter / iptables        : [██████████                      ] 2,0 s
XDP Stateful DFA (Proposto) : [███████████████                 ] 3,0 s
XDP Stateful Heurístico     : [████████████████                ] 3,2 s
```

**Interpretação:** o Netfilter/iptables apresentou o menor tempo de detecção informado, embora tenha registrado TPR de 0,0%. Isso evidencia que o tempo de reação, isoladamente, não demonstra eficácia: é necessário considerar também a capacidade de identificar corretamente o ataque.

---

## 3. Principais Destaques Técnicos

### 3.1. Limitação do firewall tradicional diante de múltiplos IPs de origem

Nos resultados reportados, o Netfilter/iptables apresentou TPR de 0,0% no cenário com 31 IPs de origem simulados. Uma hipótese para esse resultado é que a distribuição das conexões entre diferentes endereços tenha permitido que cada origem permanecesse abaixo dos limites estáticos configurados por IP.

Essa interpretação deve ser confirmada por meio das regras efetivamente aplicadas, da distribuição das conexões por endereço IP e dos registros de pacotes descartados.

### 3.2. Comportamento do XDP Stateful DFA em relação aos falsos positivos

O XDP Stateful DFA apresentou TPR de 100,0% e FPR de 0,0% nos resultados informados. O mecanismo foi projetado para considerar transições de estado associadas ao protocolo MQTT, buscando distinguir o comportamento malicioso do tráfego legítimo.

O resultado sugere que a abordagem pode reduzir bloqueios indevidos em comparação com a heurística testada. Entretanto, a ausência de falsos positivos deve ser limitada ao conjunto de cenários, cargas e amostras avaliados.

### 3.3. Descarte de pacotes no caminho rápido do XDP

A arquitetura eBPF/XDP permite processar e descartar pacotes em um estágio inicial do caminho de recepção da rede, antes do processamento convencional completo pelo kernel e pela aplicação.

Os valores de CPU do gateway foram registrados como 0,00% nos três cenários. Esse resultado deve ser interpretado considerando a resolução e o método de medição: um valor arredondado para zero não comprova ausência absoluta de custo computacional.

---

## 4. Considerações sobre os Resultados

Antes de consolidar as conclusões do artigo, recomenda-se verificar:

1. **Definição do TPR:** especificar quais eventos foram considerados detecções bem-sucedidas e como a taxa foi calculada.
2. **Definição do FPR:** informar a quantidade de fluxos ou mensagens legítimas avaliadas e quantos foram bloqueados indevidamente.
3. **Tempo de detecção:** documentar o instante inicial da medição e o critério usado para determinar que o ataque foi detectado.
4. **Conexões retidas:** esclarecer se os valores correspondem às conexões totais, às conexões de origem maliciosa ou às conexões que permaneceram após a mitigação.
5. **Carga experimental:** manter equivalentes a duração do ataque, o número de origens, a taxa de envio e o perfil dos clientes legítimos.
6. **Consumo de recursos:** informar a ferramenta de monitoramento, o intervalo de amostragem e a precisão das medições de CPU e RAM.

## 5. Conclusão Preliminar

Nos experimentos reportados, o XDP Stateful DFA apresentou TPR de 100,0% e FPR de 0,0%, enquanto o mecanismo heurístico também apresentou TPR de 100,0%, mas registrou falsos positivos. O Netfilter/iptables apresentou TPR de 0,0% no cenário distribuído avaliado.

Esses resultados preliminares sugerem que o acompanhamento de estado pode ser útil para mitigar ataques SlowTT sem bloquear o tráfego legítimo observado. Contudo, a superioridade da abordagem proposta depende da validação dos critérios de detecção, da repetibilidade dos ensaios e da confirmação de que os mecanismos foram comparados sob condições equivalentes.
