// grafo3d.mjs — o LAYOUT, único para as duas vistas.
//
// Constelação radial: ÂNGULO = bloco (setor fixo de 45°), RAIO = camada de dependência,
// Z = camada. O 2D desenha (x, y) — planta baixa. O 3D acrescenta o z — corte. Não são
// dois desenhos: é a mesma matemática, com e sem profundidade.
//
// A CENA NÃO CALCULA NADA (emenda do Hudson): tudo sai daqui pronto, no servidor.
import { CORES } from './grafo.mjs';

const R_MIOLO = 1100;   // quando há MAIS DE UMA raiz, o miolo vira um anel pequeno:
                        // duas raízes do mesmo bloco em r≈0 dividem um arco curto demais
                        // e o desempate radial chegava a virar raio NEGATIVO (180° fora
                        // do setor). Com raio 1100 o arco de 22,5° já vale 432 unidades.
const R_BASE = 1600;    // primeiro anel de dependência, com folga de 500 sobre o miolo
const R_ANEL = 460;     // distância entre anéis
const R_FOLGA = 320;    // onde o rótulo do bloco fica, além do anel externo
const DESLOCA = 200;    // desempate radial de quem divide o mesmo (bloco, camada)
const R_NO_MIN = 46; const R_NO_MAX = 116;   // raio da esfera: hierarquia por dependentes
const E_Z = 500;        // profundidade por camada: girar revela o cone
const ARCO = 220;       // quanto a aresta arqueia, em Z
const AMOSTRAS = 16;
const SETOR = 45;       // 8 blocos × 45° = 360°

// Camada = maior caminho seguindo 'injeta'. Raiz (não injeta ninguém) = 0, no centro.
// Ciclo não trava: a recursão se protege e o modelo DECLARA que houve ciclo.
function camadas(nos, arestas) {
  const injeta = new Map(nos.map((n) => [n.pacote, []]));
  for (const a of arestas) injeta.get(a.de)?.push(a.para);
  const memo = new Map();
  const visitando = new Set();
  let temCiclo = false;

  const de = (p) => {
    if (memo.has(p)) return memo.get(p);
    if (visitando.has(p)) { temCiclo = true; return 0; }
    visitando.add(p);
    const alvos = injeta.get(p) ?? [];
    const c = alvos.length ? 1 + Math.max(...alvos.map(de)) : 0;
    visitando.delete(p);
    memo.set(p, c);
    return c;
  };
  for (const n of nos) de(n.pacote);
  return { camadaDe: memo, temCiclo };
}

// Raiz única fica no CENTRO exato; várias raízes viram o anel do miolo.
const raioDa = (camada, raizes) => {
  if (camada > 0) return R_BASE + (camada - 1) * R_ANEL;
  return raizes > 1 ? R_MIOLO : 0;
};

export function modelo3d(g) {
  const { camadaDe, temCiclo } = camadas(g.nos, g.arestas);
  const dependentes = new Map(g.nos.map((n) => [n.pacote, 0]));
  for (const a of g.arestas) dependentes.set(a.para, (dependentes.get(a.para) ?? 0) + 1);
  const maior = Math.max(...camadaDe.values());

  // quantos dividem a mesma célula (bloco, camada) — eles se espalham DENTRO do setor
  const total = new Map();
  for (const no of g.nos) {
    const k = `${no.bloco}/${camadaDe.get(no.pacote)}`;
    total.set(k, (total.get(k) ?? 0) + 1);
  }
  const raizes = g.nos.filter((n) => camadaDe.get(n.pacote) === 0).length;
  const usado = new Map();

  const nos = g.nos.map((no) => {
    const camada = camadaDe.get(no.pacote);
    const k = `${no.bloco}/${camada}`;
    const m = total.get(k); const j = usado.get(k) ?? 0;
    usado.set(k, j + 1);
    const setor = g.colunas.indexOf(no.bloco);
    // (j+0.5)/m espalha ate as bordas do setor; (j+1)/(m+1) apertava no meio e
    // deixava nll-store e nll-llm a 264 unidades, com os rotulos empilhados
    const ang = ((setor + (j + 0.5) / m) * SETOR * Math.PI) / 180;
    // desempate radial além do angular: dois nós do mesmo bloco no mesmo anel ficariam
    // perto demais só com o ângulo, porque 45° vale pouco em raio pequeno
    const r = raioDa(camada, raizes) + (j - (m - 1) / 2) * DESLOCA;
    return {
      pacote: no.pacote,
      bloco: no.bloco,
      camada,
      dependentes: dependentes.get(no.pacote) ?? 0,
      chaves: no.chaves,
      listaChaves: no.listaChaves,
      status: no.status,
      cor: no.status ? CORES[no.status] : CORES.sem,   // MESMA fonte de cor do 2D
      raioNo: 0,                    // preenchido abaixo, quando o maior dependentes e conhecido
      rotuloAcima: j % 2 === 0,     // alterna: dois vizinhos de setor não colidem o chip
      pos: [Math.round(r * Math.cos(ang)), Math.round(r * Math.sin(ang)), (camada - maior / 2) * E_Z],
    };
  });

  const maisDeps = Math.max(1, ...nos.map((n) => n.dependentes));
  for (const n of nos) n.raioNo = Math.round(R_NO_MIN + (R_NO_MAX - R_NO_MIN) * (n.dependentes / maisDeps));

  const onde = new Map(nos.map((n) => [n.pacote, n.pos]));
  const arestas = g.arestas.map(({ de, para }) => {
    const p0 = onde.get(de); const p1 = onde.get(para);
    const c = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2 + ARCO];
    const pontos = [];
    for (let i = 0; i < AMOSTRAS; i += 1) {
      const t = i / (AMOSTRAS - 1); const u = 1 - t;
      pontos.push([0, 1, 2].map((x) => u * u * p0[x] + 2 * u * t * c[x] + t * t * p1[x]));
    }
    return { de, para, pontos };
  });

  // rótulo do bloco: UMA vez por setor, na borda de fora — não repetido em cada nó
  const raioMax = Math.max(...nos.map((n) => Math.hypot(n.pos[0], n.pos[1])));
  const setores = g.colunas.map((bloco, i) => {
    const ang = ((i + 0.5) * SETOR * Math.PI) / 180;
    const r = raioMax + R_FOLGA;
    return { bloco, nome: g.blocos?.get(bloco) ?? '',
      pos: [Math.round(r * Math.cos(ang)), Math.round(r * Math.sin(ang)), 0] };
  });

  const eixo = (x) => [...nos.map((n) => n.pos[x]), ...setores.map((s) => s.pos[x])];
  const limites = {
    min: [0, 1, 2].map((x) => Math.min(...eixo(x))),
    max: [0, 1, 2].map((x) => Math.max(...eixo(x))),
  };

  // um anel por CAMADA: o desempate radial cria varios raios dentro da mesma camada,
  // e desenhar todos viraria um alvo de circulos em vez de anéis de dependencia
  const aneis = Array.from({ length: maior + 1 }, (_, c) => raioDa(c, raizes));

  return {
    nos,
    arestas,
    setores,
    aneis,
    colunas: g.colunas,
    camadas: maior + 1,
    temCiclo,
    limites,
    chaves: g.chaves,
    naoCasadas: g.naoCasadas,
    prosaDiz: g.prosaDiz,
    divergenciaDeContagem: g.divergenciaDeContagem,
  };
}
