# Controle positivo das medidas de P1

- Sementes-piloto: [901, 902, 903, 904, 905] (descartaveis; grade 1-20 intocada)
- CLI sha256: `07b2464d2be93e3ad68f65d61bd841e4465fed34fc142b101b3e8b7d9229db7a`
- Veredito: **blind**

| Par | Celula | TVD medio | TVD max | Desacordo medio |
|---|---|---|---|---|
| A_vs_C | T=40,alpha=strict | 0.0000 | 0.0000 | 0.0000 |
| A_vs_C | T=40,alpha=lenient | 0.0000 | 0.0000 | 0.0000 |
| A_vs_C | T=160,alpha=strict | 0.0000 | 0.0000 | 0.0000 |
| A_vs_C | T=160,alpha=lenient | 0.0000 | 0.0000 | 0.0000 |
| A_vs_B_logged | T=40,alpha=strict | 0.5000 | 0.5000 | 1.0000 |
| A_vs_B_logged | T=40,alpha=lenient | 0.5000 | 0.5000 | 1.0000 |
| A_vs_B_logged | T=160,alpha=strict | 0.5000 | 0.5000 | 1.0000 |
| A_vs_B_logged | T=160,alpha=lenient | 0.5000 | 0.5000 | 1.0000 |
| A_vs_A_diff_seed | T=40,alpha=strict | 0.0000 | 0.0000 | 0.0000 |
| A_vs_A_diff_seed | T=40,alpha=lenient | 0.0000 | 0.0000 | 0.0000 |
| A_vs_A_diff_seed | T=160,alpha=strict | 0.0000 | 0.0000 | 0.0000 |
| A_vs_A_diff_seed | T=160,alpha=lenient | 0.0000 | 0.0000 | 0.0000 |

## Diagnostico

A vs C da 0.00 nas duas medidas em todas as 20 observacoes: o controle positivo principal nao separa. As contagens brutas de nu sao IDENTICAS entre A e C em toda celula e semente — nu nao le o sinal (BETTER/WORSE/UNCLEAR). A e C so diferem no sinal: mesma condicao {'env':'stable'}, mesma estrategia s_star, nenhum evento de vocabulario. Logo nu depende so de escopo e idade, e as duas medidas sao cegas a qualquer mundo que mova apenas a trajetoria. A estrategia vencedora e sempre {'s_star'} — ha um unico alvo s_star, entao o primeiro componente do parecer nao pode discordar; o desacordo herda so o resumo de nu. A vs B logged separa (TVD max = 0.5000), e o controle negativo A vs A (semente vizinha) da TVD max = 0.0000.

## Contagens brutas de nu — A vs C, T=40, alpha=strict

| Semente | Mundo | APPLICABLE | OUT_OF_SCOPE | AGED | UNEVALUABLE |
|---|---|---|---|---|---|
| 901 | A | 40 | 0 | 0 | 0 |
| 901 | C | 40 | 0 | 0 | 0 |
| 902 | A | 40 | 0 | 0 | 0 |
| 902 | C | 40 | 0 | 0 | 0 |
| 903 | A | 40 | 0 | 0 | 0 |
| 903 | C | 40 | 0 | 0 | 0 |
| 904 | A | 40 | 0 | 0 | 0 |
| 904 | C | 40 | 0 | 0 | 0 |
| 905 | A | 40 | 0 | 0 | 0 |
| 905 | C | 40 | 0 | 0 | 0 |
