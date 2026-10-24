for defesa in off iptables stateful dfa; do
    for cenario in legitimo atacante todos; do
        ./rodar_experimento.sh --$defesa --$cenario
    done
done
