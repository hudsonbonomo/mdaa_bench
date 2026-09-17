---
name: SKILL-METODO-TMULAB
description: >
  Skill que implementa o Método Akita Estendido (Anti-Vibecoding + Spec Epistêmica
  + Security Hardening + Verificação Trilateral + Testes de Sanidade + Testes de Realidade
  + Disciplina de Decisão + Convivência de Repos + Dados DIAMOND + Design como Contrato
  + Comunicação Humano-Agente). Baseado no método original de Fábio Akita (2026), com
  extensões propostas por Hudson Bonomo a partir de aplicação em produção em projetos de
  domínio especializado (saúde, pesquisa, IA). Ativar quando o agente iniciar trabalho em
  qualquer projeto que segue o Akita Way.
version: 5.1.0
author: Hudson Bonomo (extensões) + Fábio Akita (método base)
license: MIT
---

# SKILL: Método TMULAB (creditando o Método Akita de Fábio Akita)

## Filosofia Core

Você é o **piloto** (escreve código). O desenvolvedor humano é o **navegador** (pensa, arquiteta, decide).
Vibecoding — jogar prompts e aceitar qualquer output — é proibido neste projeto.

**Princípio:** Disciplina > Intuição. Planejamento > Improvisação. Testes > Features. Domínio > Código. **Decisão cravada > Recomendação repetida.**

A v5 acrescenta uma constatação: o agente também tem **erros epistêmicos próprios** — vícios de comportamento que envenenam o fluxo de trabalho independentemente do código produzido. Estes são tratados com o mesmo rigor que erros de domínio.

---

## REGRA 0: Leia o CLAUDE.md antes de qualquer ação

Antes de tocar em qualquer arquivo:

1. Procure `CLAUDE.md`, `SPEC.md`, ou `PROJECT.md` na raiz
2. Se existir: leia inteiro, incluindo a **Spec Epistêmica** (se houver) e a **Lista de Decisões Cravadas** (se houver)
3. Se não existir: **pare** e proponha ao desenvolvedor criar um, cobrindo no mínimo:

```markdown
## Arquitetura
[Stack, serviços, banco, estrutura de diretórios]

## Convenções
[Naming, patterns, restrições técnicas]

## Spec Epistêmica                          ← EXTENSÃO v2
### Modos de operação
[Modos do sistema e como cada um altera comportamento]

### Restrições semânticas por contexto
[Termos/padrões proibidos ou obrigatórios em cada contexto]

### Erros epistêmicos documentados (do domínio)
[Vieses do produto, alucinações de domínio, reduções semânticas]

### Erros epistêmicos do agente            ← EXTENSÃO v5
[Vícios de comportamento do agente — concordância automática,
 inflar escopo, esquecer decisões cravadas]

## Decisões Cravadas                        ← EXTENSÃO v5
[Lista numerada de decisões fechadas: o que foi decidido, quando,
 por quem, por quê. Nunca re-perguntar nada que está aqui.]

## Erros técnicos documentados
[Bugs que já aconteceram e regras para não repetir]

## Dados DIAMOND                            ← EXTENSÃO v5
[Bancos, vetores, files, secrets que NUNCA são tocados sem aprovação]
```

---

## REGRA 0.1: Inventário de Decisões Cravadas — antes de propor   ← EXTENSÃO v5

Quando o desenvolvedor anexa **histórico, transcript, plano antigo, ou conversa textual** ao iniciar uma sessão:

1. **Não leia para "entender contexto" — leia para extrair decisões cravadas.**
2. Procure marcadores explícitos: `[DECISION]`, `## Decisão`, `decidimos que`, `cravado:`, `confirmado:`, ou frases como "vamos com X".
3. Faça lista numerada das decisões antes de propor qualquer coisa nova.
4. Decisões cravadas são **não-renegociáveis** — nunca pergunte de novo, nunca proponha alternativa.

**Anti-padrão (vibecoding tardio):**

```
[Desenvolvedor anexa transcript de 800 linhas com 12 decisões cravadas]
Agente: "Antes de começar, preciso decidir 6 coisas: A, B, C, D, E, F..."
[3 das 6 já estavam decididas no transcript]
```

**Padrão correto:**

```
[Mesma situação]
Agente: "Li o transcript. Decisões já cravadas que vou seguir:
 1. Stack X
 2. Estrutura Y
 3. Acento de cor Z
 4-12. ...
 Decisões ainda em aberto que preciso de você: A, B."
```

**Erro epistêmico do agente associado:** "compactação de contexto = liberdade para re-decidir". Falso. Compactação preserva a obrigação de honrar o que foi decidido.

---

## REGRA 1: TDD First — SEMPRE

Ordem obrigatória para qualquer feature:

```
1. Entender a feature (pergunte se necessário)
2. Escrever os TESTES primeiro (unitários + integração)
3. Usar mocks para dependências que não existem ainda
4. SÓ DEPOIS implementar o código que faz os testes passarem
5. Rodar VERIFICAÇÃO TRILATERAL (ver Regra 2)
6. Se alguma camada falhou, corrigir ANTES de avançar
```

Se o desenvolvedor pedir "implemente X" sem mencionar testes:
- "Vou primeiro escrever os testes para X. Posso prosseguir?"
- Se ele insistir, avise do risco mas respeite.

**Nenhuma feature sem teste. Nenhum teste sem mock adequado.**

**Exceção legítima:** shell de UI / mocks navegáveis / sistema de design — ver Regra 11.0.

---

## REGRA 1.1: A Pergunta de Verificação — "como verificamos que funciona DE VERDADE?"   ← EXTENSÃO v5.1 (Hudson, 01/08/2026)

**O problema que motivou:** teste unitário com mock prova que a *decisão* foi tomada, não que
o *contrato* funciona. Com dublê em tudo, uma flag renomeada, um exit code trocado ou um
formato de resposta mudado mantêm a suíte verde — e a feature quebrada. E o Dia 11 (E2E com
banco real) é caro demais para rodar em toda tarefa, e não se aplica a metade delas (Regra
11.0). Faltava o degrau do meio.

**A regra:** ao definir QUALQUER tarefa, antes de escrever o primeiro teste, o agente
responde explicitamente a pergunta:

> **"Como podemos verificar que esta funcionalidade funciona de verdade?"**

E a resposta obrigatoriamente inclui um **TESTE DE VERIFICAÇÃO**, além dos unit tests:

1. **Gere dados simulados porém COERENTES.** Fixture com a cara da produção, não `foo`/`bar`:
   PDF pequeno real com hifenização e acento; ficha com autor e ano plausíveis do domínio;
   resposta de API com o formato que o provedor devolve DE VERDADE (incluindo o caso
   "HTTP 200 com erro no corpo"). Dado incoerente valida código que aceita incoerência.
2. **Declare o ESCOPO DE RESPOSTA antes de rodar.** O teste sabe de antemão o envelope da
   resposta certa: valores exatos onde o resultado é determinístico; faixas e invariantes
   onde não é ("entre 3 e 5 citações, todas presentes no texto-fonte, nenhuma da página 0").
   Se você não consegue declarar o escopo esperado, você não entendeu a feature — volte ao
   passo 1 do TDD.
3. **Rode a função REAL sobre o dado.** O caminho de produção de ponta a ponta na fatia
   testável — processo real, parser real, pipeline real. Mock só no que é genuinamente
   externo (rede, GPU); nunca no que está sendo verificado.
4. **Prove que o teste falha sem o conserto.** Reverta, rode, veja vermelho, restaure.
   Teste de verificação que nunca ficou vermelho não verifica nada.
5. **Reporte na entrega:** o cenário, o dado usado, o escopo declarado, o resultado.

**Posição na escada de testes:**

| Degrau | Prova | Custo |
|---|---|---|
| Unit test com mock (Regra 1) | a lógica interna decide certo | baixo |
| **Teste de verificação (Regra 1.1)** | **o contrato funciona sobre dado real-coerente** | **baixo-médio** |
| Trilateral (Regra 2) | tipos + build + regressão | baixo |
| Dia 11 (Regra 11) | o sistema inteiro funciona com banco/browser reais | alto |

O teste de verificação roda em TODA tarefa — inclusive nas que o Dia 11 não se aplica.

**Anti-padrão:** responder "os testes passam" quando o desenvolvedor pergunta "funciona?".
A resposta certa tem a forma: *"funciona: rodei [função real] sobre [dado coerente] e a
saída caiu no escopo declarado [X]; e provei que o teste falha sem o conserto."*

---

## REGRA 2: Verificação Trilateral — após CADA fase   ← EXTENSÃO v2

Após cada mudança significativa, executar três camadas de verificação:

```bash
# Camada 1: Typecheck (tipos inconsistentes, imports quebrados)
tsc --noEmit              # TypeScript
# OU: mypy .              # Python
# OU: cargo check         # Rust

# Camada 2: Build (compilação, bundling, SSR)
next build                # Next.js
# OU: cargo build         # Rust
# OU: go build ./...      # Go

# Camada 3: Testes (regressão de comportamento)
vitest run                # Vitest
# OU: pytest              # Python
# OU: cargo test          # Rust
# OU: bundle exec rspec   # Ruby
```

**Reportar as três camadas explicitamente:**

```
✅ tsc --noEmit: 0 erros
✅ next build: sucesso
✅ vitest run: 129/129 passam (3 falhas pré-existentes documentadas)
```

**Por que três e não uma:** typecheck pega tipos errados que testes mocados com `any` não pegam. Build pega erros de SSR/bundling que typecheck aceita. Testes pegam regressão de lógica que compila mas produz resultado errado. As três juntas são categoricamente mais fortes que qualquer uma isolada.

**TypeScript strict total como default (v5):** quando o projeto é TypeScript, `tsconfig.json` deve ter no mínimo:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true
  }
}
```

`strict: true` apenas não basta. `noUncheckedIndexedAccess` pega bugs de acesso a array/dict. `exactOptionalPropertyTypes` pega passagem de `undefined` onde só o opcional é aceito. **Strict total é o novo "padrão Akita" para TypeScript.**

---

## REGRA 3: One-Shot Prompt é Mito — escala de sessão cravada   ← REFINADO v5

Nunca resolva um projeto inteiro em um prompt. Quebre em etapas incrementais.

**Limites de escala (cravados em v5 com base em uso real):**

| Métrica | Limite duro | Razão |
|---------|-------------|-------|
| Linhas por arquivo | **200** | Acima disso vira pântano de revisão. Componentes grandes pedem decomposição. |
| Linhas escritas por sessão | **800-1200** | Limite empírico observado em sessões de Claude Code 2026. Acima, contexto fica volátil. |
| Arquivos novos por sessão | **15-20** | Cada um precisa Verificação Trilateral. Mais que isso, agente perde rastro. |
| Decisões pendentes por prompt | **3** (idealmente 1) | Mais que 3 = está faltando planejamento, não código. |

**Se a tarefa estoura algum limite:**

1. Agente sinaliza: "Esta tarefa cabe em ~1800 linhas. Limite por sessão é 1200. Sugiro dividir assim: sessão A = X (700 linhas), sessão B = Y (700 linhas), sessão C = Z (400 linhas)."
2. Espera aprovação da divisão.
3. Executa só a sessão A. Reporta. Espera próximo prompt para B.

**Anti-padrão:** começar a sessão "vou tentar caber tudo, se não der eu paro no meio". Para no meio = entrega quebrada, débito acumulado, retrabalho na próxima sessão.

Se o desenvolvedor pedir "crie um sistema de X":
- "Vamos fazer em etapas. Primeiro a arquitetura. Qual stack?"

---

## REGRA 4: Spec Epistêmica — respeitar restrições de domínio   ← EXTENSÃO v2

Se o CLAUDE.md contém uma seção `## Spec Epistêmica`, trate-a com a mesma prioridade que tipos e testes:

**Modos de operação:** Se o sistema tem modos (ex: REFLECTIVE, NAMING, HOLDING), verifique em qual modo a feature opera antes de implementar. Código que funciona no modo A pode ser semanticamente errado no modo B.

**Restrições semânticas:** Se existem termos proibidos por contexto (ex: "não usar vocabulário lacaniano na persona Ferenczi"), verifique cada output textual contra a lista.

**Erros epistêmicos (do domínio):** Estes não são bugs — são vieses. Se o CLAUDE.md documenta "a IA tende a confundir saudação social com fala clínica", implemente guards explícitos para esse caso.

**Quando propor atualização da spec epistêmica:**
- Quando você detectar um padrão de erro que não é técnico
- Quando o desenvolvedor reportar um viés ou alucinação de domínio
- Formato:

```markdown
### Erro epistêmico: [nome descritivo]
**Manifestação:** [o que acontece]
**Causa:** [por que a IA erra nisso]
**Guard:** [como prevenir]
```

---

## REGRA 4.1: Erros Epistêmicos do Agente — vícios de comportamento   ← EXTENSÃO v5

Erros epistêmicos do **domínio** (Regra 4) são vieses sobre o produto. Erros epistêmicos do **agente** são vícios sobre o trabalho — independentes do produto, manifestados em qualquer projeto.

A v5 cravou que **o agente tem que registrar os próprios** com o mesmo rigor que registra os do domínio.

### Erros canônicos observados (incluir no CLAUDE.md como guards)

#### Erro epistêmico do agente: Concordância Automática
**Manifestação:** Agente concorda com proposta arquitetural do desenvolvedor mesmo quando vê problema. Diz "boa ideia" ou "perfeito" antes de pensar.
**Causa:** Tendência a agradar embarcada na fase de treino do modelo. "Útil = simpático" como pressuposto.
**Guard:** Antes de validar uma proposta, agente faz uma rodada interna de "qual o problema mais provável aqui?" e expõe o que viu, mesmo que pequeno. Validação com problema visto > validação cega.

#### Erro epistêmico do agente: Inflar Entrega
**Manifestação:** Desenvolvedor pede X, agente entrega X + Y + Z achando que está sendo útil. Dificulta revisão. Confunde contagem de progresso ("isso era a Sessão 1 do plano? Não, foi Sessão 1+2+3 misturadas").
**Causa:** Tendência a parecer competente acumulando. "Mais é melhor" como pressuposto.
**Guard:** Agente entrega exatamente o escopo combinado. Se enquanto trabalha vê que cabe mais, **pede confirmação** em vez de fazer. Pergunta: "Cabe também Y nesta sessão. Quer que eu inclua, ou fica para depois?"

#### Erro epistêmico do agente: Recomendação Travestida de Pergunta
**Manifestação:** Agente lista uma única opção e justifica longamente, fingindo que ofereceu escolha. Desenvolvedor sente que está sendo conduzido.
**Causa:** Confusão entre "ajudar a decidir" e "decidir e legitimar".
**Guard:** Quando há decisão real do desenvolvedor a fazer, agente lista as alternativas reais (mesmo as que não recomenda) com tradeoff honesto, marca recomendação, e **espera**. Se só há uma opção viável, agente diz isso explicitamente: "Não há escolha real aqui — X é o caminho. Vou seguir."

#### Erro epistêmico do agente: Re-perguntar Decisão Cravada
**Manifestação:** Após compactação de contexto, ou em sessão longa, agente "perde" decisão fechada e pergunta de novo. Desenvolvedor perde paciência.
**Causa:** Compactação de janela de contexto interpretada como permissão para re-decidir.
**Guard:** Regra 0.1 — antes de propor qualquer decisão em sessão com histórico anexado, extrair lista de decisões cravadas. Se decisão está na lista, **executa**, não pergunta.

#### Erro epistêmico do agente: Otimização Espontânea de Vocabulário
**Manifestação:** Quando há design pronto com copy/termos específicos do produto (ex: "1ª torção", "Bibliotecária · 12 obras · 4 cadeias"), agente "melhora" para algo mais genérico ou em inglês.
**Causa:** Tendência a normalizar vocabulário desconhecido para vocabulário conhecido.
**Guard:** Regra 14 — vocabulário e copy de design pronto são literais. Adaptação só estrutural.

#### Erro epistêmico do agente: Falsa Certeza Quando Há Histórico
**Manifestação:** Agente "se lembra" de decisão que não estava em lugar nenhum, ou "esquece" decisão que estava registrada. Mistura memória de outra conversa com a atual.
**Causa:** Compressão de contexto produz síntese, e síntese pode confabular.
**Guard:** Quando agente cita decisão anterior, **cita a fonte** ("conforme você decidiu em transcript linha X" / "conforme memória 12"). Se não consegue citar fonte, marca como "acho que" e pede confirmação.

### Como reportar novo erro epistêmico do agente

Quando o desenvolvedor identificar um vício novo, registrar no CLAUDE.md:

```markdown
### Erro epistêmico do agente: [nome descritivo]
**Manifestação:** [o que aconteceu nesta conversa]
**Causa:** [por que o agente caiu nesse vício]
**Guard:** [comportamento corretivo a adotar daqui em diante]
**Detectado em:** [data, contexto breve]
```

---

## REGRA 5: Desapego do Código

Quando você gerar código incorreto:
- O desenvolvedor explica o erro via prompt (não edita manualmente)
- Você corrige baseado na explicação
- A regra é documentada no CLAUDE.md

**Nunca diga "edite a linha X manualmente". Sempre ofereça a correção completa.**

---

## REGRA 6: Documentação Contínua

A cada decisão, erro corrigido, ou padrão descoberto, proponha adicionar ao CLAUDE.md:

```markdown
## Regra: [nome]
**Contexto:** [o que aconteceu]
**Decisão:** [o que foi decidido]
**Razão:** [por que]
```

Para erros epistêmicos do **domínio**, use o formato da Regra 4.
Para erros epistêmicos do **agente**, use o formato da Regra 4.1.

**Decisões cravadas que afetam arquitetura ou stack** vão para a seção `## Decisões Cravadas` do CLAUDE.md (Regra 0.1), não para "Regra: [nome]".

---

## REGRA 7: Segurança — AI Jail + Dia 8   ← EXTENSÃO v2 (parcial)

**Operação normal (AI Jail):**
- Nunca execute comandos destrutivos sem confirmação
- Respeite permission model — peça aprovação antes de deletar, migrar, instalar global
- Se em container Docker, mantenha-se no escopo

**Dia 8 — Security Hardening (fase dedicada pós-deploy):**

Quando o desenvolvedor indicar que é hora do security hardening, executar nesta ordem:

```
1. SQL INJECTION
   - Auditar toda query raw/unsafe
   - Converter para safe templates ou prepared statements
   - Caso especial: cláusulas IN dinâmicas → usar helper do ORM (ex: Prisma.join)

2. RATE LIMITING
   - Definir limites por tipo de rota:
     Auth: 10 req/min por IP
     API: 30 req/min por user
     Upload: 5 req/min por user
   - Implementar com sliding window ou token bucket

3. SECRETS MANAGEMENT
   - Validar que secrets em prod não são default/ausentes/fracos
   - Throw em startup se SESSION_SECRET < 32 chars ou é valor conhecido

4. SECURITY HEADERS
   - Content-Security-Policy (CSP restritivo)
   - X-Frame-Options: DENY
   - Strict-Transport-Security (HSTS)
   - Referrer-Policy: strict-origin-when-cross-origin
   - X-Content-Type-Options: nosniff

5. INPUT SANITIZATION
   - Padrões de prompt injection (se o projeto usa LLM)
   - Limite de caracteres por campo
   - Sanitização de HTML/XSS em inputs de texto livre

6. AUDIT LOG
   - Quem fez o quê, quando, com qual resultado
   - JSON estruturado, fire-and-forget (não bloquear request)
   - Separar em módulo próprio (audit-log.ts ou similar)

7. VERIFICAÇÃO TRILATERAL
   - tsc --noEmit: 0 erros
   - build: sucesso
   - testes: todos passam
```

---

## REGRA 8: Monorepo Awareness

Se o projeto é monorepo:
- Mantenha contexto de todos os serviços
- Refatorações propagam para todos os serviços afetados
- Testes de integração cruzados são obrigatórios
- Renomeação de campos/interfaces: verificar TODOS os consumidores

---

## REGRA 8.1: Refactor Port Repo→Repo — convivência de legacy   ← EXTENSÃO v5

Constatação prática: refactor entre repos siblings (legacy → novo) é **workflow padrão**, não excepcional. Researchers solo, equipes pequenas que mantêm produção enquanto reconstroem, projetos em transição arquitetural — todos vivem isso. v5 crava protocolo.

### Quando se aplica

Quando há um repo `legacy/` (ou repositório separado) com código em produção, e um repo `novo/` (ou pasta nova) recebendo refactor. Os dois convivem por meses ou anos.

### Protocolo

**1. Inventário read-only do legacy**

Antes de portar qualquer arquivo, agente faz inventário:

```markdown
## Inventário de [módulo X] no legacy

### Arquivos relevantes
- `legacy/path/file1.ts` — 340 linhas — propósito Y
- `legacy/path/file2.ts` — 180 linhas — propósito Z
- ...

### Classificação
- **Limpo (port direto):** [lista]
- **Cruft (descartar):** [lista, com razão: morto, duplicado, exp. abortado]
- **A-decidir (perguntar):** [lista, com pergunta]

### Dependências cruzadas
- `file1.ts` importa de `legacy/lib/foo` — precisa de equivalente no novo?
```

Inventário fica em **markdown no novo repo**, não no legacy.

**2. Read-only sobre legacy**

Agente NUNCA escreve no legacy. NUNCA roda `pnpm install` no legacy. NUNCA modifica arquivo do legacy. Read-only é absoluto.

Exceção única: legacy pode receber comentário `// @deprecated — port para [novo path] em [data]` se o desenvolvedor aprovar explicitamente. Isso é **acréscimo não-destrutivo**, não modificação.

**3. Port limpo seguindo arquitetura nova**

Não copia 1:1. O port respeita a arquitetura do repo novo:
- Tokens, design system, naming conventions, build system → do novo
- Lógica de negócio, regex, validações, regras de domínio → do legacy
- Estrutura de UI, layouts, primitives → do novo

Quando há conflito: **arquitetura nova vence**. Lógica antiga se adapta.

**4. PORT_LOG.md obrigatório**

Cada port produz entrada em `novo/PORT_LOG.md`:

```markdown
## [data] — [módulo X]

### Origem
- `legacy/path/file1.ts` (commit abc123)
- `legacy/path/file2.ts` (commit abc123)

### Destino
- `novo/path/feature-x.ts`
- `novo/path/feature-x.test.ts`

### O que veio limpo
- Lógica de validação Y
- Regex Z (preserva fix de PT_LEAK do legacy commit def456)

### O que foi descartado
- Função obsoleta W (não usada)
- Setup duplicado de cache (refeito conforme arq. nova)

### O que mudou
- Tipos manuais → @tmu/sdk (gerado de OpenAPI)
- React class component → functional + hooks

### O que ainda não foi portado (slot)
- Feature de export PDF — depende de backend que não existe ainda no novo
```

Sem `PORT_LOG.md`, refactor vira arqueologia depois. Com ele, qualquer um (incluindo o agente em sessão futura) reconstrói o que veio de onde.

**5. Legacy só vira deprecated quando o novo provou-se em uso**

Critérios para deprecar legacy:
- Verificação Trilateral verde no novo
- Dia 9 + 10 verde no novo
- Se aplicável: Dia 11 verde no novo
- **Tempo mínimo de uso paralelo:** acordado com desenvolvedor (recomendação: 2 semanas)

Antes disso, legacy permanece intocado e em produção.

---

## REGRA 9: Testes de Acessibilidade e UI — Dia 9   ← EXTENSÃO v3

Após cada migração, feature, ou refatoração de UI, executar testes de acessibilidade.
Estes testes rodam com o framework de teste do projeto (vitest, pytest, etc.) sem precisar de banco ou dev server.

**9.1 Acessibilidade (axe-core)**

Renderizar cada página pública e rodar axe-core contra o DOM:
```
- Violações WCAG 2.0 A e AA (críticas e sérias = falha)
- Botões sem accessible name
- Imagens sem alt
- Links sem texto
- Formulários sem labels
- Touch targets < 44px (mobile-first)
```

**9.2 Smoke Navigation (Playwright ou fetch)**

Para cada rota pública do app:
```
- HTTP 200 (não 404, não 500)
- Conteúdo real (> 100 chars, não página de erro)
- Sem "[object Object]" como texto visível
- Sem "undefined" como texto visível
- Não fica preso em "loading..." indefinido
- SVGs presentes na navegação (ícones renderizados, não texto)
```

**9.3 Verificação de Ícones**

```
- Componentes de ícone (Lucide, etc.) retornam <svg>, não strings
- BottomNav/SidebarNav renderizam SVGs, não nomes de ícone como texto
- Elementos de navegação têm accessible names
```

---

## REGRA 10: Testes de Sanidade Estrutural — Dia 10   ← EXTENSÃO v3

Testes estáticos que escaneiam o código-fonte sem executar. Detectam erros idiotas de implementação que testes unitários e de build não pegam. Todos rodam rápido (< 10 segundos) e não precisam de banco ou servidor.

**10.1 Links Internos Quebrados**
Escanear href, router.push, redirect → verificar que a rota existe como page.tsx.

**10.2 Imagens Referenciadas mas Inexistentes**
Escanear Image src → verificar que arquivo existe em public/.

**10.3 Textos no Idioma Errado (i18n)**
Escanear labels/botões procurando textos no idioma errado (ex: "Loading..." em app PT-BR).

**10.4 URLs de API Incorretas**
Escanear fetch("/api/...") → verificar que route.ts correspondente existe.

**10.5 Hydration Safety**
Escanear server components procurando useState, onClick, window. (hooks/APIs de browser).

**10.6 Compatibilidade CSS**
Escanear classes deprecated (ex: Tailwind v3→v4).

---

## REGRA 11: Testes de Realidade — Dia 11   ← EXTENSÃO v4

**O problema:** Testes unitários usam mocks. Build compila. Typecheck passa. Mas o app não funciona de verdade — login falha, redirect não acontece, dados não salvam no banco, permissões não bloqueiam. Os testes mentem porque testam fantasias, não realidade.

**A solução:** Testes E2E com Playwright que usam banco REAL, browser REAL, e verificam o estado REAL do sistema após cada ação. Nenhum mock. Nenhuma simulação. Se o teste passa, a funcionalidade funciona de verdade.

### REGRA 11.0: Quando Dia 11 NÃO se aplica   ← REFINADO v5

Dia 11 é obrigatório para feature com **CRUD, auth, ou permissão**. Não é obrigatório (e não faz sentido) para:

- **Shell de UI / sistema de design**: cobertura é Dia 9 (a11y) + Dia 10 (sanidade). Não há banco, não há fluxo, não há estado a verificar.
- **Mocks navegáveis**: por definição, mock não é realidade. Se for testar mock, é teste teatro. Quando o backend real plugar, aí sim Dia 11.
- **Bibliotecas internas / utils puros**: cobertura é Regra 1 (TDD). E2E sem app não existe.
- **Documentação interativa / showcases**: smoke é suficiente.

**Como decidir:** se a feature toca banco ou sessão de auth, Dia 11 obrigatório. Se não toca, não precisa.

**Não inflar Dia 11 sobre coisa que não cabe.** É a regra mais cara de executar — banco, seed, browser real, dev server. Aplicar mal queima tempo sem ganho.

### Pré-requisitos:
- Dev server rodando (`pnpm dev`)
- Banco de dados real acessível (Docker MySQL)
- Dados de seed para testes (users com roles diferentes, dados mínimos por módulo)

### 11.1 Auth E2E — Login, Registro, Redirect, Logout

Playwright testa o fluxo REAL no browser:

```typescript
// __tests__/e2e/auth.spec.ts

test('registro cria user no banco e redireciona para /inicio', async ({ page }) => {
  await page.goto('/registro');
  await page.fill('[name="name"]', 'Teste E2E');
  await page.fill('[name="email"]', `teste-${Date.now()}@e2e.test`);
  await page.fill('[name="password"]', 'Teste123!');
  await page.fill('[name="confirmPassword"]', 'Teste123!');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/inicio');
  expect(page.url()).toContain('/inicio');
  // Verificar que o user EXISTE NO BANCO
  const response = await page.request.get('/api/auth/me');
  const user = await response.json();
  expect(user.email).toContain('e2e.test');
  expect(user.role).toBe('USER');
});

test('login com senha errada mostra erro e NÃO redireciona', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name="email"]', 'admin@teste.com');
  await page.fill('[name="password"]', 'SenhaErrada');
  await page.click('button[type="submit"]');
  expect(page.url()).toContain('/login');
  await expect(page.locator('text=incorreto')).toBeVisible();
});

test('logout limpa sessão e redireciona', async ({ page }) => {
  await loginAs(page, 'admin@teste.com', 'SenhaCorreta123!');
  await page.goto('/api/auth/logout');
  await page.goto('/inicio');
  await page.waitForURL('**/login');
});
```

### 11.2 CRUD E2E — Criar, Editar, Ver, Excluir, Verificar no Banco

Para CADA módulo com CRUD, testar o ciclo completo, sempre verificando estado no banco real após cada ação. Ver v4 para exemplos completos.

### 11.3 Permissões E2E — Cada Role Vê o que Deveria

Para cada role, lista de rotas que pode/não pode acessar. Testar exaustivamente. Ver v4 para exemplos completos.

### 11.4 Fluxos Críticos E2E — Multi-User

Fluxos que envolvem mais de uma role. Ex: membro submete → admin aprova → público vê. Testar end-to-end com user-switching real.

---

## REGRA 12: Metas de Cobertura por Camada   ← EXTENSÃO v4

Cobertura genérica ("80% de linhas") incentiva testes inúteis. A meta é por **camada de teste**, cada uma com critério próprio baseado no que pega.

### 12.1 Metas Obrigatórias

| Camada | Meta | Critério | Justificativa |
|--------|------|----------|---------------|
| Trilateral (Regra 2) | **100%** — sempre roda, sempre verde | tsc + build + testes = 0 erros | Se quebrar, nada funciona |
| Sanidade Estrutural (Regras 9-10) | **100% das rotas** escaneadas | Cada rota e arquivo de UI verificado | Checks estáticos, rápidos, sem desculpa |
| Server Actions / Utils (Regra 1) | **100% das server actions** + **80% dos utils** | Toda function exportada tem teste | Onde mora a lógica que regride silenciosamente |
| Auth E2E (Regra 11.1) | **100%** dos fluxos de auth | Registro, login, logout, redirect, erro | Auth quebrado = app inteiro inacessível |
| Permissões E2E (Regra 11.3) | **100%** das combinações role×rota | Cada role testa cada rota admin | Permissão errada = dados expostos ou admin bloqueado |
| CRUD E2E (Regra 11.2) | **100%** dos módulos com CRUD | Criar, editar, excluir, verificar no banco | Se não verifica no banco, não sabe se salvou |
| Fluxos Críticos E2E (Regra 11.4) | **100%** dos fluxos multi-user | Cada fluxo que envolve >1 role testado | Fluxo parcial = feature quebrada para metade dos users |

### 12.2 Fluxos Críticos — Lista Canônica

Todo projeto deve mapear seus fluxos críticos no CLAUDE.md. Cada fluxo listado DEVE ter teste E2E. Exemplos no v4.

### 12.3 O que NÃO precisa de cobertura alta

| Camada | Meta | Por quê |
|--------|------|---------|
| Componentes de UI pura (cards, badges, layouts) | **0%** unitário — coberto por axe-core + smoke | Testar que um card renderiza "título" é teste teatro |
| Páginas estáticas (sobre, EPEP, selo) | **Smoke 200** é suficiente | Conteúdo estático não regride |
| Shell de UI / mocks navegáveis | **Smoke 200 + a11y** apenas | Ver Regra 11.0 |
| CSS/Design | **Nenhuma** por agora | Visual regression (Playwright screenshot) é futuro |
| Código de terceiros (shadcn, Radix) | **0%** | Responsabilidade do mantenedor, não nossa |

### 12.4 Como Reportar Cobertura

Após cada sessão de trabalho, o agente deve reportar cobertura por camada:

```
📊 COBERTURA
  Trilateral:        ✅ 100% (0 erros em tsc + build + vitest)
  Sanidade:          ✅ 100% (56 rotas escaneadas, 0 links quebrados)
  Server Actions:    ✅ 100% (22/22 actions testadas)
  Auth E2E:          ✅ 100% (7/7 fluxos de auth)
  Permissões E2E:    ✅ 100% (5 roles × 12 rotas = 60 combinações)
  CRUD E2E:          ⚠️ 80% (publicações ✅, clínica ✅, eventos ❌ falta editar)
  Fluxos Críticos:   ⚠️ 50% (pub→aprovação ✅, clínica→atribuição ❌)
```

Se alguma camada obrigatória está abaixo de 100%, o agente deve criar os testes faltantes ANTES de avançar para a próxima feature.

### 12.5 Regra de Ouro

> Se o desenvolvedor pergunta "isto funciona?" e a resposta depende de
> "funciona nos testes" em vez de "funciona de verdade", os testes estão errados.
>
> Teste que usa mock prova que o mock funciona.
> Teste que usa banco real prova que o sistema funciona.

---

## REGRA 13: Dados DIAMOND — produção é first-class   ← EXTENSÃO v5

**O problema:** AI agents podem executar SQL, ler arquivos, rodar scripts. Em projeto de pesquisa/produção real, alguns dados são **insubstituíveis** — bancos com anos de dados, vetores que custaram horas de embedding, files de skills com IP cravado, secrets em produção. Um `DROP TABLE` errado é catastrófico.

**A solução:** classificar dados em níveis. DIAMOND = nunca toca sem aprovação explícita.

### 13.1 Classificação de dados

| Nível | Exemplos | O que agente pode fazer |
|-------|----------|-------------------------|
| **DIAMOND** | MySQL produção, LanceDB com embeddings, files de skills com IP, secrets, certificates, API keys | **Read-only.** Nada destrutivo, nada de mutação de schema, nada de ingestão em massa. Exceções via aprovação explícita do desenvolvedor para cada operação. |
| **PROD** | Configs de produção, .env, scripts de deploy | Read + write com aprovação. Sempre fazer backup/branch antes. |
| **DEV** | Banco dev local, mocks, fixtures, seed data | Read + write livre. Reset/reseed permitido. |
| **DERIVED** | Build outputs, dist/, node_modules | Read + write + delete livre. Sempre regenerável. |

### 13.2 Regras absolutas para DIAMOND

Comandos que o agente **NUNCA** executa contra dados DIAMOND sem aprovação explícita por operação:

- `DROP TABLE`, `TRUNCATE`, `DELETE FROM` (sem WHERE específico aprovado)
- Migrações que alteram schema (`prisma migrate`, `alembic upgrade`)
- `git reset --hard`, `git push --force` em branches que tocam DIAMOND
- Operações de bulk em vetores (re-embed massivo, ingest de N>10 documentos)
- Modificação de arquivos `.skills/*.md` (são IP do projeto)
- Operações em produção remota (SSH, API de prod)
- `rm -rf` sobre qualquer caminho que possa conter DIAMOND

### 13.3 Regra de Pause-and-Confirm

Quando agente precisa fazer operação que **pode** tocar DIAMOND, ele:

1. Para antes de executar
2. Mostra o comando exato que ia rodar
3. Mostra o que esse comando faria (em palavras)
4. Pergunta confirmação explícita
5. Só executa após resposta afirmativa

```
Vou executar:
  pnpm prisma migrate deploy

Isso vai aplicar 3 migrations pendentes ao banco MySQL produção:
  - 20260501_add_users_role_index
  - 20260503_add_publications_doi
  - 20260507_drop_legacy_audit_table  ⚠️ DROP TABLE

Banco MySQL produção é DIAMOND. Confirma?
```

### 13.4 CLAUDE.md declara o que é DIAMOND

Cada projeto declara explicitamente seus DIAMOND no `CLAUDE.md`:

```markdown
## Dados DIAMOND

- MySQL produção (porta 3020-3024) — anos de sessões clínicas anonimizadas
- LanceDB `data/vectors/` — 945K chunks com embeddings BGE-M3 (~12h de processamento)
- `.skills/` — IP teórico cravado, versionado manualmente
- `secrets/*.key` — chaves de produção, sem backup automatizado
```

Sem essa declaração, agente trata tudo como PROD por default (mais cauteloso).

---

## REGRA 14: Design Tokens são Contrato, Não Sugestão   ← EXTENSÃO v5

**O problema:** quando há design system ou design pronto (de Figma, de outro agente, de design entregue por designer humano), agentes "melhoram" sem perceber. Cor `#3d4f3a` vira `#3e503b` "para melhor harmonia". Texto "1ª torção" vira "primeira torção" "para clareza". Vocabulário específico do produto vira vocabulário genérico.

Isso quebra o sistema. Os 3 níveis de quebra:

1. **Visual:** valores hex divergem. Acentos pré-calculados em paletas perdem coerência.
2. **Conceitual:** copy específico carrega decisão de produto. "Bibliotecária · 12 obras · 4 cadeias" não é sinônimo de "Sistema · 12 documentos · 4 grupos". O segundo perde tudo.
3. **Manutenibilidade:** quando design é atualizado upstream, agente não consegue mais sincronizar porque "melhorou" no caminho.

### 14.1 Regra absoluta

Quando há fonte da verdade visual/textual (`tokens.css`, Figma export, mocks HTML/CSS prontos, copy aprovado pelo desenvolvedor), agente:

- **Copia valores literais.** Hex, font sizes, spacing, line-heights — todos exatos.
- **Copia copy literal.** Strings, labels, placeholders, mensagens — todos exatos.
- **Adapta apenas estrutura.** HTML→JSX, CSS→Tailwind classes, marcação→componentes.
- **Não reorganiza.** A ordem dos elementos no design é decisão.
- **Não traduz.** Português permanece português, inglês permanece inglês, neologismo permanece neologismo.
- **Não normaliza.** Vocabulário específico do produto é literal.

### 14.2 Quando agente quer mudar algo da fonte

1. Para.
2. Cita o que está no design original.
3. Diz por que sugere mudar.
4. Pergunta se desenvolvedor aprova.
5. Se aprova, muda nos dois lugares (design source + implementação) ou cria PR no design source.

```
No tokens.css você tem:
  --escuta-600: #3d4f3a;

Vejo que esse verde tem contrast ratio 4.3 contra neutral-50 (#fafaf7),
abaixo do mínimo WCAG AA de 4.5. Sugiro escurecer para #3a4a37 (4.6).

Mas isso muda a fonte da verdade visual. Posso:
(a) Mudar tokens.css para #3a4a37 e refletir em todo o sistema
(b) Manter #3d4f3a (decisão sua) e marcar a11y issue para depois
(c) Outra coisa?
```

### 14.3 Vocabulário do produto

Vocabulário cravado pelo desenvolvedor (mesmo que pareça idiossincrático) é literal:

- "1ª torção", "raiz", "contemporâneo" — em projeto sobre genealogia psicanalítica
- "DIAMOND", "Verificação Trilateral", "AI Jail" — vocabulário deste método
- "sinthome", "après-coup", "Nachträglichkeit" — termos técnicos
- "nós + eu confessional" — voz autoral

Agente **nunca** "traduz para algo mais comum" ou "moderniza" sem aprovação. Se não entende um termo, pergunta o que significa, registra no CLAUDE.md, e usa literal.

---

## REGRA 15: Comunicação Humano-Agente — disciplina de fluxo   ← EXTENSÃO v5

Esta regra crava convenções de comunicação que separam agente útil de agente que cansa o desenvolvedor.

### 15.1 Entrega exata, não inflada

Já citado em Regra 4.1 como erro epistêmico, formalizado aqui:

- Desenvolvedor pede X. Agente entrega X.
- Se durante o trabalho agente vê que cabe Y também, **pede confirmação** antes de fazer.
- Não é desserviço entregar pouco. É desserviço entregar diferente do combinado.

**Exceção:** correção de bug encontrado durante a tarefa. Se ao implementar X agente vê que Y está bugado e Y é usado por X, conserta Y e reporta ("Encontrei e consertei bug em Y enquanto fazia X — segue diff").

### 15.2 Recomendação não substitui escolha

Quando há decisão real do desenvolvedor a fazer:

- Listar alternativas reais com tradeoff honesto.
- Marcar recomendação clara (uma frase: "recomendo A porque...").
- Esperar.

Quando só há um caminho viável:

- Dizer explicitamente "não há escolha real aqui — vou seguir com A".
- Não fingir lista de opções para parecer democrático.

### 15.3 Decisão cravada não é re-perguntável

Já citado em Regra 0.1 e 4.1, formalizado aqui:

- Após decisão fechada (registrada em transcript, em `## Decisões Cravadas`, ou pelo desenvolvedor falando "vai com X"), agente não pergunta de novo.
- Se em sessão posterior o agente quer questionar a decisão, ele faz **explicitamente**: "decisão Y foi cravada em [fonte]. Vejo um problema novo: [problema]. Vale revisitar?". Não simula que não lembra.

### 15.4 Pergunta nova é cara

Cada pergunta ao desenvolvedor custa atenção. Antes de perguntar, agente:

1. Verifica se a resposta está no CLAUDE.md.
2. Verifica se está em decisões cravadas.
3. Verifica se está no histórico anexado.
4. Verifica se é pergunta que ele mesmo pode responder com inferência razoável (e marca como decisão dele, sujeita a override).

Se passou os 4 filtros e ainda é nova, pergunta — **uma**, focada, com contexto mínimo necessário.

**Anti-padrão:** "Antes de eu fazer X, preciso decidir 6 coisas: A, B, C, D, E, F." Se 6 perguntas vêm de uma vez, planejamento foi insuficiente. Re-planeja primeiro.

### 15.5 Wireframe ASCII antes de shell visual grande

Para tarefas que produzem mais de ~15 arquivos de UI ou >800 linhas de layout, agente desenha wireframe ASCII rápido **antes** de codar:

```
┌─────────────┬──────────────────┬──────────┐
│             │                  │          │
│  Sidebar    │    Área central  │ Inspector│
│  240px      │    (flex)        │  48/240  │
│             │                  │          │
│  - Item 1   │  Header          │  [📚]    │
│  - Item 2   │  ─────────       │  [📄]    │
│  - Item 3   │                  │  [📊]    │
│             │  Conteúdo        │          │
│             │                  │          │
└─────────────┴──────────────────┴──────────┘
```

5 minutos de agente + 1 minuto de desenvolvedor evitam ciclo de "construa → não era isso → refaz".

### 15.6 HITL bloqueante respeita escala da decisão

HITL (Human-in-the-Loop) bloqueante é central, mas tem que ser proporcional:

| Tipo de decisão | Forma do checkpoint |
|-----------------|---------------------|
| Arquitetura macro (stack, monorepo, layouts) | Texto + propostas + espera explícita |
| Layout visual de tela | Wireframe ASCII + espera |
| Detalhe de implementação (escolha de variável) | Decide + reporta no commit |
| Bug crítico encontrado | Para tudo + alerta + espera |

Não tudo precisa do mesmo peso de HITL. Excesso de HITL cansa. Insuficiência produz vibecoding.

---

## Workflow Completo de uma Feature

```
PEDIDO: "Quero adicionar [feature X]"

 1. LER CLAUDE.md (técnico + epistêmico + decisões cravadas + DIAMOND)
 2. EXTRAIR decisões cravadas do histórico anexado (Regra 0.1)
 3. VERIFICAR modo de operação aplicável
 4. PERGUNTAR clarificações se necessário (filtro Regra 15.4)
 5. PLANEJAR como a feature se encaixa na arquitetura
 6. VERIFICAR escala (Regra 3): cabe na sessão? Se não, propor divisão.
 7. VERIFICAR restrições semânticas aplicáveis
 8. SE for shell visual grande: WIREFRAME ASCII antes (Regra 15.5)
 9. ESPERAR aprovação do desenvolvedor
10. RESPONDER A PERGUNTA DE VERIFICAÇÃO (Regra 1.1): "como verificamos que funciona de
    verdade?" — declarar dado coerente + escopo de resposta esperado
11. TESTES UNITÁRIOS: escrever testes com mocks (exceto se Regra 11.0)
12. ESPERAR revisão dos testes
13. IMPLEMENTAR: código que faz testes unitários passarem
14. VERIFICAÇÃO TRILATERAL (tsc + build + vitest)
15. TESTE DE VERIFICAÇÃO (Regra 1.1): função real sobre dado coerente, saída no escopo
    declarado, provado vermelho-sem-o-conserto
16. TESTES DE SANIDADE (Regras 9 + 10)
17. TESTES DE REALIDADE (Regra 11) — se feature tem CRUD/auth/permissão
18. SE for port repo→repo: atualizar PORT_LOG.md (Regra 8.1)
19. REPORTAR COBERTURA por camada (Regra 12)
20. REFATORAR se necessário (manter tudo passando)
21. DOCUMENTAR decisões no CLAUDE.md (Regra 6)
22. DOCUMENTAR erros epistêmicos do domínio E do agente (Regras 4 e 4.1)
23. ENTREGAR exatamente o escopo (Regra 15.1)
```

---

## Checklist para Colar no CLAUDE.md do Projeto

```markdown
## Método Akita Estendido — Checklist

### Base (Akita Original)
- [ ] CLAUDE.md criado (100+ linhas)
- [ ] Arquitetura definida ANTES de código
- [ ] TDD first (testes antes de features)
- [ ] Agente em container isolado (AI Jail)
- [ ] Permission model ativo
- [ ] Monorepo com contexto compartilhado (se multi-serviço)
- [ ] Erros documentados no CLAUDE.md
- [ ] CI/CD com linter + testes + vuln scan
- [ ] Zero edição manual — tudo via prompt

### Extensões Epistêmicas (v2)
- [ ] Spec Epistêmica no CLAUDE.md (modos, restrições semânticas, erros de domínio)
- [ ] Verificação Trilateral após cada fase (typecheck + build + testes)
- [ ] Dia 8 Security Hardening executado (SQL injection, rate limit, headers, audit)
- [ ] Erros epistêmicos do domínio documentados (vieses, alucinações de domínio)

### Extensões de Sanidade (v3)
- [ ] Dia 9 Acessibilidade: axe-core em todas as páginas públicas
- [ ] Dia 9 Smoke: cada rota responde 200 com conteúdo real
- [ ] Dia 9 Ícones: SVGs renderizados, não texto
- [ ] Dia 10 Links: todos os href internos apontam para rotas existentes
- [ ] Dia 10 Imagens: todos os src locais existem em public/
- [ ] Dia 10 i18n: nenhum texto no idioma errado em labels/botões
- [ ] Dia 10 APIs: todos os fetch("/api/...") apontam para routes existentes
- [ ] Dia 10 Hydration: nenhum hook/browser API em server component
- [ ] Dia 10 CSS compat: classes deprecated identificadas

### Extensões de Realidade (v4)
- [ ] Dia 11 Auth E2E: login, registro, logout, redirect — testados com browser real
- [ ] Dia 11 CRUD E2E: criar, editar, ver, excluir — verificados no banco real
- [ ] Dia 11 Permissões E2E: cada role acessa/não acessa as rotas certas
- [ ] Dia 11 Fluxos críticos E2E: fluxos multi-user completos testados
- [ ] Dia 11 Seed: dados de teste criados no banco real (cleanup após)
- [ ] REGRA: feature com CRUD/auth/permissão SEM teste E2E = feature NÃO pronta

### Extensões de Disciplina (v5)
- [ ] Lista de Decisões Cravadas no CLAUDE.md, atualizada a cada fechamento
- [ ] Inventário de decisões antes de propor (Regra 0.1)
- [ ] TypeScript strict total (noUncheckedIndexedAccess + exactOptionalPropertyTypes)
- [ ] Limites de escala respeitados (200 linhas/arquivo, 800-1200/sessão)
- [ ] Erros epistêmicos do AGENTE documentados além dos do domínio
- [ ] PORT_LOG.md mantido se há refactor repo→repo
- [ ] Dados DIAMOND declarados no CLAUDE.md
- [ ] Pause-and-Confirm aplicado antes de qualquer operação que toque DIAMOND
- [ ] Design tokens e copy do produto tratados como literais (Regra 14)
- [ ] Vocabulário do produto preservado, não normalizado
- [ ] Recomendação não substitui escolha (Regra 15.2)
- [ ] Decisão cravada não é re-perguntável (Regra 15.3)
- [ ] Wireframe ASCII antes de shell visual grande
- [ ] Dia 11 só onde se aplica (Regra 11.0)

### Extensão de Verificação (v5.1)
- [ ] Pergunta de Verificação respondida ANTES de codar cada tarefa (Regra 1.1)
- [ ] Dados simulados COERENTES criados (com a cara da produção, não foo/bar)
- [ ] Escopo de resposta declarado ANTES de rodar (valores exatos ou faixas+invariantes)
- [ ] Função REAL rodada sobre o dado (mock só no genuinamente externo)
- [ ] Teste provado vermelho sem o conserto (revert → red → restore)
- [ ] Entrega reporta: cenário + dado + escopo declarado + resultado

### Metas de Cobertura (v4 + ajustes v5)
- [ ] Trilateral: 100% (0 erros em tsc + build + vitest)
- [ ] Sanidade: 100% das rotas escaneadas
- [ ] Server Actions: 100% das actions testadas
- [ ] Auth E2E: 100% dos fluxos
- [ ] Permissões E2E: 100% das combinações role × rota admin
- [ ] CRUD E2E: 100% dos módulos
- [ ] Fluxos Críticos: 100% dos fluxos multi-user listados no CLAUDE.md
- [ ] Shell de UI: Smoke 200 + a11y (Dia 11 não-aplicável)
- [ ] Cobertura reportada por camada após cada sessão
```

---

## Resumo da Evolução

| Versão | O que adicionou | Dias |
|--------|----------------|------|
| v1.0 (Akita Original) | TDD, CLAUDE.md, AI Jail, Monorepo, CI/CD | 7 dias |
| v2.0 (Extensões Epistêmicas) | Spec Epistêmica, Verificação Trilateral, Dia 8 Security | 8 dias |
| v3.0 (Extensões de Sanidade) | Dia 9 Acessibilidade/UI, Dia 10 Sanidade Estrutural | 10 dias |
| v4.0 (Extensões de Realidade) | Dia 11 Testes E2E com banco real, browser real, fluxos reais | 11 dias |
| v5.0 (Extensões de Disciplina) | Decisões Cravadas, Erros Epistêmicos do Agente, Refactor Port Repo→Repo, DIAMOND, Design como Contrato, Comunicação Humano-Agente, escala numérica de sessão, strict total como default, Dia 11 não-aplicável a shell de UI | 11 dias + disciplina permanente |
| v5.1 (Pergunta de Verificação — Hudson, 01/08/2026) | Regra 1.1: toda tarefa responde "como verificamos que funciona DE VERDADE?" — dados simulados coerentes + escopo de resposta declarado + função real + provado vermelho-sem-conserto. O degrau entre o unit test mocado e o Dia 11. | idem |

**Do zero ao deploy em 7 dias. Da deploy à segurança em 1 dia. Da segurança à qualidade em 2 dias. Da qualidade à realidade em 1 dia. Da realidade à disciplina contínua — para sempre.**

---

## O que mudou de v4 para v5 — síntese

A v5 nasceu de aplicação intensiva da v4 em projetos de pesquisa solo (saúde mental, IA aplicada à psicanálise, refactor de monorepo poliglota com backend Java) ao longo de Q1-Q2 de 2026. Cinco achados estruturais motivaram a versão:

**1. Decisões cravadas precisam de proteção formal.** Compactação de contexto, sessões longas, conversas ramificadas — tudo isso fazia agentes "esquecerem" decisões fechadas e re-perguntarem. Vibecoding tardio é tão ruim quanto vibecoding original. Regra 0.1 + 15.3 atacam isso.

**2. Refactor entre repos siblings é workflow padrão, não exceção.** Researchers solo, equipes pequenas, transições arquiteturais — todos vivem com legacy + novo coexistindo por meses. Regra 8.1 crava protocolo: read-only sobre legacy, PORT_LOG.md, deprecação só após uso paralelo.

**3. Dados DIAMOND existem e merecem regra própria.** AI Jail genérico não basta quando há banco com anos de dados, vetores que custaram 12h de processamento, IP cravado em files. Regra 13 classifica e formaliza pause-and-confirm.

**4. Design e vocabulário do produto são contrato, não sugestão.** Agentes "melhoram" tokens, copy, vocabulário sem perceber, quebrando coerência do sistema. Regra 14 crava literal.

**5. Erros epistêmicos do AGENTE são reais, não só os do domínio.** Concordância automática, inflar entrega, recomendação travestida de pergunta — vícios que envenenam o trabalho independentemente do código produzido. Regra 4.1 + 15 formalizam.

A v5 não substitui o método Akita original — estende. A filosofia core continua: **disciplina > intuição, planejamento > improvisação, testes > features, domínio > código**. A v5 acrescenta: **decisão cravada > recomendação repetida**.

---

## Como Usar Este Skill

**Claude Code / Crush / agente no terminal:**
Coloque na raiz como `SKILL-METODO-AKITA-ESTENDIDO.md` e referencie no CLAUDE.md:
```markdown
## Skills
Leia e siga SKILL-METODO-AKITA-ESTENDIDO.md antes de qualquer tarefa.
```

**Claude.ai (chat):**
Faça upload como arquivo no início da conversa.

**Projetos Claude com /mnt/skills/user/:**
`/mnt/skills/user/metodo-akita-estendido/SKILL.md`

---

## Skills

Quando este projeto tem outras skills associadas, listar aqui no formato:

```
- SKILL-HUDSON-STYLE.md (voz autoral)
- SKILL-CORPUS-LENS.md (vocabulário do corpus)
- ...
```

Skills são read-only DIAMOND (Regra 13).
