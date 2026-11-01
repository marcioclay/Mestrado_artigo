# Comandos para Todos os Cenários por Defesa

## 1. Defesa: OFF (Baseline / Sem Defesa)

### Cenário Legítimo

```bash
./rodar_experimento.sh --off --legitimo --duracao 600
```

### Cenário Atacante

```bash
./rodar_experimento.sh --off --atacante --duracao 600
```

### Cenário Todos (Misto)

```bash
./rodar_experimento.sh --off --todos --duracao 600
```

---

## 2. Defesa: IPTables (Netfilter)

### Cenário Legítimo

```bash
./rodar_experimento.sh --iptables --legitimo --duracao 600
```

### Cenário Atacante

```bash
./rodar_experimento.sh --iptables --atacante --duracao 600
```

### Cenário Todos (Misto)

```bash
./rodar_experimento.sh --iptables --todos --duracao 600
```

---

## 3. Defesa: Stateful (Heurístico por Contagem)

### Cenário Legítimo

```bash
./rodar_experimento.sh --stateful --legitimo --duracao 600
```

### Cenário Atacante

```bash
./rodar_experimento.sh --stateful --atacante --duracao 600
```

### Cenário Todos (Misto)

```bash
./rodar_experimento.sh --stateful --todos --duracao 600
```

---

## 4. Defesa: DFA (Abordagem Baseada em Autômato)

### Cenário Legítimo

```bash
./rodar_experimento.sh --dfa --legitimo --duracao 600
```

### Cenário Atacante

```bash
./rodar_experimento.sh --dfa --atacante --duracao 600
```

### Cenário Todos (Misto)

```bash
./rodar_experimento.sh --dfa --todos --duracao 600
```

---

## Observação

Caso também esteja utilizando a opção `stateless` nos testes, basta substituir a flag de defesa por `--stateless`, mantendo a mesma estrutura dos comandos.

### Exemplo com Stateless

```bash
./rodar_experimento.sh --stateless --todos --duracao 600
```
