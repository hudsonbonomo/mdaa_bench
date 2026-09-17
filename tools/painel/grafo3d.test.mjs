// Testes da vista 3D — G8..G13 do CONTRATO-V2A.md. Escritos ANTES de qualquer linha.
// A CENA NÃO CALCULA NADA: tudo aqui testa o modelo que o SERVIDOR manda pronto.
// Escopo declarado (fixture mini-mapa): 3 nós · 3 arestas · 2 colunas · 1 ciclo de propósito ·
//   CONSTELACAO RADIAL: raio por camada, angulo por bloco (setor de 45 graus).
//   mini-kernel [2328,964,750] · mini-store [1478,612,-250] · mini-outros [788,1903,250]
// Escopo declarado (mapa real): 19 nós · 39 arestas · 8 setores · 6 anéis · DUAS raízes no miolo.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { montarGrafo } from './grafo.mjs';
import { svg } from './svg2d.mjs';
import { modelo3d } from './grafo3d.mjs';
import { parseIndice } from './parse.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = join(AQUI, '..', '..');
const MINI = join(AQUI, 'fixture', 'mini-mapa');
const textoMini = readFileSync(join(MINI, 'contratos', 'mapa-de-chaves.md'), 'utf8');
const celulasMini = parseIndice(readFileSync(join(MINI, 'vault', 'estado', 'INDICE.md'), 'utf8'));
const grafoMini = () => montarGrafo(textoMini, celulasMini, { esperado: 6 });
const m3dMini = () => modelo3d(grafoMini());

describe('G8 · posições determinísticas, sem sobreposição', () => {
  test('as 3 posições exatas do contrato', () => {
    const nos = m3dMini().nos;
    const pos = (p) => nos.find((n) => n.pacote === p).pos;
    assert.deepEqual(pos('mini-kernel'), [2328, 964, 750]);
    assert.deepEqual(pos('mini-store'), [1478, 612, -250]);
    assert.deepEqual(pos('mini-outros'), [788, 1903, 250]);
  });

  test('nenhum par de nós compartilha posição — na fixture e no mapa real', () => {
    for (const m of [m3dMini(), modelo3d(montarGrafo(
      readFileSync(join(RAIZ, 'contratos', 'mapa-de-chaves.md'), 'utf8'),
      parseIndice(readFileSync(join(RAIZ, 'vault', 'estado', 'INDICE.md'), 'utf8'))))]) {
      const vistas = new Set(m.nos.map((n) => n.pos.join(',')));
      assert.equal(vistas.size, m.nos.length);
    }
  });

  test('duas execuções dão JSON idêntico', () => {
    assert.equal(JSON.stringify(m3dMini()), JSON.stringify(m3dMini()));
  });
});

describe('G8b · Z é CAMADA topológica, não relevo decorativo', () => {
  const real = () => modelo3d(montarGrafo(
    readFileSync(join(RAIZ, 'contratos', 'mapa-de-chaves.md'), 'utf8'),
    parseIndice(readFileSync(join(RAIZ, 'vault', 'estado', 'INDICE.md'), 'utf8'))));

  test('raiz que não injeta ninguém fica no FUNDO; quem injeta mais, à FRENTE', () => {
    const m = real();
    const z = (p) => m.nos.find((n) => n.pacote === p).pos[2];
    assert.equal(m.camadas, 6);
    assert.equal(m.nos.find((n) => n.pacote === 'nll-kernel').camada, 0);
    assert.equal(m.nos.find((n) => n.pacote === 'nll-learning').camada, 5);
    assert.ok(z('nll-kernel') < z('nll-store'), 'a raiz tem de estar atrás de quem a injeta');
    assert.ok(z('nll-store') < z('nll-learning'));
    // quem injeta alguém está SEMPRE à frente de todos os seus alvos
    for (const a of m.arestas) assert.ok(z(a.de) > z(a.para), `${a.de} devia estar à frente de ${a.para}`);
  });

  test('o mapa real não tem ciclo — e a fixture tem, de propósito, sem travar', () => {
    assert.equal(real().temCiclo, false);
    const m = m3dMini();
    assert.equal(m.temCiclo, true);
    assert.equal(m.nos.length, 3);   // ciclo não pode derrubar o layout
  });

  test('os limites vêm do servidor, para a câmera enquadrar sem adivinhar', () => {
    const m = real();
    assert.deepEqual(m.limites.min, [-3474, -3474, -1250]);
    assert.deepEqual(m.limites.max, [3474, 3474, 1250]);
    // a caixa inclui os rótulos de setor: a câmera tem de enquadrar eles também
  });
});

describe('G9 · arestas ancoradas e curvas', () => {
  test('16 pontos, extremos colados nos nós', () => {
    const m = m3dMini();
    assert.equal(m.arestas.length, 3);
    for (const a of m.arestas) {
      assert.equal(a.pontos.length, 16);
      assert.deepEqual(a.pontos[0], m.nos.find((n) => n.pacote === a.de).pos);
      assert.deepEqual(a.pontos[15], m.nos.find((n) => n.pacote === a.para).pos);
    }
  });

  test('a curva arqueia: o miolo sai da reta origem→destino', () => {
    for (const a of m3dMini().arestas) {
      const [p0] = a.pontos;
      const p1 = a.pontos[15];
      let maior = 0;
      a.pontos.forEach((p, i) => {
        const t = i / 15;
        const reta = p0.map((v, k) => v + (p1[k] - v) * t);
        const d = Math.hypot(...p.map((v, k) => v - reta[k]));
        if (d > maior) maior = d;
      });
      assert.ok(maior > 40, `aresta ${a.de}->${a.para} veio reta (desvio ${maior})`);
    }
  });
});

describe('G10 · uma fonte de cor para as duas vistas', () => {
  test('a cor do nó no 3D é a mesma que o SVG 2D usa', () => {
    const g = grafoMini();
    const desenho = svg(modelo3d(g));
    const m = modelo3d(g);
    assert.equal(m.nos.find((n) => n.pacote === 'mini-kernel').cor, '#3ddc97');
    assert.equal(m.nos.find((n) => n.pacote === 'mini-store').cor, '#4aa8ff');
    assert.equal(m.nos.find((n) => n.pacote === 'mini-outros').cor, '#3a4049');
    for (const n of m.nos) assert.ok(desenho.includes(n.cor), `cor ${n.cor} não existe no 2D`);
  });
});

describe('G10b · hierarquia visual vem do servidor, não do olho da cena', () => {
  test('`dependentes` conta quem injeta o nó — é o que dá tamanho e clareza à caixa', () => {
    const m = modelo3d(montarGrafo(
      readFileSync(join(RAIZ, 'contratos', 'mapa-de-chaves.md'), 'utf8'),
      parseIndice(readFileSync(join(RAIZ, 'vault', 'estado', 'INDICE.md'), 'utf8'))));
    const dep = (p) => m.nos.find((n) => n.pacote === p).dependentes;
    assert.equal(dep('nll-store'), 9);
    assert.equal(dep('nll-catalog'), 9);
    assert.equal(dep('nll-kernel'), 6);
    assert.equal(dep('nll-learning'), 0);   // ninguém injeta a folha da frente
    // a soma dos dependentes é exatamente o número de arestas: nada contado duas vezes
    assert.equal(m.nos.reduce((s, n) => s + n.dependentes, 0), m.arestas.length);
  });
});

describe('G11b · o modelo leva os NOMES das chaves (painel lateral)', () => {
  test('clicar num nó tem de poder listar as chaves do pacote, não só contá-las', () => {
    const nos = m3dMini().nos;
    assert.deepEqual(nos.find((n) => n.pacote === 'mini-outros').listaChaves,
      ['mini.view', 'mini.extra']);
    for (const n of nos) assert.equal(n.listaChaves.length, n.chaves);
  });
});

describe('G12 · realidade — o mapa do edtech-nll', () => {
  test('19 nós · 39 arestas · 8 setores · 6 anéis concêntricos', () => {
    const m = modelo3d(montarGrafo(
      readFileSync(join(RAIZ, 'contratos', 'mapa-de-chaves.md'), 'utf8'),
      parseIndice(readFileSync(join(RAIZ, 'vault', 'estado', 'INDICE.md'), 'utf8'))));
    assert.equal(m.nos.length, 19);
    assert.equal(m.arestas.length, 39);
    assert.deepEqual(m.colunas, ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']);
    assert.equal(m.camadas, 6);
    assert.equal(m.setores.length, 8);
    // o anel externo do modelo: camada 5, raio 3440
    assert.equal(Math.round(Math.max(...m.nos.map((n) => Math.hypot(n.pos[0], n.pos[1])))), 3440);
  });
});

