# 📝 Relatório Resumido para Orientação: Comparativo Experimental

## 1. Ataque Utilizado

- **Ataque:** SlowTT (*Slow Denial of Service* direcionado ao protocolo MQTT).
- **Perfil do tráfego:** tráfego de baixa taxa (*Low-and-Slow*), projetado para esgotar a capacidade de conexões sem gerar alto volume de pacotes.

## 2. Alvo e Fragilidade Explorada

- **Alvo:** broker MQTT Mosquitto (`clab-seg-mqtt`), escutando na porta `1883`.
- **Fragilidade explorada:** manutenção de conexões retidas na tabela de soquetes da aplicação por meio de conexões com valores elevados de `Keep Alive` e envio periódico de mensagens de manutenção (`PINGREQ`). A ocupação dos recursos de conexão pode prejudicar o acesso de clientes legítimos.

## 3. Estrutura e Codificação dos Mecanismos de Defesa

### 3.1. Netfilter / iptables

- **Mecanismo:** firewall tradicional no kernel Linux.
- **Implementação:** combinação dos módulos `connlimit`, `recent` e `hashlimit` para controle e limitação de conexões e taxas de tráfego.
- **Camada de atuação:** predominantemente L3/L4, conforme as regras configuradas.

### 3.2. XDP Stateful Heurístico (`xdp_stateful.o`)

- **Mecanismo:** programa eBPF/XDP baseado em contadores e critérios heurísticos para identificar padrões de abuso.
- **Limitação observada:** bloqueio indevido de nós assinantes legítimos, como o `sensor_sub`, caracterizando falsos positivos no experimento.

### 3.3. XDP Stateful DFA (`xdp_monitor_dfa.o`)

- **Mecanismo:** programa eBPF/XDP baseado em uma máquina de estados finitos determinística (DFA).
- **Estratégia:** rastreamento e validação das transições de sessão consideradas relevantes para o protocolo MQTT.
- **Resultado observado:** ausência de falsos positivos nos testes reportados.

> **Nota metodológica:** a afirmação de eliminação de falsos positivos deve ser limitada aos cenários, cargas e amostras efetivamente testados. A inspeção de MQTT em XDP também exige considerar a segmentação TCP e o fato de que o XDP não reconstitui automaticamente o fluxo completo da conexão.

## 4. Tabela Comparativa dos Experimentos

| Métrica / Recurso | XDP Stateful Heurístico | XDP Stateful DFA | Netfilter / iptables |
|---|---:|---:|---:|
| **Mecanismo de defesa** | `xdp_stateful.o` | `xdp_monitor_dfa.o` | `connlimit` / `recent` / `hashlimit` |
| **Arquivo de captura** | `/Mestrado/scripts/stateful.pcap` | `/Mestrado/scripts/dfa.pcap` | `/Mestrado/scripts/iptables.pcap` |
| **Conexões retidas (\(N_{conn}\))** | 3 | 6 | 8 |
| **Taxa de detecção (TPR)** | 100,0% | 100,0% | 100,0% |
| **Falsos positivos (FPR)** | > 0% (alto, conforme relato) | 0,0% | 0,0% |
| **CPU do broker (`clab-seg-mqtt`)** | 0,10% | 0,06% | 0,05% |
| **RAM do broker (`clab-seg-mqtt`)** | 8,973 MiB | 8,164 MiB | 8,172 MiB |
| **CPU do gateway (`clab-seg-gateway`)** | 0,00% | 0,00% | 0,00% |
| **RAM do gateway (`clab-seg-gateway`)** | 58,21 MiB | 59,50 MiB | 58,05 MiB |

## 5. Gráficos Comparativos

Os gráficos abaixo representam os valores informados na tabela. As barras são ilustrativas e não substituem a análise estatística dos resultados.

### 5.1. Conexões retidas no broker (\(N_{conn}\))

```text
XDP Stateful Heurístico  ███       3
XDP Stateful DFA         ██████    6
Netfilter / iptables     ████████  8
```

**Interpretação:** nos resultados reportados, o mecanismo heurístico apresentou 3 conexões retidas, o DFA apresentou 6 e o Netfilter/iptables apresentou 8.

### 5.2. Taxa de falsos positivos (FPR)

```text
XDP Stateful Heurístico  > 0%  — alto, conforme relato
XDP Stateful DFA          0,0%
Netfilter / iptables      0,0%
```

**Interpretação:** o mecanismo heurístico apresentou bloqueio indevido do `sensor_sub`. Nos testes reportados, os mecanismos DFA e Netfilter/iptables não apresentaram falsos positivos.

> Para produzir um gráfico quantitativo proporcional, é necessário informar o FPR numérico do mecanismo heurístico. O valor `> 0%` não permite determinar o comprimento exato da barra.

### 5.3. Uso de memória RAM no broker (MiB)

```text
XDP Stateful Heurístico  ████████████████████  8,973 MiB
Netfilter / iptables    ██████████████████    8,172 MiB
XDP Stateful DFA        ██████████████████    8,164 MiB
```

**Interpretação:** o consumo de RAM do broker foi semelhante entre os três mecanismos. O DFA apresentou o menor valor informado, com diferença pequena em relação ao Netfilter/iptables.

## 6. Síntese dos Resultados

Com base nos dados apresentados:

1. **Detecção:** os três mecanismos reportaram TPR de 100,0%.
2. **Falsos positivos:** o mecanismo heurístico apresentou bloqueio indevido do sensor assinante, enquanto DFA e Netfilter/iptables reportaram FPR de 0,0%.
3. **Conexões retidas:** o DFA apresentou valor intermediário entre o mecanismo heurístico e o Netfilter/iptables.
4. **Consumo do broker:** os valores de CPU e RAM foram próximos entre as abordagens.
5. **Consumo do gateway:** os valores de CPU registrados como 0,00% podem refletir arredondamento ou baixa resolução de medição; não demonstram ausência absoluta de custo computacional.

### Conclusão preliminar

Nos experimentos reportados, o XDP Stateful DFA apresentou ausência de falsos positivos e consumo de recursos semelhante ao Netfilter/iptables. Entretanto, a comparação definitiva exige esclarecer a definição de TPR e FPR, repetir os ensaios, informar a duração e a carga de cada teste e apresentar medidas de variabilidade.

Os resultados de conexões retidas, isoladamente, não comprovam superioridade de mitigação. Devem ser analisados em conjunto com a taxa de entrega dos sensores legítimos, o sucesso de novas conexões, a disponibilidade do broker e a intensidade do ataque.
