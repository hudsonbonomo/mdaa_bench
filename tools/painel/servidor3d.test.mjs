// Testes do SERVIDOR da vista 3D — G11 e G13 do CONTRATO-V2A.md.
// Separado do grafo3d.test.mjs pela Regra 3, quando o arquivo passou de 200 linhas:
// layout de um lado, rotas e offline do outro.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, cpSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import http from 'node:http';
import { execFileSync } from 'node:child_process';
import { criarPainel } from './painel.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));

function pegar(porta, caminho) {
  return new Promise((ok, erro) => {
    http.get({ host: '127.0.0.1', port: porta, path: caminho }, (r) => {
      let corpo = '';
      r.setEncoding('utf8');
      r.on('data', (c) => { corpo += c; });
      r.on('end', () => ok({ status: r.statusCode, tipo: r.headers['content-type'], corpo }));
    }).on('error', erro);
  });
}

function comPainel(nome, fn) {
  return async () => {
    const destino = mkdtempSync(join(tmpdir(), 'painel3d-'));
    cpSync(join(AQUI, 'fixture', nome), destino, { recursive: true });
    const painel = await criarPainel(destino, { porta: 0 });
    try { await fn(painel); } finally { await painel.fechar(); }
  };
}

describe('G11 · o modelo trafega como JSON puro', () => {
  test('/modelo.json devolve 200 application/json, números que sobrevivem ao round-trip',
    comPainel('mini-mapa', async (painel) => {
      const r = await pegar(painel.porta, '/modelo.json');
      assert.equal(r.status, 200);
      assert.match(r.tipo, /application\/json/);
      const lido = JSON.parse(r.corpo);
      assert.equal(lido.nos.length, 3);
      for (const n of lido.nos) for (const v of n.pos) assert.equal(typeof v, 'number');
      assert.deepEqual(lido, JSON.parse(JSON.stringify(lido)));
    }));
});

describe('G13 · offline de verdade', () => {
  test('a página não busca nada de fora', comPainel('mini-mapa', async (painel) => {
    const { corpo } = await pegar(painel.porta, '/');
    assert.ok(!corpo.includes('https://'), 'a página tem uma URL https');
    for (const atributo of ['src="http', "src='http", 'href="http', "href='http"]) {
      assert.ok(!corpo.includes(atributo), `a página busca recurso externo: ${atributo}`);
    }
  }));

  test('os módulos do cliente são servidos E parseiam', comPainel('mini-mapa', async (painel) => {
    for (const arquivo of ['cena3d.mjs', 'orbita.mjs', 'camera3d.mjs', 'rotulos.mjs']) {
      const r = await pegar(painel.porta, `/${arquivo}`);
      assert.equal(r.status, 200, `${arquivo} não é servido`);
      assert.match(r.tipo, /javascript/);
      // código de browser não roda em node, mas erro de sintaxe é barato de pegar —
      // é a única cobertura de máquina que este arquivo admite
      execFileSync(process.execPath, ['--check', join(AQUI, arquivo)], { timeout: 20000 });
    }
  }));

  test('o three vendorizado é servido pelo próprio painel', comPainel('mini-mapa', async (painel) => {
    const r = await pegar(painel.porta, '/vendor/three@0.180.0/three.module.min.js');
    assert.equal(r.status, 200);
    assert.match(r.tipo, /javascript/);
    assert.ok(r.corpo.includes('three.core.min.js'), 'o module tem de apontar para o core');
  }));
});
