// auditoria-chaves.mjs — compara as chaves declaradas no `mapa-de-chaves.md` com os
// plugins que existem em `packages/*/src`. Genérica, standalone, zero dependências,
// projeto como argumento (padrão `sdd-para-vault`).
//
// POR QUE ELA EXISTE: a varredura ad-hoc por `name: 'chave'` **subconta**. O `nll.config`
// é composição de loader — uma função, não um objeto com `name:` — e sumia da contagem.
// A tentação é somar essas à contagem de plugins e declarar "39 de 46"; é justamente
// isso que esta ferramenta se recusa a fazer.
//
// TRÊS BALDES, e o do meio não se soma a ninguém:
//   1. comLiteral  — plugin com `name: 'chave'` (ou `'chave:variante'`). Fato verificável.
//   2. semLiteral  — a chave aparece em `src/`, mas só em prosa. **Exige leitura humana.**
//   3. ausentes    — não aparece em lugar nenhum.
//
// Um balde "quase implementada" que entra no total é o mesmo erro que o painel já pegou
// uma vez (FM-1: prosa dizia 17, tabela tinha 18). Contagem que arredonda a favor é pior
// que contagem nenhuma, porque parece auditoria.

/** Só as linhas cuja PRIMEIRA célula é uma chave `dominio.nome` — linhas de pacote usam `dominio-nome`. */
export function chavesDoMapa(texto) {
  const achadas = [];
  for (const linha of texto.split('\n')) {
    const m = /^\|\s*`((?:nll|edtech)\.[a-z-]+)`/.exec(linha);
    if (m && !achadas.includes(m[1])) achadas.push(m[1]);
  }
  return achadas;
}

const literalDe = (chave) => new RegExp(`name:\\s*'${chave.replace('.', '\\.')}(:[a-z-]+)?'`);

/**
 * `fontes` é uma lista de `{ arquivo, texto }` — a leitura de disco fica fora, para o
 * teste poder exercitar a classificação sem inventar um repositório.
 */
export function classificar(chaves, fontes) {
  const comLiteral = [];
  const semLiteral = [];
  const ausentes = [];

  for (const chave of chaves) {
    const comNome = fontes.find((f) => literalDe(chave).test(f.texto));
    if (comNome) {
      const evidencia = literalDe(chave).exec(comNome.texto)[0];
      comLiteral.push({ chave, arquivo: comNome.arquivo, evidencia });
      continue;
    }
    // Menção em prosa NÃO é implementação. Ela vira pergunta, não crédito.
    const citada = fontes.find((f) => f.texto.includes(`\`${chave}\``) || f.texto.includes(`${chave} `));
    if (citada) semLiteral.push({ chave, arquivo: citada.arquivo });
    else ausentes.push(chave);
  }
  // Sem campo `total`: quem quiser um número tem de escolher qual, e assumir a escolha.
  return { comLiteral, semLiteral, ausentes };
}

export function auditar(textoDoMapa, fontes) {
  const chaves = chavesDoMapa(textoDoMapa);
  const { comLiteral, semLiteral, ausentes } = classificar(chaves, fontes);
  const linhas = [
    `chaves com plugin nomeado: ${comLiteral.length} de ${chaves.length}`,
    '',
    `sem literal (${semLiteral.length}) — aparecem em src/ só em prosa, EXIGEM leitura humana:`,
    ...semLiteral.map((c) => `  · ${c.chave} — ${c.arquivo}`),
    '',
    `ausentes (${ausentes.length}):`,
    ...ausentes.map((c) => `  · ${c}`),
  ];
  return linhas.join('\n');
}

// A leitura de disco mora no CLI (`auditoria-chaves-cli.mjs`), não aqui: manter este
// módulo puro é o que deixa a classificação testável sem inventar um repositório.
