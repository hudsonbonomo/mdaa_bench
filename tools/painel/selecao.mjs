// selecao.mjs — roda no BROWSER. A MÁQUINA DE ESTADO da seleção, uma só para as duas
// vistas. O painel tem uma matemática (grafo3d) e duas projeções (svg2d, cena3d);
// o comportamento segue a mesma regra: uma seleção, duas pinturas.
//
// Quem varia entre as vistas é só COMO se pinta e COMO se aproxima. Isso entra por
// adaptador; o resto — vizinhos, foco, painel lateral, limpar — mora aqui e é idêntico.
//
// Nasceu de uma pergunta do Hudson (26/08): "não entendi porque não fez como um
// componente só, faz mais sentido". Fazia. O 3D nasceu fechado na v2a e o 2D espelhou
// a lógica na v2b — deriva incremental, não decisão.

export function criarSelecao({ lateral, arestas, pintar, focar }) {
  let focado = null;

  const vizinhos = (pacote) => {
    const perto = new Set([pacote]);
    for (const a of arestas()) {
      if (a.de === pacote) perto.add(a.para);
      if (a.para === pacote) perto.add(a.de);
    }
    return perto;
  };

  const mostrar = (no) => {
    lateral.hidden = false;
    lateral.innerHTML = `<h3>${no.pacote}</h3>
      <p class="meta">bloco ${no.bloco} · ${no.status || 'sem célula'}
        · ${no.chaves.length} chaves · ${no.dependentes} dependentes</p>
      <ul>${no.chaves.map((k) => `<li><code>${k}</code></li>`).join('')}</ul>
      <button type="button" data-fechar>fechar</button>`;
    lateral.querySelector('[data-fechar]').addEventListener('click', () => limpar());
  };

  function limpar() {
    focado = null;
    lateral.hidden = true;
    pintar(null);
  }

  return {
    // passar o mouse: destaca sem fixar; sem alvo, volta para o que está focado
    sobre(no) { pintar(no ? vizinhos(no.pacote) : (focado ? vizinhos(focado) : null)); },

    // clicar: fixa, abre as chaves e APROXIMA — igual nas duas vistas
    clicar(no) {
      if (!no) return limpar();
      focado = no.pacote;
      pintar(vizinhos(focado));
      mostrar(no);
      focar?.(no);
    },

    limpar,
    // o SSE troca o desenho a cada escrita no vault: o destaque tem de voltar sozinho
    reaplicar() { pintar(focado ? vizinhos(focado) : null); },
    focado: () => focado,
  };
}
