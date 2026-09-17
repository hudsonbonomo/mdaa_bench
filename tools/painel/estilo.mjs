// estilo.mjs — tokens e folha de estilo. FONTE ÚNICA de cor: CSS, SVG 2D e cena 3D
// bebem daqui. Contraste conferido por teste (I2), não estimado no olho.
//
// LAYOUT DE DASHBOARD (v2b, 2ª rodada): a página NÃO rola. Ela é uma grade de altura
// de viewport — topo com contagens, faixa da alma, e embaixo dois painéis que rolam
// por dentro. Quem rola é o painel, nunca o essencial.
import { CORES } from './grafo.mjs';

export const TOKENS = {
  base: {
    fundo: '#0b0d14',
    superficie: '#141824',
    borda: '#2a3145',
    texto: '#e8eaf2',
    secundario: '#a8b1c9',
    terciario: '#7d87a3',
    acento: '#8b6cff',        // violeta — o ÚNICO acento da casa
  },
  estado: CORES,              // ✔ 🔵 ⏸ 📋 + `sem`, sem cópia
};

const T = TOKENS.base;

export const CSS = `
:root { color-scheme: dark; }
* { box-sizing: border-box; }

body {
  margin: 0; padding: .9rem 1.25rem 1.1rem; color: ${T.texto};
  height: 100vh; overflow: hidden;
  display: grid; gap: 1.25rem;
  grid-template-columns: clamp(17rem, 22vw, 26rem) minmax(0, 1fr);
  grid-template-rows: auto auto minmax(0, 1fr);
  /* a faixa dos tiles e a alma cedem altura para o grafo */
  background: ${T.fundo};
  background-image:
    radial-gradient(70% 45% at 50% -10%, ${T.acento}22 0%, transparent 70%),
    radial-gradient(50% 35% at 100% 0%, ${TOKENS.estado['🔵']}14 0%, transparent 60%);
  font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
code { font: .88em ui-monospace, SFMono-Regular, "Cascadia Code", Consolas, monospace;
  color: ${T.secundario}; background: ${T.superficie}; border: 1px solid ${T.borda};
  border-radius: .3rem; padding: .05em .35em; }
strong { color: ${T.texto}; font-weight: 650; }

/* --- topo: nome + tiles de contagem --- */
header { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; }
h1 { margin: 0; font-size: .95rem; font-weight: 650; letter-spacing: .12em;
  text-transform: uppercase; color: ${T.terciario}; }
.tiles { display: grid; grid-auto-flow: column; gap: .75rem; margin-left: auto; }
.tile { display: grid; gap: .1rem; padding: .4rem .85rem; border-radius: .7rem;
  background: ${T.superficie}; border: 1px solid ${T.borda};
  border-top: 2px solid var(--cor); }
.tile b { color: var(--cor); line-height: 1; font-weight: 650;
  font-variant-numeric: tabular-nums; }
.tile span { letter-spacing: .12em; text-transform: uppercase; color: ${T.terciario}; }
/* peso pela AÇÃO: o que pede algo de você agora é grande; histórico é nota de rodapé */
.tile.forte { min-width: 6.5rem; }
.tile.forte b { font-size: 1.75rem; }
.tile.forte span { font-size: .7rem; }
.tile.fraco { min-width: 4.6rem; opacity: .62; border-top-color: ${T.borda}; }
.tile.fraco b { font-size: 1.05rem; }
.tile.fraco span { font-size: .62rem; }

/* --- a alma: faixa inteira, o herói da tela --- */
.alma { padding: 1rem 1.5rem; border-radius: 1rem; border: 1px solid ${T.borda};
  max-height: 22vh; overflow-y: auto;
  background: linear-gradient(150deg, ${T.superficie} 0%, ${T.fundo} 100%);
  box-shadow: 0 0 0 1px ${T.acento}1a, 0 24px 60px -34px ${T.acento}66; }
.alma .rotulo { font-size: .7rem; letter-spacing: .18em; text-transform: uppercase;
  color: ${T.acento}; font-weight: 650; }
.alma p { margin: .6rem 0 0; font-size: clamp(1.3rem, 2.1vw, 2rem); line-height: 1.25;
  font-weight: 550; letter-spacing: -.015em; }

/* --- embaixo: dois painéis, e são ELES que rolam --- */
#corpo { display: contents; }
header, .alma { grid-column: 1 / -1; }
.caixa { border-radius: 1rem; border: 1px solid ${T.borda}; background: ${T.superficie}80;
  min-height: 0; display: flex; flex-direction: column; }
.caixa > .rotulo { flex: none; display: flex; align-items: center; gap: .75rem;
  min-height: 2.9rem; padding: .5rem .7rem .5rem 1.1rem; font-size: .7rem;
  letter-spacing: .16em; text-transform: uppercase; color: ${T.terciario};
  border-bottom: 1px solid ${T.borda}; }
#grafo-vista { color: ${T.acento}; }
.encaixar { margin-left: auto; }
.vista, .encaixar { padding: .35rem .85rem; border-radius: 999px;
  border: 1px solid ${T.borda}; background: ${T.fundo}; color: ${T.acento};
  font: 650 .68rem ui-sans-serif, system-ui, sans-serif; letter-spacing: .14em;
  cursor: pointer; }
.vista:hover, .encaixar:hover { border-color: ${T.acento}; }
#celulas { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: .6rem; }
.grupo { margin-bottom: 1.25rem; }
.grupo h2 { display: flex; align-items: center; gap: .5rem; margin: 0 0 .35rem;
  padding: 0 .5rem; font-size: .68rem; letter-spacing: .14em; text-transform: uppercase;
  color: ${T.terciario}; font-weight: 650; }
.qtd { color: ${T.terciario}; font-weight: 500; font-variant-numeric: tabular-nums; }
ul { list-style: none; margin: 0; padding: 0; display: grid; gap: .15rem; }
li { display: grid; gap: .15rem; padding: .6rem .75rem; border-radius: .55rem;
  border-left: 2px solid transparent; }
li:hover { background: ${T.fundo}; border-left-color: ${T.borda}; }
.nome { font-size: .92rem; font-weight: 550; }
.area { color: ${T.terciario}; font-size: .78rem; }
.passo { color: ${T.secundario}; font-size: .82rem; }

/* --- grafo: MESMO container para planta baixa e corte 3D --- */
.tela { flex: 1 1 auto; min-height: 0; overflow: hidden; position: relative;
  cursor: grab; touch-action: none; }
.tela[hidden] { display: none; }
.tela { display: grid; }
/* o SVG encaixa NO CONTAINER: 100% nos dois eixos + preserveAspectRatio centraliza e
   escala. Com max-width/height + width:auto ele ficava amontoado num canto. */
.tela svg { display: block; width: 100%; height: 100%; }
/* barra de rolagem VISIVEL: a do Windows e sobreposta e some no escuro — se um painel
   rola, isso tem de ser perceptivel, nao adivinhavel */
#celulas { scrollbar-width: thin; scrollbar-color: ${T.borda} transparent; }
#celulas::-webkit-scrollbar { width: 10px; }
#celulas::-webkit-scrollbar-thumb { background: ${T.borda}; border-radius: 999px; }
.avisos { flex: none; display: grid; gap: .3rem; padding: .6rem 1.1rem .9rem; }
.avisos:empty { display: none; }
.aviso { margin: 0; font-size: .78rem; color: ${TOKENS.estado["⏸"]}; }
.aviso b { color: ${T.texto}; font-weight: 600; }
.aviso.nota { color: ${T.terciario}; }
.aviso.nota b { color: ${T.secundario}; }

/* --- 3D --- */
#cena { background:
    radial-gradient(70% 50% at 50% 0%, ${T.acento}1f 0%, transparent 70%),
    radial-gradient(50% 40% at 85% 100%, ${TOKENS.estado["🔵"]}18 0%, transparent 65%); }
#lateral { position: fixed; top: 5.25rem; right: 1.5rem; z-index: 2; width: 20rem;
  max-height: 70vh; overflow-y: auto; padding: 1.25rem 1.4rem; border-radius: .9rem;
  background: ${T.superficie}f2; border: 1px solid ${T.borda};
  box-shadow: 0 24px 60px -32px ${T.fundo}; }
#lateral .apagado { opacity: .1; }
#lateral h3 { margin: 0; font-size: 1.05rem; font-weight: 650; }
#lateral .meta { margin: .3rem 0 1rem; color: ${T.terciario}; font-size: .74rem;
  letter-spacing: .08em; text-transform: uppercase; }
#lateral ul { display: grid; gap: .35rem; }
#lateral button { margin-top: 1.1rem; background: none; border: 1px solid ${T.borda};
  color: ${T.terciario}; border-radius: .45rem; padding: .35rem .8rem; cursor: pointer; }
.rotulos { position: absolute; inset: 0; pointer-events: none; z-index: 2; }
.chip { position: absolute; top: 0; left: 0; padding: .22rem .6rem; border-radius: .45rem;
  background: ${T.fundo}e6; border: 1px solid ${T.borda}; border-left-width: 3px;
  color: ${T.texto}; font: 600 .78rem ui-sans-serif, system-ui, sans-serif;
  white-space: nowrap; transition: opacity .12s; will-change: transform; }
.chip.setor { background: none; border: none; color: ${T.terciario};
  font: 700 1.4rem ui-sans-serif, system-ui, sans-serif; letter-spacing: .2em; }
#ajuda { position: fixed; left: 50%; transform: translateX(-50%); bottom: 1.25rem;
  z-index: 2; padding: .5rem 1rem; border-radius: 999px; background: ${T.superficie}e6;
  border: 1px solid ${T.borda}; color: ${T.terciario}; font-size: .74rem;
  white-space: nowrap; overflow-x: auto; max-width: 94vw; }
#ajuda b { color: ${T.secundario}; font-weight: 600; }
`+`
/* --- valvula de seguranca: dashboard de viewport e promessa de tela grande.
   Abaixo do piso, insistir nela esconde informacao — entao vira documento rolavel. */
@media (max-height: 640px), (max-width: 900px) {
  body { height: auto; min-height: 100vh; overflow: auto; }
  .painel { grid-template-columns: minmax(0, 1fr); }
  .alma { max-height: none; overflow-y: visible; }
  .caixa { grid-template-rows: auto auto; }
  #celulas, .tela { overflow: visible; }
  .tela svg { max-height: none; }
}
`;
