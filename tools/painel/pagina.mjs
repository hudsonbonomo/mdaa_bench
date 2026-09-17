// pagina.mjs — o HTML autocontido (sem CDN, sem build).
//
// ARQUITETURA (v2b, 3ª rodada — caneta do Hudson): a cena 3D ocupa o MESMO container do
// SVG 2D. Elas são duas vistas do mesmo modelo, então dividem o mesmo painel; o botão do
// cabeçalho troca qual está à mostra. Isso obriga o SSE a parar de trocar o `innerHTML`
// do mundo: ele atualiza PEDAÇOS nomeados, e o `#cena` — que segura o canvas e a câmera
// — nunca é tocado.
import { STATUS } from './parse.mjs';
import { montarGrafo } from './grafo.mjs';
import { modelo3d } from './grafo3d.mjs';
import { svg } from './svg2d.mjs';
import { CSS, TOKENS } from './estilo.mjs';

const ORDEM = ['🔵', '⏸', '📋', '✔'];   // na página: ativa primeiro, concluída por último
// Os tiles seguem a MESMA ordem, e o peso segue a AÇÃO: 47 concluída é histórico, não
// convite. Forte é o que pede alguma coisa de você agora.
const forte = (s, n) => (s === '🔵' || (s === '⏸' && n > 0) ? 'forte' : 'fraco');
const NOMES = { '🔵': 'ativa', '⏸': 'pausada', '📋': 'planejada', '✔': 'concluída' };

export function escapar(t) {
  return String(t).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

// Markdown mínimo: negrito e código, nada além. Escapa ANTES de marcar — sem isso uma
// tag escrita no vault viraria elemento na página.
export function mdParaHtml(texto) {
  return escapar(texto)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

function linhaCelula(c) {
  const passo = c.proximoPasso && c.proximoPasso !== '—'
    ? `<span class="passo">${mdParaHtml(c.proximoPasso)}</span>` : '';
  return `<li><span class="nome">${mdParaHtml(c.nome)}</span>
    <span class="area">${mdParaHtml(c.area)}</span>${passo}</li>`;
}

// --- os pedaços do painel do grafo, cada um atualizável sozinho ---
function pedacosDoGrafo(e) {
  if (!e.temMapa) return { rotulo: 'sem grafo: mapa ausente', tela: '', avisos: '' };
  let g;
  try { g = montarGrafo(e.mapaTexto, e.celulas); } catch (erro) {
    return { rotulo: `grafo NÃO desenhado — ${escapar(erro.message)}`, tela: '', avisos: '' };
  }
  const divergencia = g.divergenciaDeContagem
    ? `<p class="aviso">a prosa do mapa diz <b>${g.prosaDiz} pacotes</b>, a tabela tem
       <b>${g.nos.length}</b> — desenhados os ${g.nos.length} da tabela.</p>` : '';
  const naoCasadas = g.naoCasadas.length
    ? `<p class="aviso">NÃO CASADA: ${g.naoCasadas.map((n) =>
      `<b>packages/${escapar(n.pacote)}</b> (${n.status})`).join(' · ')} — não existe no mapa</p>` : '';
  // pacote sem chave é estado legítimo (double de teste), não erro — mas some do desenho
  // por não ter bloco, então tem de aparecer dito, nunca sumir calado
  const semChave = g.semChave.length
    ? `<p class="aviso nota">sem chave, fora do grafo: ${g.semChave.map((p) =>
      `<b>${escapar(p)}</b>`).join(' · ')}</p>` : '';
  return {
    rotulo: `${g.nos.length} pacotes · ${g.chaves} chaves · ${g.arestas.length} injeções`,
    tela: svg(modelo3d(g)),
    avisos: divergencia + naoCasadas + semChave,
  };
}

// DASHBOARD: topo com tiles · faixa da alma · lista à esquerda · grafo à direita.
// Quem rola são os painéis, nunca o essencial (I7).
export function renderCorpo(e) {
  const tiles = ORDEM.map((s) => `<div class="tile ${forte(s, e.contagens[s])}" style="--cor:${TOKENS.estado[s]}">
    <b>${e.contagens[s]}</b><span>${NOMES[s]}</span></div>`).join('');
  const grupos = ORDEM.filter((s) => e.celulas.some((c) => c.status === s)).map((s) => `
    <section class="grupo">
      <h2>${s} ${NOMES[s]} <span class="qtd">${e.contagens[s]}</span></h2>
      <ul>${e.celulas.filter((c) => c.status === s).map(linhaCelula).join('')}</ul>
    </section>`).join('');
  const outras = e.celulas.filter((c) => !STATUS.includes(c.status));
  const resto = outras.length
    ? `<section class="grupo"><h2>sem status reconhecido <span class="qtd">${outras.length}</span></h2>
       <ul>${outras.map(linhaCelula).join('')}</ul></section>` : '';
  return `
    <header>
      <h1>${escapar(e.projeto)}</h1>
      <div class="tiles">${tiles}</div>
    </header>
    <section class="alma">
      <div class="rotulo">➜ PRÓXIMO PASSO${e.celulaAtual ? ` · ${escapar(e.celulaAtual)}` : ''}</div>
      <p>${e.proximoPasso ? mdParaHtml(e.proximoPasso) : 'nenhum próximo passo anotado'}</p>
    </section>
    <section class="caixa lista">
      <div class="rotulo">células · ${escapar(e.estado)}</div>
      <div id="celulas">${grupos}${resto}</div>
    </section>`;
}

export function pagina(estado) {
  const g = pedacosDoGrafo(estado);
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>${escapar(estado.projeto)} — painel</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>${CSS}</style></head>
<body>
<main id="corpo">${renderCorpo(estado)}</main>
<section class="caixa grafo">
  <div class="rotulo"><span id="grafo-rotulo">${g.rotulo}</span>
    <span id="grafo-vista">planta baixa</span>
    <button class="encaixar" type="button" title="encaixar na tela">⤢ encaixar</button>
    <button class="vista" type="button">3D</button></div>
  <div class="tela" id="tela">${g.tela}</div>
  <div class="tela" id="cena" hidden></div>
  <div class="avisos" id="grafo-avisos">${g.avisos}</div>
</section>
<div id="ajuda">arrastar <b>move</b> · roda <b>zoom</b> · <b>⤢ encaixar</b> volta ao início<span id="ajuda3d" hidden> · no 3D: arrastar <b>gira</b>, botão direito <b>arrasta</b>, clique <b>foca</b>, <b>R</b> reseta</span></div>
<aside id="lateral" hidden></aside>
<script type="module">
  const botao = document.querySelector('.vista');
  const tela = document.getElementById('tela');
  const cena3d = document.getElementById('cena');
  let cena = null;

  // a planta baixa ganha os MESMOS gestos do corte: arrastar, roda, encaixar
  const { criarZoom2d } = await import('/zoom2d.mjs');
  const zoom = criarZoom2d(tela);
  const { criarInteracao2d } = await import('/interacao2d.mjs');
  const toque = criarInteracao2d(tela, document.getElementById('lateral'), zoom);

  document.querySelector('.encaixar').addEventListener('click', () => {
    if (document.body.dataset.vista === '3d') cena?.encaixar();
    else zoom.encaixar();
  });

  async function aplicar(vista) {
    document.body.dataset.vista = vista;
    tela.hidden = vista === '3d';
    cena3d.hidden = vista !== '3d';
    document.getElementById('ajuda3d').hidden = vista !== '3d';
    document.getElementById('grafo-vista').textContent = vista === '3d' ? 'corte 3D' : 'planta baixa';
    botao.textContent = vista === '3d' ? '2D' : '3D';
    localStorage.setItem('painel-vista', vista);
    document.getElementById('lateral').hidden = true;
    if (vista === '3d' && !cena) {
      const { montarCena } = await import('/cena3d.mjs');
      cena = await montarCena(cena3d, document.getElementById('lateral'));
    }
  }

  botao.addEventListener('click', () => aplicar(document.body.dataset.vista === '3d' ? '2d' : '3d'));
  aplicar(localStorage.getItem('painel-vista') === '3d' ? '3d' : '2d');

  // O SSE atualiza PEDAÇOS nomeados. Trocar o innerHTML do mundo destruiria o canvas
  // e a câmera do 3D — que é justamente o que não pode piscar enquanto você anota.
  const fonte = new EventSource('/eventos');
  fonte.addEventListener('estado', (e) => {
    const d = JSON.parse(e.data);
    document.getElementById('corpo').innerHTML = d.html;
    document.getElementById('grafo-rotulo').textContent = d.rotulo;
    document.getElementById('grafo-avisos').innerHTML = d.avisos;
    tela.innerHTML = d.tela;
    zoom.aplicar();             // a ampliação sobrevive à anotação
    toque.aplicar();            // e o destaque do nó focado também
    cena?.atualizar();          // o 3D repinta as cores sem mexer na câmera
  });
</script>
</body></html>`;
}

// O que o SSE manda: os pedaços nomeados, nunca a página inteira.
export function fragmentos(estado) {
  return { html: renderCorpo(estado), ...pedacosDoGrafo(estado) };
}
