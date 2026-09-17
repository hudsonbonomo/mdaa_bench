// Testes do Painel v1 — V1..V6 do CONTRATO-PAINEL.md.
// Escritos ANTES do código (princípio 1). Escopo declarado no contrato:
// 6 células · 2 ✔ · 1 🔵 · 1 ⏸ · 2 📋 · 1 evento SSE por escrita · 0 escritas no alvo.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, readdirSync, mkdtempSync, cpSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { setTimeout as esperar } from 'node:timers/promises';
import http from 'node:http';

import { parseIndice, parseCelulaAtual, lerProjeto } from './parse.mjs';
import { criarPainel } from './painel.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const FIXTURE = join(AQUI, 'fixture');
const CLI = join(AQUI, 'painel.mjs');
const FRASE = 'Rodar `node --test src/indice/` e ler o PRIMEIRO erro — sem consertar nada ainda.';

function copia(nome) {
  const destino = mkdtempSync(join(tmpdir(), 'painel-'));
  cpSync(join(FIXTURE, nome), destino, { recursive: true });
  return destino;
}

function fotografar(dir) {
  const foto = {};
  const andar = (prefixo) => {
    for (const e of readdirSync(join(dir, prefixo), { withFileTypes: true })) {
      const rel = prefixo ? `${prefixo}/${e.name}` : e.name;
      if (e.isDirectory()) andar(rel);
      else foto[rel] = readFileSync(join(dir, rel), 'utf8');
    }
  };
  andar('');
  return foto;
}

function pegar(porta, caminho = '/') {
  return new Promise((ok, erro) => {
    http.get({ host: '127.0.0.1', port: porta, path: caminho }, (r) => {
      let corpo = '';
      r.setEncoding('utf8');
      r.on('data', (c) => { corpo += c; });
      r.on('end', () => ok({ status: r.statusCode, tipo: r.headers['content-type'], corpo }));
    }).on('error', erro);
  });
}

describe('V1 · parse fiel — varre TODAS as tabelas', () => {
  const texto = readFileSync(join(FIXTURE, 'mini-projeto/vault/estado/INDICE.md'), 'utf8');

  test('encontra as 6 células das DUAS tabelas', () => {
    assert.equal(parseIndice(texto).length, 6);
  });

  test('contagens exatas: 2 ✔ · 1 🔵 · 1 ⏸ · 2 📋', () => {
    const { contagens } = lerProjeto(join(FIXTURE, 'mini-projeto'));
    assert.deepEqual(contagens, { '✔': 2, '🔵': 1, '⏸': 1, '📋': 2 });
  });

  test('célula COM link e SEM link chegam com a mesma forma', () => {
    const celulas = parseIndice(texto);
    const comLink = celulas.find((c) => c.nome === 'Fetcher OpenAlex');
    const semLink = celulas.find((c) => c.nome === 'Exportador CSV');
    assert.equal(comLink.slug, 'celulas/fetcher-openalex.md');
    assert.equal(semLink.slug, null);
    for (const campo of ['nome', 'area', 'status', 'proximoPasso']) {
      assert.equal(typeof comLink[campo], 'string');
      assert.equal(typeof semLink[campo], 'string');
    }
  });

  test('pipe escapado no meio da célula não parte a linha', () => {
    const dedupe = parseIndice(texto).find((c) => c.nome === 'Deduplicação por DOI');
    assert.equal(dedupe.status, '⏸');
    assert.ok(dedupe.proximoPasso.endsWith('chave composta (`titulo` | `ano`)'),
      `próximo passo veio partido: ${dedupe.proximoPasso}`);
  });
});

describe('V2 · a alma está no topo', () => {
  test('o PRÓXIMO PASSO vem da SEÇÃO, não do status (cravada de 25/08)', () => {
    const atual = readFileSync(join(FIXTURE, 'mini-projeto/vault/estado/CELULA-ATUAL.md'), 'utf8');
    assert.equal(parseCelulaAtual(atual).proximoPasso, FRASE);
  });

  test('o nome da célula no topo vem limpo, sem markdown de link', () => {
    const atual = readFileSync(join(FIXTURE, 'mini-projeto/vault/estado/CELULA-ATUAL.md'), 'utf8');
    assert.equal(parseCelulaAtual(atual).celula, 'Índice invertido');
  });

  test('GET / devolve 200 html com a frase exata, as contagens e as 6 células', async () => {
    const raiz = copia('mini-projeto');
    const painel = await criarPainel(raiz, { porta: 0 });
    try {
      const r = await pegar(painel.porta);
      assert.equal(r.status, 200);
      assert.match(r.tipo, /text\/html/);
      // A alma passou a renderizar markdown na v2b (caneta do Hudson, 26/08): a garantia
      // deixou de ser "o HTML contém a frase crua" e virou "o TEXTO da alma é a frase do
      // vault, sem as marcas". Continua caractere por caractere — só que do lado de fora
      // das tags, que é o que o humano lê.
      const alma = /class="alma"[\s\S]*?<p>([\s\S]*?)<\/p>/.exec(r.corpo)[1];
      const lido = alma.replace(/<[^>]+>/g, '').replaceAll('&amp;', '&')
        .replaceAll('&lt;', '<').replaceAll('&gt;', '>');
      assert.equal(lido, FRASE.replaceAll('**', '').replaceAll('`', ''),
        'o texto da alma tem de ser a frase do vault, sem marca de markdown');
      // v2b: as contagens viraram TILES (número grande + cor do estado), então a
      // asserção passou a ler o par cor→número em vez do texto "✔ 2".
      const { CORES } = await import('./grafo.mjs');
      const tiles = [...r.corpo.matchAll(/--cor:(#[0-9a-f]{6})"[^>]*>\s*<b>(\d+)<\/b>/g)]
        .map((m) => [m[1], Number(m[2])]);
      // v2b, 4ª rodada: a ordem passou a ser por AÇÃO, não pela ordem canônica dos
      // status — ativa primeiro, concluída por último. "47 concluída" é histórico.
      assert.deepEqual(tiles, [[CORES['🔵'], 1], [CORES['⏸'], 1], [CORES['📋'], 2], [CORES['✔'], 2]]);
      for (const nome of ['Fetcher OpenAlex', 'Normalizador de autores', 'Índice invertido',
        'Deduplicação por DOI', 'Exportador CSV', 'Cache de requisições']) {
        assert.ok(r.corpo.includes(nome), `célula ausente na página: ${nome}`);
      }
    } finally { await painel.fechar(); }
  });
});

describe('V3 · AO VIVO — exatamente 1 evento por escrita', () => {
  test('uma escrita no INDICE gera 1 evento SSE, não 2 (debounce de 80ms)', async () => {
    const raiz = copia('mini-projeto');
    const painel = await criarPainel(raiz, { porta: 0 });
    let eventos = 0;
    const req = http.get({ host: '127.0.0.1', port: painel.porta, path: '/eventos' }, (r) => {
      r.setEncoding('utf8');
      r.on('data', (c) => { eventos += c.split('event: estado').length - 1; });
    });
    try {
      await esperar(200);                       // watcher armado, conexão de pé
      assert.equal(eventos, 0, 'conectar não pode disparar evento');
      const alvo = join(raiz, 'vault/estado/INDICE.md');
      writeFileSync(alvo, readFileSync(alvo, 'utf8').replace('| 🔵 |', '| ⏸ |'));
      await esperar(600);
      assert.equal(eventos, 1);
    } finally { req.destroy(); await painel.fechar(); }
  });
});

describe('V4 · degradação declarada, não erro', () => {
  test('sem contratos/mapa-de-chaves.md o painel sobe e declara', async () => {
    const raiz = copia('mini-sem-mapa');
    const painel = await criarPainel(raiz, { porta: 0 });
    try {
      const r = await pegar(painel.porta);
      assert.equal(r.status, 200);
      assert.ok(r.corpo.includes('sem grafo: mapa ausente'));
    } finally { await painel.fechar(); }
  });
});

describe('V5 · fail-fast alto, ANTES de abrir a porta', () => {
  test('pasta sem vault/estado: sai != 0, cita o caminho, e a porta fica livre', () => {
    const vazia = mkdtempSync(join(tmpdir(), 'painel-vazia-'));
    mkdirSync(join(vazia, 'src'));
    const PORTA = 3117;
    let status = 0; let stderr = '';
    try {
      execFileSync(process.execPath, [CLI, vazia, '--porta', String(PORTA)],
        { timeout: 20000, encoding: 'utf8', stdio: 'pipe' });
    } catch (e) { status = e.status; stderr = e.stderr ?? ''; }
    assert.notEqual(status, 0, 'tinha de sair com código != 0');
    assert.ok(stderr.includes(join(vazia, 'vault', 'estado')), `stderr precisa citar o caminho: ${stderr}`);
    return new Promise((ok) => {
      http.get({ host: '127.0.0.1', port: PORTA, path: '/' }, () => {
        assert.fail('havia servidor escutando — o fail-fast abriu a porta antes de checar');
      }).on('error', (e) => { assert.equal(e.code, 'ECONNREFUSED'); ok(); });
    });
  }, { timeout: 30000 });
});

describe('V6 · read-only provado', () => {
  test('servir e observar não muda um byte do projeto-alvo', async () => {
    const raiz = copia('mini-projeto');
    const antes = fotografar(raiz);
    const painel = await criarPainel(raiz, { porta: 0 });
    const req = http.get({ host: '127.0.0.1', port: painel.porta, path: '/eventos' }, () => {});
    try {
      await pegar(painel.porta);
      await esperar(200);
    } finally { req.destroy(); await painel.fechar(); }
    assert.deepEqual(fotografar(raiz), antes);
  });
});
