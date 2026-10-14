# Guia de Métricas para Avaliação Experimental: eBPF/XDP vs. iptables em Gateways IoT

Este documento consolida a estrutura de métricas recomendada pela literatura científica (Vaccari et al. [14, 16], Pham Le et al. [17], Kirdan et al. [20]) para a avaliação e caracterização de ataques **Slow DoS em MQTT** (especificamente o **SlowTT**) e a validação do mecanismo de mitigação baseado em **eBPF/XDP** em comparação ao **iptables** (Netfilter) em Gateways IoT de borda.

---

## 1. Justificativa Metodológica (Exclusão de ML/DL na Borda)

Conforme verificado na literatura recente (estudos com os datasets *MQTTset* [11] e *MQTTEEB-D* [12]), a utilização de modelos de Aprendizado de Máquina (*Machine Learning*) e Aprendizado Profundo (*Deep Learning*) diretamente no fluxo em tempo real de Gateways IoT apresenta limitações operacionais críticas:

* **Latência de Inferência e Custo de Processamento:** Modelos supervisionados pesados ou de Deep Learning (ex.: GRU, LSTM, CNN) exigem janelas de pré-processamento e extração de *features* em espaço de usuário (*user-space*), introduzindo atrasos de processamento incompatíveis com o tempo de linha (*line-rate*) do driver de rede [11, 15].
* **Ausência de Reação Instantânea:** A inferência baseada em ML atua na classificação/detecção posterior, necessitando de uma camada operacional adicional no kernel para aplicar o bloqueio efetivo de pacotes.
* **Escassez e Ruído em Datasets Sintéticos:** A variação natural de tráfego em redes IoT reais gera altas taxas de falsos positivos quando modelos treinados com dados sintéticos são expostos a flutuações legítimas [12, 15].

Por essas razões, a arquitetura adota a **verificação comportamental determinística baseada em métricas de estado e temporizadores no kernel (eBPF/XDP)**, garantindo descarte imediato na camada do driver de rede [11, 16].

---

## 2. Métricas de Identificação do Ataque SlowTT (Camada L4 / L7)

O ataque **SlowTT** explora a retenção contínua de sessões no Broker MQTT através do envio estratégico de pacotes de controle curtos (`PINGREQ`), mantendo $R_{payload} \approx 0$ e esgotando a tabela de soquetes (`max_connections`) do Mosquitto [14, 20]. 

Para caracterizar esse comportamento sem necessidade de inspeção pesada no *user-space*, utilizam-se as seguintes métricas em nível de kernel:

### A. Razão de Payload Útil ($R_{payload}$)
* **Definição:** Proporção entre o número de mensagens de telemetria com dados reais (`PUBLISH`) e o número total de pacotes de controle/manutenção de sessão (`CONNECT` + `PINGREQ`) [14].
* **Fórmula:**
  $$R_{payload} = \frac{\text{Contagem de PUBLISH}}{\text{Contagem de PINGREQ + CONNECT}}$$
* **Interpretação:** Em fluxos de sensores legítimos, $R_{payload} > 0.5$ (envio regular de dados) [11]. Em conexões maliciosas do SlowTT, $R_{payload} \to 0$ [14].

### B. Tempo de Inatividade e Cadência de Controle ($T_{interval}$)
* **Definição:** Intervalo de tempo (em milissegundos) medido entre a recepção de pacotes `PINGREQ` consecutivos de um mesmo endereço IP de origem [14, 16].
* **Interpretação:** O SlowTT envia pacotes de manutenção em intervalos calculados para evitar o encerramento por *timeout* do Broker ($WT < 1.5 \times \text{Keep-Alive}$) [14]. A regularidade temporal estrita combinada com $R_{payload} \approx 0$ caracteriza a anomalia [14, 16].

### C. Densidade de Conexões por Origem ($N_{conn}$)
* **Definição:** Quantidade de conexões TCP simultâneas mantidas no estado `ESTABLISHED` por um único endereço IP apontando para a porta do serviço MQTT (1883/8883) [14, 20].
* **Interpretação:** Utilizada para identificar a alocação predatória de tabela de soquetes do servidor [14].

---

## 3. Métricas de Desempenho e Impacto na Infraestrutura (Gateway & Rede)

Para compor os experimentos do artigo e comparar os cenários **(1) Sem Proteção**, **(2) Mitigação via iptables** e **(3) Mitigação via eBPF/XDP**, devem ser coletadas as seguintes métricas quantitativas [11, 13]:

| Categoria | Métrica | Unidade | Descrição / Metodologia |
| :--- | :--- | :--- | :--- |
| **Recursos do Gateway** | **Uso de CPU por Núcleo** | Porcentagem (%) | Medição da utilização individual dos cores do processador (ex.: Raspberry Pi) via `top` / `psutil` [13]. |
| **Recursos do Gateway** | **Consumo de Memória RAM** | Megabytes (MB) | Alocação de memória do sistema para gerenciamento da tabela de regras/mapas e pacotes em trânsito [13]. |
| **Recursos do Gateway** | **Tempo de Decisão (*Drop Latency*)** | Nanossegundos (ns) | Tempo decorrido entre a chegada do pacote na interface e a execução da ação de descarte (`XDP_DROP` vs. `iptables DROP`). |
| **Qualidade de Serviço (QoS)** | **Taxa de Entrega Legítima (PDR)** | Porcentagem (%) | Percentual de mensagens `PUBLISH` de sensores legítimos que chegam com sucesso ao Broker. |
| **Qualidade de Serviço (QoS)** | **Latência E2E / RTT** | Milissegundos (ms) | Tempo de ida e volta do tráfego do sensor legítimo sob o impacto do descarte de ataques na borda [13, 15]. |
| **Disponibilidade do Broker** | **Soquetes Retidos no Broker** | Unidades (integer) | Contagem de conexões presas na porta 1883 do Mosquitto (`ss -tna \| grep :1883 \| wc -l`) [14]. |

---

## 4. Tabela Comparativa de Resultados Esperados (Matriz para o Artigo)

| Métrica de Avaliação | Sem Proteção (Baseline) | Mitigação via `iptables` | Mitigação via `eBPF/XDP` |
| :--- | :--- | :--- | :--- |
| **Status do Broker MQTT** | Negação de Serviço (Tabela Cheia) [14] | Operacional (Com Carga) [17] | Operacional (Sem Carga) [11] |
| **Consumo de CPU no Gateway** | Baixo no Gateway / Alto no Broker | Elevado (Processamento no Netfilter) | Mínimo (Descarte no Driver / NIC) [11] |
| **Alocação de Memória Kernel** | Padrão | Crescimento Dinâmico (`sk_buff`) | Constante (Tamanho Fixo do eBPF Map) [11] |
| **Latência do Sensor Legítimo** | Alta / Timeout na Conexão [14] | Moderada / Flutuante | Baixa e Estável ($\approx 1\text{ ms}$) [13] |
| **Camada do Descarte** | N/A (Pacote atinge o Broker) | Camada de Rede / Transporte (L3/L4) | Camada de Driver / Ingress (XDP) [11] |

---

## 5. Referências Bibliográficas de Apoio

1. **Vaccari, I., Chiola, G., Aiello, M., Mongelli, M., & Cambiaso, E. (2020).** *SlowITe, a Novel Denial of Service Attack Affecting MQTT.* Sensors, 20(10), 2932 [14, 18].
2. **Castro, M. F., Medeiros, R. L. P., Lucena Junior, V. F., & Bessa, I. (2024).** *Classificação de ataques cibernéticos em redes MQTT com base em aprendizado de máquina.* Anais do XXV Congresso Brasileiro de Automática (CBA 2024) [11].
3. **Pham Le, P.-H., Do, Q. N., Dinh, T. Q., Pham, H.-T.-N., & Nguyen, L. V. (2026).** *A comparative security analysis of MQTT brokers against DoS attacks.* Journal on Information Security, 2026:5 [17].
4. **El-Hajj, M., & Vorotilov, A. (2024).** *Testing Security and Performance of MQTT Protocol on Raspberry Pi for IoT Applications.* IEEE APWiMob [13].
5. **Kirdan, E., Horvath, P., & Pahl, M. O. (2023).** *Work-in-Progress: Slow Denial of Service Attack on MQTT-Based IoT.* IEEE Cluster Computing [20, 21].
6. **Laghari, S. U. A., et al. (2024).** *Securing MQTT Ecosystem: A Survey on Vulnerabilities, Attacks, and Countermeasures.* IEEE Access [17, 18].
