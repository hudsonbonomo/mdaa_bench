// Testes do grafo — G1..G7. Escritos ANTES do grafo.mjs.
// Escopo declarado na fixture mini-mapa: 6 chaves · 3 pacotes · 3 blocos (A B C) ·
// 5 injeções brutas · 1 auto-aresta descartada · 3 arestas · 2 colunas (A B) · 1 NÃO CASADA.
// Escopo declarado no mapa real: 46 chaves · 20 pacotes (19 nós + 1 sem chave) · 39 arestas.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseMapa, montarGrafo } from './grafo.mjs';
import { svg } from './svg2d.mjs';
import { modelo3d } from './grafo3d.mjs';
import { parseIndice } from './parse.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = join(AQUI, '..', '..');
const MINI = join(AQUI, 'fixture', 'mini-mapa');
const textoMini = readFileSync(join(MINI, 'contratos', 'mapa-de-chaves.md'), 'utf8');
const celulasMini = parseIndice(readFileSync(join(MINI, 'vault', 'estado', 'INDICE.md'), 'utf8'));
const grafoMini = () => montarGrafo(textoMini, celulasMini, { esperado: 6 });

describe('G1 · parse do mapa — chaves, pacotes, blocos', () => {
  test('6 chaves, 4 pacotes (um sem chave), 3 blocos', () => {
    const m = parseMapa(textoMini);
    assert.equal(m.chaves.size, 6);
    assert.equal(m.pacotes.size, 4);
    assert.deepEqual([...new Set([...m.chaves.values()].map((c) => c.bloco))].sort(), ['A', 'B', 'C']);
  });

  test('BUG 1: cabeçalho "Chaves" não pode ser lido como "Chave"', () => {
    // com casamento por prefixo, a tabela de pacotes vira tabela de chaves e os
    // pacotes somem em silêncio — o sintoma exato foi "pacotes: 0"
    assert.notEqual(parseMapa(textoMini).pacotes.size, 0);
  });

  test('BUG 2: token citado na anotação depois do travessão não é chave do pacote', () => {
    const m = parseMapa(textoMini);
    assert.deepEqual(m.pacotes.get('mini-outros'), ['mini.view', 'mini.extra']);
    const donos = [...m.pacotes].filter(([, ks]) => ks.includes('mini.config')).map(([p]) => p);
    assert.deepEqual(donos, ['mini-kernel'], 'mini.config só pode ter um dono');
  });

  test('pipe escapado na coluna Provê não parte a linha', () => {
    assert.ok(parseMapa(textoMini).chaves.has('mini.view'));
  });
});

describe('G2 · arestas agregadas, sem auto-arestas', () => {
  test('5 injeções brutas viram 3 arestas, 1 auto descartada', () => {
    const g = grafoMini();
    assert.equal(g.injecoesBrutas, 5);
    assert.equal(g.autoArestas, 1);
    assert.equal(g.arestas.length, 3);
    assert.deepEqual(g.arestas.map((a) => `${a.de}->${a.para}`).sort(),
      ['mini-kernel->mini-outros', 'mini-outros->mini-store', 'mini-store->mini-kernel']);
  });

  test('nenhuma aresta liga um pacote a si mesmo', () => {
    for (const a of grafoMini().arestas) assert.notEqual(a.de, a.para);
  });
});

describe('G3 · coluna = bloco da PRIMEIRA chave do pacote', () => {
  test('pacote espalhado por 2 blocos cai no bloco da primeira chave', () => {
    const nos = grafoMini().nos;
    assert.equal(nos.find((n) => n.pacote === 'mini-kernel').bloco, 'A');   // A+C
    assert.equal(nos.find((n) => n.pacote === 'mini-store').bloco, 'A');    // A+B
    assert.equal(nos.find((n) => n.pacote === 'mini-outros').bloco, 'B');   // B+C
  });

  test('só entram colunas que têm nó — a fixture tem 2, não 3', () => {
    assert.deepEqual(grafoMini().colunas, ['A', 'B']);
  });
});

describe('G4 · cor por estado e a linha NÃO CASADA', () => {
  test('Plugin/área só colore; pacote sem célula fica cinza', () => {
    const nos = grafoMini().nos;
    assert.equal(nos.find((n) => n.pacote === 'mini-kernel').status, '✔');
    assert.equal(nos.find((n) => n.pacote === 'mini-store').status, '🔵');
    assert.equal(nos.find((n) => n.pacote === 'mini-outros').status, null);
  });

  test('`packages/` sem nome é a PASTA, não um pacote — ignorada, não vira NÃO CASADA', () => {
    // a linha da C3 no índice real é `packages/` — monorepo + 2 plugins promovidos.
    // Reportar isso como NÃO CASADA enche a página de ruído e esvazia o marcador.
    for (const n of grafoMini().naoCasadas) assert.notEqual(n.pacote, '');
  });

  test('célula apontando para pacote fora do mapa aparece NÃO CASADA, não some', () => {
    const g = grafoMini();
    assert.deepEqual(g.naoCasadas, [{ pacote: 'mini-inexistente', status: '📋', celula: 'Fantasma' }]);
    assert.equal(g.nos.length, 3, 'a não casada não vira nó');
  });
});

describe('G5 · asserção de contagem falha ALTO', () => {
  test('mapa com menos chaves que o esperado lança citando os dois números', () => {
    assert.throws(() => montarGrafo(textoMini, celulasMini, { esperado: 45 }), (e) => {
      assert.ok(e.message.includes('6') && e.message.includes('45'), e.message);
      return true;
    });
  });

  test('sem `esperado`, a asserção usa a contagem que o PRÓPRIO mapa declara', () => {
    // 45 é a contagem DESTE projeto, não uma constante do mundo: o painel recebe o
    // projeto como argumento, e cada mapa declara na prosa quantas chaves tem.
    assert.equal(montarGrafo(textoMini, celulasMini).chaves, 6);
    const mentiroso = textoMini.replace('6 chaves em 4 pacotes', '5 chaves em 4 pacotes');
    assert.throws(() => montarGrafo(mentiroso, celulasMini), /esperava 5/);
  });

  test('pacote SEM chave é legítimo (double de teste) — não vira nó e não estoura', () => {
    // `nll-event-log-fixtures` no mapa real: double in-memory da C3, não provê chave
    // nenhuma de propósito (N3). Antes disso o painel morria com um TypeError cru
    // em `chaves.get(ks[0]).bloco`.
    const g = grafoMini();
    assert.equal(g.nos.length, 3, 'o pacote sem chave não pode virar nó — não tem bloco');
    assert.deepEqual(g.semChave, ['mini-fixtures']);
  });

  test('pacote citando chave INEXISTENTE falha alto, nomeando pacote e chave', () => {
    // esse sim é divergência de contrato, não estado legítimo
    const mentiroso = textoMini.replace('| `mini-store` | `mini.store`', '| `mini-store` | `mini.fantasma`');
    assert.throws(() => montarGrafo(mentiroso, celulasMini, { esperado: 6 }), (e) => {
      assert.ok(e.message.includes('mini-store') && e.message.includes('mini.fantasma'), e.message);
      assert.ok(!(e instanceof TypeError), 'tem de ser erro nomeado, não TypeError cru');
      return true;
    });
  });

  test('a divergência de contagem compara a prosa com a TABELA, não com os nós', () => {
    // com um pacote sem chave, nós < pacotes: comparar com os nós inventaria divergência
    assert.equal(grafoMini().divergenciaDeContagem, false, 'a fixture diz 4 e a tabela tem 4');
    const g = montarGrafo(textoMini.replace('6 chaves em 4 pacotes', '6 chaves em 3 pacotes'),
      celulasMini, { esperado: 6 });
    assert.equal(g.divergenciaDeContagem, true);
    assert.equal(g.prosaDiz, 3);
  });

  test('chave sem pacote também falha alto, nomeando a chave', () => {
    const furado = textoMini.replace('| `mini-outros` | `mini.view` · `mini.extra`', '| `mini-outros` | `mini.view`');
    assert.throws(() => montarGrafo(furado, celulasMini, { esperado: 6 }), /mini\.extra/);
  });
});

describe('G6 · SVG determinístico', () => {
  test('um nó por pacote, uma aresta por par, e duas execuções dão o MESMO svg', () => {
    const g = grafoMini();
    const a = svg(modelo3d(g));
    assert.equal(a.split('class="no"').length - 1, 3);
    assert.equal(a.split('class="aresta"').length - 1, 3);
    assert.ok(a.startsWith('<svg') && a.trimEnd().endsWith('</svg>'));
    assert.equal(a, svg(modelo3d(montarGrafo(textoMini, celulasMini, { esperado: 6 }))));
  });
});

describe('G7 · realidade — o mapa do edtech-nll', () => {
  const texto = readFileSync(join(RAIZ, 'contratos', 'mapa-de-chaves.md'), 'utf8');
  const celulas = parseIndice(readFileSync(join(RAIZ, 'vault', 'estado', 'INDICE.md'), 'utf8'));

  test('46 chaves · 19 nós + 1 pacote sem chave · 39 arestas — o escopo declarado', () => {
    const g = montarGrafo(texto, celulas, { esperado: 46 });
    assert.equal(g.chaves, 46);
    assert.equal(g.nos.length, 19);
    assert.deepEqual(g.semChave, ['nll-event-log-fixtures']);
    assert.deepEqual(g.colunas, ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']);
    assert.equal(g.arestas.length, 39);
    assert.equal(g.autoArestas, 13);
  });

  test('a divergência 17×18 foi RESOLVIDA no contrato — a prosa agora diz 20', () => {
    // FM-1 nasceu dessa divergência. O Hudson corrigiu a prosa em db4faa3, contando a
    // tabela em vez de somar sobre a prosa velha — e o painel deixa de acusar sozinho.
    const g = montarGrafo(texto, celulas, { esperado: 46 });
    assert.equal(g.prosaDiz, 20);
    assert.equal(g.divergenciaDeContagem, false);
  });

  test('as NÃO CASADAS aparecem, e cada pacote UMA vez só', () => {
    // duas células apontam para packages/nll-event-log (a C6 e a do carimbo): repetir
    // o aviso na página é ruído, então a lista dedupe por pacote.
    const nomes = montarGrafo(texto, celulas, { esperado: 46 }).naoCasadas.map((n) => n.pacote);
    assert.equal(new Set(nomes).size, nomes.length, 'a lista não pode repetir pacote');
    assert.ok(nomes.includes('nll-event-log'));
    // os pacotes da leva 1 existem no disco e no índice, mas ainda NÃO no mapa
    for (const p of ['nll-evidence', 'nll-onboarding', 'nll-continuity']) assert.ok(nomes.includes(p));
  });
});
