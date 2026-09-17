// Testes da CONSTELACAO — G8c do CONTRATO-V2A.md. Separado do grafo3d.test.mjs pela
// Regra 3, quando o arquivo passou de 200 linhas.
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

describe('G8c · constelação radial — ângulo é bloco, raio é camada', () => {
  const real = () => modelo3d(montarGrafo(
    readFileSync(join(RAIZ, 'contratos', 'mapa-de-chaves.md'), 'utf8'),
    parseIndice(readFileSync(join(RAIZ, 'vault', 'estado', 'INDICE.md'), 'utf8'))));
  const grau = (n) => ((Math.atan2(n.pos[1], n.pos[0]) * 180) / Math.PI + 360) % 360;
  const raio = (n) => Math.hypot(n.pos[0], n.pos[1]);

  test('cada nó cai DENTRO do setor de 45° do seu bloco', () => {
    const m = real();
    for (const n of m.nos) {
      if (raio(n) < 1) continue;                 // o centro não tem ângulo
      const i = m.colunas.indexOf(n.bloco);
      const g = grau(n);
      assert.ok(g > i * 45 && g < (i + 1) * 45,
        `${n.pacote} (bloco ${n.bloco}) caiu em ${g.toFixed(1)}°, fora do setor ${i * 45}–${(i + 1) * 45}°`);
    }
  });

  test('as raízes ocupam o MIOLO e o raio cresce com a camada', () => {
    const m = real();
    // nll.invariants (25/08) criou uma SEGUNDA raiz: o miolo deixou de ser um ponto e
    // virou um anel pequeno. Raiz única volta a ficar em r = 0 exato.
    const raizes = m.nos.filter((n) => n.camada === 0);
    assert.deepEqual(raizes.map((n) => n.pacote).sort(), ['nll-invariants', 'nll-kernel']);
    const anel1 = Math.min(...m.nos.filter((n) => n.camada === 1).map(raio));
    assert.ok(Math.max(...raizes.map(raio)) < anel1, 'o miolo tem de ser menor que o anel 1');
    for (const n of m.nos) assert.ok(raio(n) >= 0 && Number.isFinite(raio(n)));
    const medio = (c) => {
      const grupo = m.nos.filter((n) => n.camada === c);
      return grupo.reduce((s, n) => s + raio(n), 0) / grupo.length;
    };
    for (let c = 1; c < m.camadas - 1; c += 1) {
      assert.ok(medio(c) < medio(c + 1), `anel ${c} devia ser menor que o anel ${c + 1}`);
    }
  });

  test('separação mínima entre nós na planta baixa — rótulo não empilha', () => {
    const m = real();
    let menor = Infinity; let par = '';
    for (let i = 0; i < m.nos.length; i += 1) {
      for (let j = i + 1; j < m.nos.length; j += 1) {
        const d = Math.hypot(m.nos[i].pos[0] - m.nos[j].pos[0], m.nos[i].pos[1] - m.nos[j].pos[1]);
        if (d < menor) { menor = d; par = `${m.nos[i].pacote} × ${m.nos[j].pacote}`; }
      }
    }
    assert.ok(menor >= 380, `nll-store/nll-llm empilhavam a 264: agora o pior par é ${par} a ${Math.round(menor)}`);
  });

  test('o raio do nó vem do servidor e cresce com os dependentes', () => {
    const m = real();
    const r = (p) => m.nos.find((n) => n.pacote === p).raioNo;
    assert.ok(r('nll-store') > r('nll-kernel'), '9 dependentes tem de ser maior que 6');
    assert.ok(r('nll-kernel') > r('nll-learning'), '6 dependentes maior que 0');
    assert.equal(r('nll-store'), r('nll-catalog'), 'mesmos 9 dependentes, mesmo raio');
  });

  test('os 8 rótulos de setor cabem no enquadramento da pose inicial (16:9)', () => {
    const m = real();
    const fi = Math.PI / 2 - (15 * Math.PI) / 180;
    const alturas = [...m.nos, ...m.setores].map((n) => Math.abs(n.pos[1] * Math.sin(fi) - n.pos[2] * Math.cos(fi)));
    const meiaA = Math.max(...alturas) * 1.02;
    const meiaL = meiaA * (16 / 9);
    for (const s of m.setores) {
      assert.ok(Math.abs(s.pos[0]) <= meiaL, `setor ${s.bloco} sai pela lateral`);
      assert.ok(Math.abs(s.pos[1] * Math.sin(fi)) <= meiaA, `setor ${s.bloco} sai por cima/baixo`);
    }
  });

  test('um anel por CAMADA — não um por raio distinto', () => {
    const m = real();
    // o desempate radial cria vários raios dentro da mesma camada; o anel desenhado
    // tem de ser o da camada, senão a planta baixa vira um alvo de 11 círculos
    assert.equal(m.aneis.length, m.camadas);
    assert.equal(m.aneis[0], 1100, 'com DUAS raízes o miolo é um anel, não um ponto');
    for (let i = 1; i < m.aneis.length; i += 1) assert.ok(m.aneis[i] > m.aneis[i - 1]);
  });

  test('o rótulo do bloco aparece UMA vez por setor, na borda — não por nó', () => {
    const m = real();
    assert.equal(m.setores.length, 8);
    assert.deepEqual(m.setores.map((s) => s.bloco), ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']);
    const maiorRaio = Math.max(...m.nos.map(raio));
    for (const s of m.setores) {
      assert.ok(Math.hypot(s.pos[0], s.pos[1]) > maiorRaio, 'o rótulo do setor fica FORA do anel externo');
    }
  });
});

