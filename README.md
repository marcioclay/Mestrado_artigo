## 🐝 Protótipo de topologia com XDP/eBPF orquestrado por Containerlab para detectar e mitigar ataque DoS com spoofing.

> Protótipo de e deteção e mitigação usando **eBPF/XDP** em ambiente de rede virtualizado com **Containerlab**.

[![Containerlab](https://img.shields.io/badge/Containerlab-v0.50+-blue?logo=linux)](https://containerlab.dev)
[![Docker](https://img.shields.io/badge/Docker-required-blue?logo=docker)](https://www.docker.com)
[![eBPF](https://img.shields.io/badge/eBPF-XDP-orange)](https://ebpf.io)
[![Licença](https://img.shields.io/badge/licença-GPL--2.0-green)](LICENSE)
[![Linguagem](https://img.shields.io/badge/linguagem-C-blue)](https://en.wikipedia.org/wiki/C_(programming_language))



---
## 📖 Visão Geral

"Protótipo desenvolvido como atividade prática da disciplina de Redes Programáveis do Mestrado em Computação Aplicada, voltada à mitigação de ataques DDoS em gateways IoT. O sistema propõe uma Sonda de Monitoramento que utiliza eBPF e XDP para realizar a mitigação de ataques volumétricos (DDoS) com técnica de IP Spoofing."

## O que este protótipo demonstra:

**O que este protótipo demonstra:**

* **Mitigação em Nível de Driver:** Descarte de pacotes antes da alocação de memória pelo sistema operativo (sk_buff).
* **Eficiência Computacional:** Processamento de tráfego com uso mínimo de CPU, validando a arquitetura eBPF em relação a firewalls(iptables).
* **Análise Comparativa de Desempenho:** Avaliação da resiliência do Gateway sob inundações volumétricas.
* **Monitoramento Estatístico via eBPF Maps:** Uso de mapas do tipo ARRAY para contagem de pacotes e banda e mínima latência de observabilidade.
* **Seletividade de Filtro:** Implementação de regras para garantir a proteção contra ataques UDP flood sem comprometer o tráfego MQTT (TCP/1883) legítimo da infraestrutura IoT.

---

"A mitigação de ataques DDoS baseada em XDP é superior à mitigação baseada em iptables em cenários de IP Spoofing, uma vez que mantém o desempenho constante independentemente de IPs falsificados, enquanto a abordagem tradiconal, iptables sofre degradação devido à exaustão do ataque."

---

## Topologia


## 🌐 Topologia da Rede


```
┌────────────────────────────────────────────────────────┐
│                      MÁQUINA HOST                      │
│                                                        │
│  ┌────────────────────────┐    ┌────────────────────┐  │
│  │    clab-sensor    │    │    │    clab-atacante   │  │
│  │     (10.0.0.20/24)     │    │   (10.0.0.10/24)   │  │
│  └───────────┬────────────┘    └──────────┬─────────┘  │
│              │ eth1                       │ eth1       │
│              └──────────────┬─────────────┘            │
│                             ▼                          │
│                  ┌────────────────────┐                │
│                  │  clab-bridge       │                │
│                  │  (Switch Virtual)  │                │
│                  └──────────┬─────────┘                │
│                             │ eth1                     │
│                             ▼                          │
│                  ┌────────────────────┐                │
│                  │ clab- gateway      │                │
│                  │   (10.0.0.1/24)    │                │
│                  │ [Filtro eBPF/XDP]  │                │
│                  └────────────────────┘                │
└────────────────────────────────────────────────────────┘

```


| Nó     | Endereço IP  | Função                                      |
|--------|-------------|---------------------------------------------|
| atacante | `10.0.0.10`  | Emissor de pacotes - ilegítimo        |
| sensor | `10.0.0.20`  | Sensor — emissor pacotes legítimo      |
| gateway | `10.0.0.1`  | Filtro XDP - GATEWAY          |


A topologia do laboratório foi desenhada para representar um ambiente de Gateway IoT em cenário de borda, estruturada em uma topologia tipo "estrela" controlada por um elemento central.

A rede é composta por três componentes principais:

- Gateway: alvo da defesa, onde reside o filtro eBPF/XDP. Configurado para interceptar todo o tráfego que transita entre a rede. O gateway simulaum raspberry com 3G e 1 CPU>
- Sensor: Simula o dispositivo IoT legítimo que realiza a telemetria, utilizando um perfil de rede com latência e perda (via tc qdisc) para emular condições reais de conexão Wi-Fi. O sensor possui 512Mb de RAM e 1 CPU.
- Atacante: gerador de tráfego anômalo - técnica de IP Spoofing (--rand-source) para simular uma botnet distribuída.

---

## 🔧 Pré-requisitos


### 0. Requisitos do Sistema

Os seguintes requisitos devem ser atendidos para que a ferramenta containerlab seja executada com sucesso (https://containerlab.dev/install/):

- Um usuário com privilégios de sudo para executar o containerlab.

- Um servidor Linux, pode ser WSL2 (https://learn.microsoft.com/pt-br/windows/wsl/install).

### 1. Instalar o Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

> Saia e entre novamente na sessão após adicionar seu usuário ao grupo `docker`.

### 2. Instalar o Containerlab

```
bash -c "$(curl -sL https://get.containerlab.dev)"
```

Verifique a instalação:

```
containerlab version
```

---

### 3. Obtendo o Laboratório

Clone o repositório e acesse o diretório do laboratório:

```bash
git clone https://github.com/marcioclay/Mestrado.git
cd Mestrado
```
Instalação de imagem ubuntu com ebpf
```
# A. Entre na pasta ebpf-host dentro do seu repositório local
cd ebpf-host/

# B. Construa a imagem localmente
sudo docker build -t ebpf-host:latest .
```
---

### 4. Compilar o Programa eBPF

O script `compile.sh` usa um **container nicolaka/netshoot como ambiente de build**, dispensando a instalação de ferramentas de compilação no host.Isso evita que você precise instalar localmente todas as dependências de eBPF (que podem ser pesadas ou conflitar) diretamente no seu sistema host.

```bash
# Se não estiver no diretório do lab:

chmod +x ./scripts/compile.sh
./scripts/compile.sh
```

<details>
<summary>O que o compile.sh faz?</summary>

Ele sobe um container Docker temporário que:
1. Instala `clang`, `llvm`, `libbpf-dev` e `gcc-multilib`.
2. Compila `xdp_monitor.c` gerando bytecode para a **máquina virtual BPF** (`-target bpf`).
3. Gera o arquivo objeto `xdp_monitor.o` no diretório atual.
4. Remove o container de build automaticamente (`--rm`).

</details>

**Saída esperada:**
```
Success! xdp_monitor.o created. 😱😱😱
```

---

### 5. Deploy da Topologia

```bash
sudo containerlab deploy -t topologia.yml --reconfigure
```

Isso irá:
- Criar três containers Linux (`gateway` , `atacante` e `sensor`).
- Configurar os IPs nas interfaces `eth1` de cada nó.
- Montar o `xdp_monitor.o` dentro do `gateway` em `/xdp_monitor.o`.
- Criar um barramento virtual através de uma bridge conectando as interfaces eth1 dos nós atacante, sensor e gateway.

Verifique se o lab está rodando:

```bash
docker ps --filter "label=containerlab=TE-eBPF"
```
```
docker ps --format "table {{.Names}}\t{{.Status}}" | grep clab
```

---


### 6. Verificar Conectividade Inicial

Antes de ativar o filtro XDP, confirme que os nós se comunicam normalmente:

```bash
docker exec clab-lab-ebpf-sensor ping -c 3 10.0.0.1
```

**Resultado esperado:** `0% packet loss`  

---

### 7. Executar script 

Instala as bibliotecas necessárias para o painel de visualização e configure o broker MQTT no Gateway:

  ```
  chmod +x ./scripts/setup.sh
  ./scripts/setup.sh
  ```

### 8. Ativar o Filtro XDP

8.1 Carregar e pinar o programa XDP

```
chmod +x scripts/load_xdp.sh
./scripts/load_xdp.sh xdp
```
--- 



### 📂 Estrutura do Projeto 

```
TE_eBPF/
├── topologia.yml       # Configuração do laboratório (Containerlab)
├── xdp_monitor.c       # Código eBPF otimizado (DDoS + IP Spoofing)
├── scripts/
│   ├── compile.sh      # Compila o xdp_monitor.c usando container
│   ├── setup.sh        # Configura dependências e rede
│   └── load_xdp.sh     # Ativa/Limpa o XDP no Gateway
├── dash/
│   └── dashboard.py    # Dashboard Analítico (PPS, Jitter, Drops)
└── metricas/
    └── xdp_dos.md      # Roteiro de testes detalhados

```

---

### 📚 Referências 

- [Documentação Oficial do eBPF](https://ebpf.io/what-is-ebpf/)
- [Documentação do Containerlab](https://containerlab.dev/quickstart/)
- [Tutorial XDP (kernel.org)](https://github.com/xdp-project/xdp-tutorial)
- [libbpf GitHub](https://github.com/libbpf/libbpf)
- [nicolaka/netshoot — Container de diagnóstico de rede](https://github.com/nicolaka/netshoot)
- [Tutorial de artigo ataque slow](https://github.com/gianluca2414/MQTT_SlowITe )
- [1] A. Tolay, *eBPF-Based Real-Time DDoS Mitigation for IoT Edge Devices*, Jul. 13, 2025. doi: 10.48550/arXiv.2508.00851
- [2] C. K. Dominicini, *Redes Programáveis com XDP/eBPF*, AVA da disciplina Redes Programáveis – TE em Redes I, Vila Velha, 2026.








