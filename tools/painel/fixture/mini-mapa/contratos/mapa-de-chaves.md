# Mapa de chaves — fixture do grafo

6 chaves em 4 pacotes.

## A · Fundação

| Chave | Provê (tipo) | Injeta | Dono | Card. |
|---|---|---|---|---|
| `mini.config` | `Config` | — | mini | única |
| `mini.store` | `Store` | `mini.config` | mini | única |

## B · Runtime

| Chave | Provê (tipo) | Injeta | Dono | Card. |
|---|---|---|---|---|
| `mini.learn` | `Learning` | `mini.store`, `mini.config` | mini | única |
| `mini.view` | `ViewModel` — leitura (`resumo` \| `detalhe`) | `mini.learn` | mini | única |

## C · Borda

| Chave | Provê (tipo) | Injeta | Dono | Card. |
|---|---|---|---|---|
| `mini.edge` | `Edge` | `mini.view` | mini | única |
| `mini.extra` | `Extra` | — | mini | única |

## Pacotes propostos

| Pacote | Chaves |
|---|---|
| `mini-kernel` | `mini.config` · `mini.edge` |
| `mini-store` | `mini.store` · `mini.learn` |
| `mini-outros` | `mini.view` · `mini.extra` — *provider de `mini.config`, não chave nova* |
| `mini-fixtures` | *(double de teste — não provê chave nenhuma, de propósito)* |
