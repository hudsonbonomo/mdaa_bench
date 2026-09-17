// interacao2d.mjs — roda no BROWSER. ADAPTADOR da planta baixa para a `selecao`:
// diz como achar o nó sob o cursor, como pintar em SVG e como aproximar com o zoom.
// A lógica de seleção NÃO mora aqui — mora no selecao.mjs, compartilhada com o 3D.
import { criarSelecao } from '/selecao.mjs';

// o SVG já chega do servidor com tudo: identidade, chaves e as pontas de cada aresta.
// O cliente não recalcula grafo — só lê o que veio pronto.
const dadosDe = (g) => ({
  pacote: g.dataset.pacote,
  bloco: g.dataset.bloco,
  status: g.dataset.status,
  dependentes: g.dataset.dep,
  chaves: (g.dataset.chaves || '').split(' ').filter(Boolean),
  x: Number(g.dataset.x),
  y: Number(g.dataset.y),
});

export function criarInteracao2d(host, lateral, zoom) {
  // elementFromPoint em vez de e.target: com o SVG transformado pelo zoom, o alvo do
  // evento nem sempre é o <g> do nó — o ponto na tela sempre é.
  const noEm = (e) => (document.elementFromPoint(e.clientX, e.clientY) ?? e.target)
    ?.closest?.('.no');

  const selecao = criarSelecao({
    lateral,
    arestas: () => [...host.querySelectorAll('.aresta')].map((a) => a.dataset),
    pintar: (perto) => {
      for (const n of host.querySelectorAll('.no')) {
        n.classList.toggle('apagado', !!perto && !perto.has(n.dataset.pacote));
      }
      for (const a of host.querySelectorAll('.aresta')) {
        const dentro = !!perto && perto.has(a.dataset.de) && perto.has(a.dataset.para);
        a.classList.toggle('aceso', dentro);
        a.classList.toggle('apagado', !!perto && !dentro);
      }
    },
    focar: (no) => zoom.focar(no.x, no.y),
  });

  host.addEventListener('pointermove', (e) => {
    if (e.buttons) return;                        // arrastando: não repinta
    const no = noEm(e);
    selecao.sobre(no ? dadosDe(no) : null);
    host.style.cursor = no ? 'pointer' : 'grab';
  });

  host.addEventListener('click', (e) => {
    if (host.dataset.arrastou) return;            // veio de um arrasto, não de um clique
    const no = noEm(e);
    selecao.clicar(no ? dadosDe(no) : null);
  });

  return { aplicar: () => selecao.reaplicar(), limpar: () => selecao.limpar() };
}
