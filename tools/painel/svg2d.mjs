// svg2d.mjs — a PLANTA BAIXA da constelação: exatamente o mesmo layout do 3D, com o z
// descartado. Não é um segundo desenho; é o mesmo modelo visto de cima. O toggle 2D/3D
// da página é "planta baixa" × "corte", não duas verdades diferentes.
import { TOKENS } from './estilo.mjs';

const MARGEM = 40;
const T = TOKENS.base;

// Hexagono deitado (ponta em cima): 6 vertices a cada 60 graus.
const hexagono = (r) => Array.from({ length: 6 }, (_, i) => {
  const a = ((i * 60 - 90) * Math.PI) / 180;
  return `${Math.round(r * Math.cos(a))},${Math.round(r * Math.sin(a))}`;
}).join(' ');

function escapar(t) {
  return String(t).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

// SVG cresce para baixo; o modelo cresce para cima. Só o y inverte.
const tela = (p) => [p[0], -p[1]];

export function svg(m) {
  const xs = [...m.nos, ...m.setores].map((n) => n.pos[0]);
  const ys = [...m.nos, ...m.setores].map((n) => n.pos[1]);
  const min = [Math.min(...xs) - MARGEM, -Math.max(...ys) - MARGEM];
  const largura = Math.max(...xs) - Math.min(...xs) + MARGEM * 2;
  const altura = Math.max(...ys) - Math.min(...ys) + MARGEM * 2;

  const raios = m.aneis.filter((r) => r > 1);
  const aneis = raios.map((r) => `<circle class="anel" cx="0" cy="0" r="${r}" />`).join('');

  const divisorias = m.colunas.map((_, i) => {
    const ang = (i * 45 * Math.PI) / 180;
    const r = Math.max(...raios) + 220;
    return `<line class="divisoria" x1="0" y1="0" x2="${Math.round(r * Math.cos(ang))}"
      y2="${Math.round(-r * Math.sin(ang))}" />`;
  }).join('');

  const arestas = m.arestas.map((a) => {
    const pontos = a.pontos.map((p) => tela(p).map(Math.round).join(',')).join(' ');
    return `<polyline class="aresta" data-de="${a.de}" data-para="${a.para}" points="${pontos}" />`;
  }).join('');

  const maisDeps = Math.max(1, ...m.nos.map((n) => n.dependentes));
  const nos = m.nos.map((no) => {
    const [x, y] = tela(no.pos);
    const peso = no.dependentes / maisDeps;
    // disco, não caixa: no radial a caixa alongada vira lasca inclinada. O RAIO é a
    // hierarquia, e vem pronto do servidor.
    const dy = no.rotuloAcima ? -(no.raioNo + 26) : no.raioNo + 74;
    return `<g class="no" data-pacote="${escapar(no.pacote)}" data-chaves="${escapar(no.listaChaves.join(' '))}"
      data-bloco="${no.bloco}" data-status="${no.status ?? ''}" data-dep="${no.dependentes}"
      data-x="${Math.round(x)}" data-y="${Math.round(y)}"
      transform="translate(${Math.round(x)},${Math.round(y)})">
      <circle class="alvo" r="${no.raioNo + 46}" />
      <polygon class="hex" points="${hexagono(no.raioNo)}" fill="${no.cor}"
        fill-opacity="${(0.14 + 0.2 * peso).toFixed(2)}" stroke="${no.cor}" stroke-width="4" />
      <text class="rotulo" y="${dy}">${escapar(no.pacote)}</text>
      <text class="sub" y="${dy + 46}">${no.status ?? '·'} ${no.chaves}ch · ${no.dependentes}dep</text>
    </g>`;
  }).join('');

  // rótulo do bloco: uma vez por setor, ANCORADO NA MOLDURA do desenho — não solto no
  // vazio. Projeta a direção do setor até a borda do viewBox e recua um respiro.
  // o viewBox NÃO é centrado em zero (na fixture os nós ocupam só dois setores), então a
  // projeção parte do centro da MOLDURA, não da origem do modelo
  const cx = min[0] + largura / 2; const cy = min[1] + altura / 2;
  const naBorda = (dx, dy) => {
    const meiaL = largura / 2 - 80; const meiaA = altura / 2 - 60;
    const n = Math.hypot(dx, dy) || 1;
    const t = Math.min(meiaL / Math.abs(dx / n || 1e-9), meiaA / Math.abs(dy / n || 1e-9));
    return [Math.round(cx + (dx / n) * t), Math.round(cy + (dy / n) * t)];
  };
  const setores = m.setores.map((s) => {
    const [x, y] = naBorda(...tela(s.pos));
    const letra = `<tspan class="setor-letra">${s.bloco}</tspan>`;
    const corpo = s.nome ? `${letra} ${escapar(s.nome)}` : s.bloco;
    return `<text class="setor" x="${Math.round(x)}" y="${Math.round(y)}">${corpo}</text>`;
  }).join('');

  return `<svg viewBox="${Math.round(min[0])} ${Math.round(min[1])} ${Math.round(largura)} ${Math.round(altura)}"
  width="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="constelação de pacotes">
<style>
  .anel { fill: none; stroke: ${T.borda}; stroke-width: 2; }
  .divisoria { stroke: ${T.borda}; stroke-width: 1.5; opacity: .5; }
  .aresta { fill: none; stroke: ${T.acento}; stroke-width: 3; opacity: .3; }
  .rotulo { fill: ${T.texto}; font: 600 46px ui-sans-serif, system-ui, sans-serif; text-anchor: middle; }
  .sub { fill: ${T.terciario}; font: 36px ui-sans-serif, system-ui, sans-serif; text-anchor: middle; }
  .no { cursor: pointer; }
  /* o <g> nao tem area: quem recebe o ponteiro sao os filhos, e o rotulo tambem
     tem de ser clicavel — errar o hexagono por 3px nao pode custar o clique */
  .no * { pointer-events: all; }
  /* alvo invisivel: garante que o clique pegue o no inteiro, nao so o hexagono */
  .alvo { fill: transparent; stroke: none; }
  .no.apagado, .aresta.apagado { opacity: .1; }
  .aresta.aceso { stroke: ${T.acento}; opacity: .9; }
  .setor { fill: ${T.terciario}; font: 650 96px ui-sans-serif, system-ui, sans-serif;
    text-anchor: middle; dominant-baseline: middle; letter-spacing: 2px; }
  .setor-letra { fill: ${T.borda}; font-size: 64px; letter-spacing: 8px; }
</style>
${aneis}${divisorias}${arestas}${setores}${nos}
</svg>`;
}
