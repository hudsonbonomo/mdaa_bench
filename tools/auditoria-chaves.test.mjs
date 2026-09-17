// Testes da auditoria de chaves — A1..A8. Escritos ANTES de auditoria-chaves.mjs.
// Convenção do `tools/`: `node --test`, não vitest (o vitest da raiz escopa o gate ao
// esqueleto: "o esqueleto testa o esqueleto").
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { auditar, chavesDoMapa, classificar } from './auditoria-chaves.mjs';

const MAPA = [
  '| Chave | Provê | Injeta | Dono | Card. |',
  '| `nll.alpha` | X | — | nll | única |',
  '| `nll.beta` | Y | — | nll | por nome |',
  '| `nll.gama` | Z | — | nll | única |',
  '| `nll-pacote` | `nll.alpha` · `nll.beta` |',
].join('\n');

const FONTES = [
  { arquivo: 'packages/p/src/a.ts', texto: "export default { name: 'nll.alpha', apply() {} };" },
  { arquivo: 'packages/p/src/b.ts', texto: "export const x = { name: 'nll.beta:variante' };" },
  { arquivo: 'packages/p/src/c.ts', texto: '/** `nll.gama` — sem plugin nomeado. */\nexport function f() {}' },
];

describe('auditoria de chaves · lê o mapa', () => {
  test('A1 extrai só as chaves, não as linhas de pacote', () => {
    assert.deepEqual(chavesDoMapa(MAPA), ['nll.alpha', 'nll.beta', 'nll.gama']);
  });
});

describe('auditoria de chaves · três baldes, e o do meio é o que importa', () => {
  test('A2 plugin com literal `name:` conta como implementada', () => {
    assert.deepEqual(classificar(['nll.alpha'], FONTES).comLiteral.map((c) => c.chave), ['nll.alpha']);
  });

  test('A3 variante `por nome` conta para a chave-mãe, e a evidência mostra qual', () => {
    assert.match(classificar(['nll.beta'], FONTES).comLiteral[0].evidencia, /nll\.beta:variante/);
  });

  test('A4 chave citada só em PROSA vai para o balde do meio, nunca para o dos plugins', () => {
    const r = classificar(['nll.gama'], FONTES);
    assert.deepEqual(r.comLiteral, []);
    assert.deepEqual(r.semLiteral.map((c) => c.chave), ['nll.gama']);
    assert.equal(r.semLiteral[0].arquivo, 'packages/p/src/c.ts');
  });

  test('A5 chave que não aparece em lugar nenhum vai para ausentes', () => {
    assert.deepEqual(classificar(['nll.delta'], FONTES).ausentes, ['nll.delta']);
  });

  test('A6 NÃO existe campo `total`: somar o balde do meio é exatamente o erro a evitar', () => {
    const r = classificar(['nll.alpha', 'nll.beta', 'nll.gama', 'nll.delta'], FONTES);
    assert.equal(r.comLiteral.length, 2);
    assert.equal(r.semLiteral.length, 1);
    assert.equal(r.ausentes.length, 1);
    assert.equal('total' in r, false);
  });
});

describe('auditoria de chaves · o relatório não arredonda a favor', () => {
  test('A7 relata os três números separados e cita evidência de cada balde', () => {
    const texto = auditar(MAPA, FONTES);
    assert.match(texto, /2 de 3/);
    assert.match(texto, /sem literal/);
    assert.match(texto, /packages\/p\/src\/c\.ts/);
  });

  test('A8 chave ausente aparece NOMEADA — silêncio sobre o que falta é o pior relatório', () => {
    const texto = auditar(MAPA + '\n| `nll.delta` | W | — | nll | única |', FONTES);
    assert.match(texto, /nll\.delta/);
  });
});
