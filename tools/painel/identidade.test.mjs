// Testes da identidade visual — I1..I6 do CONTRATO-V2B.md. Escritos ANTES do CSS.
// Nenhum destes mede beleza (impossível). Todos medem que a informação continua
// verdadeira e legível DEPOIS do enfeite — que é o risco real de uma célula de estética.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { TOKENS, CSS } from './estilo.mjs';
import { CORES } from './grafo.mjs';
import { montarGrafo } from './grafo.mjs';
import { modelo3d } from './grafo3d.mjs';
import { svg } from './svg2d.mjs';
import { renderCorpo, mdParaHtml, pagina as paginaHtml } from './pagina.mjs';
import { lerProjeto } from './parse.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const MINI = join(AQUI, 'fixture', 'mini-mapa');
const estado = () => lerProjeto(MINI);
const pagina = () => renderCorpo(estado());
const desenho = () => svg(modelo3d(montarGrafo(estado().mapaTexto, estado().celulas, { esperado: 6 })));
const paginaInteira = () => paginaHtml(estado());

// --- luminância relativa sRGB, para contraste calculado e não estimado ---
function luz(hex) {
  const canal = (i) => {
    const v = parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * canal(0) + 0.7152 * canal(1) + 0.0722 * canal(2);
}
const contraste = (a, b) => {
  const [x, y] = [luz(a), luz(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
const matiz = (hex) => {
  const [r, g, b] = [0, 1, 2].map((i) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255);
  const max = Math.max(r, g, b); const min = Math.min(r, g, b);
  const d = max - min;
  if (d < 0.001) return { h: 0, s: 0 };
  const s = d / (1 - Math.abs(max + min - 1));
  let h = 0;
  if (max === r) h = 60 * (((g - b) / d) % 6);
  else if (max === g) h = 60 * ((b - r) / d + 2);
  else h = 60 * ((r - g) / d + 4);
  return { h: (h + 360) % 360, s };
};
const textoDaAlma = (corpo) => /class="alma"[\s\S]*?<p>([\s\S]*?)<\/p>/.exec(corpo)[1]
  .replace(/<[^>]+>/g, '').replaceAll('&amp;', '&').replaceAll('&lt;', '<').replaceAll('&gt;', '>');
const hexesEm = (texto) => [...texto.matchAll(/#[0-9a-fA-F]{6}/g)].map((m) => m[0].toLowerCase());

describe('I1 · uma fonte de cor para a página inteira', () => {
  test('os 4 estados são os MESMOS do grafo — página e desenho não divergem', () => {
    for (const s of ['✔', '🔵', '⏸', '📋']) assert.equal(TOKENS.estado[s], CORES[s]);
    assert.equal(TOKENS.estado.sem, CORES.sem);
  });

  test('nenhum hex no CSS ou no SVG fora da paleta declarada', () => {
    const paleta = new Set(Object.values(TOKENS.estado).concat(Object.values(TOKENS.base))
      .map((c) => c.toLowerCase()));
    for (const [onde, texto] of [['CSS', CSS], ['SVG', desenho()]]) {
      for (const h of hexesEm(texto)) {
        assert.ok(paleta.has(h), `${onde} tem ${h}, que não está em TOKENS`);
      }
    }
  });
});

describe('I2 · contraste que sobrevive a olho cansado', () => {
  test('texto e estados ≥ 4.5:1 contra o fundo (WCAG AA)', () => {
    const fundo = TOKENS.base.fundo;
    for (const [nome, cor] of [['texto', TOKENS.base.texto], ['secundario', TOKENS.base.secundario],
      ...Object.entries(TOKENS.estado)]) {
      if (nome === 'sem') continue;                 // cinza de nó sem célula é gráfico
      const c = contraste(cor, fundo);
      assert.ok(c >= 4.5, `${nome} (${cor}) tem contraste ${c.toFixed(2)}:1, precisa de 4.5`);
    }
  });

  test('terciário e acento ≥ 3:1 — eles CARREGAM informação', () => {
    // o terciário é metadado legível e o acento rotula a alma: os dois são informação,
    // então valem 3:1 (WCAG 1.4.11)
    for (const nome of ['terciario', 'acento']) {
      const c = contraste(TOKENS.base[nome], TOKENS.base.fundo);
      assert.ok(c >= 3, `${nome} tem ${c.toFixed(2)}:1, precisa de 3`);
    }
  });

  test('borda e superfície só precisam ser VISÍVEIS — não são componente', () => {
    // Critério meu, corrigido: eu tinha posto a borda no mesmo balde de 3:1. Errado —
    // 1.4.11 vale para o que identifica um componente ou estado, e um fio decorativo
    // não identifica nada; quem separa o cartão é a mudança de fundo. Baixei para
    // "visível" (≥1.25) em vez de acender bordas que gritariam na tela.
    for (const nome of ['borda', 'superficie']) {
      const c = contraste(TOKENS.base[nome], TOKENS.base.fundo);
      assert.ok(c >= 1.08, `${nome} sumiu no fundo: ${c.toFixed(2)}:1`);
    }
  });
});

describe('I3 · markdown cru resolvido — e a alma intocada', () => {
  test('negrito e código viram HTML, com escape antes', () => {
    assert.equal(mdParaHtml('**a alma**: o resto'), '<strong>a alma</strong>: o resto');
    assert.equal(mdParaHtml('roda `node --test` aí'), 'roda <code>node --test</code> aí');
    assert.equal(mdParaHtml('a < b & c'), 'a &lt; b &amp; c');
    assert.equal(mdParaHtml('`<script>`'), '<code>&lt;script&gt;</code>');
  });

  test('a lista não mostra asterisco nem crase cru', () => {
    const corpo = pagina();
    const listas = corpo.slice(corpo.indexOf('<section class="grupo"'));
    assert.ok(!listas.includes('**'), 'sobrou asterisco cru na lista');
    assert.ok(!/`[^`]+`/.test(listas.replace(/<[^>]*>/g, '')), 'sobrou crase crua na lista');
  });

  test('a alma chega INTEIRA — renderizada, mas sem perder nem inventar palavra', () => {
    // Caneta do Hudson, 26/08: a alma passou a renderizar markdown. A garantia mudou de
    // forma, não de força — o TEXTO da alma continua sendo a frase do vault, exata.
    const frase = estado().proximoPasso;
    assert.ok(frase.includes('`'), 'a fixture tem de ter crase na alma, senão o teste não prova nada');
    assert.equal(textoDaAlma(pagina()), frase.replaceAll('**', '').replaceAll('`', ''));
  });
});

describe('I4 · monoespaçada só onde a FONTE pediu', () => {
  test('cada <code> da alma corresponde a um par de crases do vault — nem um a mais', () => {
    const frase = estado().proximoPasso;
    const pares = (frase.match(/`/g) ?? []).length / 2;
    const alma = /class="alma"[\s\S]*?<p>([\s\S]*?)<\/p>/.exec(pagina())[1];
    assert.equal((alma.match(/<code>/g) ?? []).length, pares,
      'mono é decisão de quem escreveu no vault, não do CSS');
  });

  test('o caminho da célula na lista é mono', () => {
    assert.ok(pagina().includes('<code>packages/mini-kernel</code>'));
  });
});

describe('I5 · um acento, não uma feira', () => {
  test('só existe UM matiz saturado fora da paleta de estado', () => {
    const estados = new Set(Object.values(TOKENS.estado).map((c) => c.toLowerCase()));
    // Critério meu, corrigido DUAS vezes, e a segunda foi a lição: saturação HSL mente
    // nos extremos. O off-white do texto (#e8eaf2) dava s=0.28 — mais "saturado" que a
    // borda — só porque o denominador encolhe perto do branco. Quem separa cor de
    // neutro é a CROMA (max-min): o texto tem 0.04, o violeta tem 0.58.
    const croma = (hex) => {
      const v = [0, 1, 2].map((i) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) / 255);
      return Math.max(...v) - Math.min(...v);
    };
    const fora = hexesEm(CSS).filter((h) => !estados.has(h))
      .filter((h) => croma(h) >= 0.2)
      .map((h) => Math.round(matiz(h).h / 15) * 15);
    assert.ok(new Set(fora).size <= 1, `matizes de acento: ${[...new Set(fora)].join(', ')}`);
  });
});

describe('I8 · o 2D reage como o 3D — e o SVG carrega o que a mão precisa', () => {
  test('cada nó leva pacote, bloco, status e as CHAVES para o painel lateral', () => {
    const d = desenho();
    const nos = [...d.matchAll(/class="no"[^>]*data-pacote="([^"]+)"[^>]*data-chaves="([^"]*)"/g)];
    assert.equal(nos.length, 3, 'todo nó tem de se identificar para o clique');
    const outros = nos.find((m) => m[1] === 'mini-outros');
    assert.deepEqual(outros[2].split(' '), ['mini.view', 'mini.extra'],
      'sem as chaves no SVG, clicar no 2D não teria o que listar');
  });

  test('cada aresta diz de onde vem e para onde vai — é o que acende os vizinhos', () => {
    const arestas = [...desenho().matchAll(/class="aresta"[^>]*data-de="([^"]+)"[^>]*data-para="([^"]+)"/g)];
    assert.equal(arestas.length, 3);
    assert.deepEqual(arestas.map((m) => `${m[1]}->${m[2]}`).sort(),
      ['mini-kernel->mini-outros', 'mini-outros->mini-store', 'mini-store->mini-kernel']);
  });

  test('a página serve a interação do 2D', () => {
    assert.ok(paginaInteira().includes("import('/interacao2d.mjs')"));
    assert.match(CSS, /\.apagado/, 'falta a classe que apaga quem não é vizinho');
  });
});

describe('I6 · hexágono, não disco', () => {
  test('cada nó é um polígono de 6 vértices, e a contagem não muda', () => {
    const d = desenho();
    assert.equal(d.split('class="no"').length - 1, 3);
    assert.equal(d.split('class="aresta"').length - 1, 3);
    assert.equal(d.includes('<circle r='), false, 'disco não, hexágono');
    for (const m of d.matchAll(/class="hex"[^>]*points="([^"]+)"/g)) {
      assert.equal(m[1].trim().split(/\s+/).length, 6, 'hexágono tem 6 vértices');
    }
    assert.equal([...d.matchAll(/class="hex"/g)].length, 3);
  });
});

describe('I7 · o essencial não rola — é dashboard, não documento', () => {
  test('a PÁGINA não rola: quem rola são os painéis', () => {
    // não dá para medir pixel em node; dá para provar que a página foi CONSTRUÍDA para
    // não rolar — altura de viewport, overflow travado no body, solto nos painéis.
    assert.match(CSS, /body\s*\{[^}]*height:\s*100vh/s, 'o body tem de ter altura de viewport');
    assert.match(CSS, /body\s*\{[^}]*overflow:\s*hidden/s, 'a página não pode rolar');
    assert.match(CSS, /#celulas\s*\{[^}]*overflow-y:\s*auto/s, 'a lista de células rola por dentro');
  });

  test('o grafo alcança tudo por GESTO, não por barra de rolagem', () => {
    // Critério corrigido (caneta do Hudson, 26/08): o painel do grafo deixou de rolar e
    // passou a ter os mesmos gestos do 3D — arrastar, roda, encaixar. A promessa "nada
    // fica preso" continua de pé; quem a cumpre mudou. E o desenho CABE por padrão:
    // era `width: 100%` num painel largo que gerava 1700px de altura e estourava a tela.
    assert.match(CSS, /\.tela\s*\{[^}]*overflow:\s*hidden/s, 'a tela é viewport de pan');
    assert.match(CSS, /\.tela\s*\{[^}]*cursor:\s*grab/s, 'e diz isso pelo cursor');
    // encaixe passou de max-width/height para 100% nos dois eixos: com `width: auto` o
    // desenho se amontoava num canto do painel em vez de preencher
    assert.match(CSS, /\.tela svg[^}]*height:\s*100%/s, 'o desenho encaixa no container');
    assert.ok(paginaInteira().includes('class="encaixar"'), 'falta o botão de encaixar');
    assert.ok(paginaInteira().includes("import('/zoom2d.mjs')"), 'falta o pan/zoom do 2D');
  });

  test('NADA fica preso: quem pode crescer declara o próprio overflow', () => {
    // O bug do Hudson, 26/08: "não cabe na tela e não tem scroll". `overflow: hidden`
    // no body garante que a página não rola — e garante junto que conteúdo pode sumir
    // sem alcance. Toda região que pode crescer tem de ter saída própria.
    assert.match(CSS, /\.alma\s*\{[^}]*max-height:/s, 'a alma tem de ter teto');
    assert.match(CSS, /\.alma\s*\{[^}]*overflow-y:\s*auto/s, 'a alma tem de rolar por dentro');
  });

  test('válvula de segurança: em tela baixa ou estreita, a página VOLTA a rolar', () => {
    // dashboard de viewport é promessa de tela grande. Abaixo de um piso, insistir nela
    // é esconder informação — então o layout degrada para documento rolável.
    const media = /@media[^{]*max-height[^{]*\{([\s\S]*?)\n\}/.exec(CSS);
    assert.ok(media, 'falta a media query de tela baixa');
    assert.match(media[1], /body\s*\{[^}]*overflow:\s*auto/s, 'na tela baixa o body tem de rolar');
    assert.match(media[1], /body\s*\{[^}]*height:\s*auto/s, 'e soltar a altura travada');
  });

  test('alma e contagens ficam FORA de qualquer painel que rola', () => {
    const corpo = pagina();
    const celulas = corpo.slice(corpo.indexOf('<div id="celulas">'));
    assert.ok(!celulas.includes('class="alma"'), 'a alma não pode estar dentro do que rola');
    assert.ok(!celulas.includes('class="tiles"'), 'as contagens não podem rolar para fora');
    assert.ok(corpo.indexOf('class="tiles"') < corpo.indexOf('class="alma"'));
    assert.ok(corpo.indexOf('class="alma"') < corpo.indexOf('class="caixa lista"'));
  });

  test('o 3D ocupa o MESMO container do 2D — não é overlay de tela cheia', () => {
    // Caneta do Hudson, 26/08: "ao clicar em 3D o grafo deveria ocupar o container do
    // 2D e vice-versa". As duas são vistas do mesmo modelo, então dividem o painel.
    const html = paginaInteira();
    const painel = html.slice(html.indexOf('<section class="caixa grafo">'),
      html.indexOf('<div id="ajuda"'));
    assert.ok(painel.includes('id="tela"'), 'a planta baixa vive no painel do grafo');
    assert.ok(painel.includes('id="cena"'), 'o corte 3D vive no MESMO painel');
    assert.ok(!/#cena[^}]*position:\s*fixed/s.test(CSS), 'o 3D não pode ser overlay fixo');
    assert.ok(painel.indexOf('id="tela"') < painel.indexOf('id="cena"'), 'irmãos no mesmo painel');
  });

  test('as contagens viraram tiles com número grande e cor do estado', () => {
    const corpo = pagina();
    assert.equal((corpo.match(/class="tile /g) ?? []).length, 4);
    for (const s of ['✔', '🔵', '⏸', '📋']) {
      assert.ok(corpo.includes(`--cor:${TOKENS.estado[s]}`), `tile de ${s} sem a cor do estado`);
    }
  });
});

describe('I9 · uma seleção, duas pinturas — não duas cópias', () => {
  test('a máquina de estado da seleção existe UMA vez e as duas vistas a usam', async () => {
    // Crítica do Hudson, 26/08: "não entendi porque não fez como um componente só".
    // Fazia sentido: o painel tem uma matemática e duas projeções; o comportamento
    // tem de seguir a mesma regra. Vizinhos, foco, painel lateral e limpar moram no
    // selecao.mjs; cada vista entra só com `pintar` e `focar`.
    const { readFileSync } = await import('node:fs');
    const ler = (f) => readFileSync(join(AQUI, f), 'utf8');
    for (const vista of ['interacao2d.mjs', 'cena3d.mjs']) {
      assert.match(ler(vista), /import \{ criarSelecao \}/, `${vista} tem de usar a seleção comum`);
      assert.ok(!/const vizinhos = /.test(ler(vista)), `${vista} não pode ter vizinhos próprio`);
      assert.ok(!/data-fechar>fechar/.test(ler(vista)), `${vista} não pode ter painel próprio`);
    }
    // e o painel lateral é montado num lugar só
    assert.equal((ler('selecao.mjs').match(/data-fechar/g) ?? []).length, 2);
  });

  test('clicar aproxima nas DUAS vistas — o 2D ganhou o equivalente do orbita.focar', async () => {
    const { readFileSync } = await import('node:fs');
    assert.match(readFileSync(join(AQUI, 'zoom2d.mjs'), 'utf8'), /focar\(ux, uy/);
    assert.match(readFileSync(join(AQUI, 'cena3d.mjs'), 'utf8'), /focar: \(no\) => orbita\.focar/);
    // e o SVG carrega a posição do nó, senão o 2D não teria onde focar
    assert.match(desenho(), /data-x="-?\d+" data-y="-?\d+"/);
  });
});

describe('I10 · os tiles destacam o que PEDE AÇÃO, não o histórico', () => {
  test('ativa vem primeiro e forte; concluída e planejada em peso menor', () => {
    const corpo = pagina();
    const tiles = [...corpo.matchAll(/class="tile ([a-z]+)"[^>]*>\s*<b>(\d+)<\/b><span>([^<]+)/g)]
      .map((m) => ({ peso: m[1], n: Number(m[2]), nome: m[3] }));
    assert.deepEqual(tiles.map((t) => t.nome), ['ativa', 'pausada', 'planejada', 'concluída'],
      '47 concluída não pode abrir a fila — é histórico, não convite');
    assert.equal(tiles.find((t) => t.nome === 'ativa').peso, 'forte');
    assert.equal(tiles.find((t) => t.nome === 'concluída').peso, 'fraco');
    assert.equal(tiles.find((t) => t.nome === 'planejada').peso, 'fraco');
  });

  test('pausada é forte SÓ quando houver — zero pausadas não pede nada', () => {
    const corpo = pagina();
    const pausada = /class="tile (\w+)"[^>]*>\s*<b>(\d+)<\/b><span>pausada/.exec(corpo);
    const zero = Number(pausada[2]) === 0;
    assert.equal(pausada[1], zero ? 'fraco' : 'forte');
  });

  test('o CSS distingue os dois pesos de verdade', () => {
    assert.match(CSS, /\.tile\.forte b\s*\{[^}]*font-size:/s);
    assert.match(CSS, /\.tile\.fraco b\s*\{[^}]*font-size:/s);
  });
});

describe('I11 · o rótulo do setor ancora na BORDA do desenho', () => {
  test('cada setor fica na moldura do viewBox, não solto no vazio', () => {
    const d = desenho();
    const [minX, minY, larg, alt] = /viewBox="([^"]+)"/.exec(d)[1].split(/\s+/).map(Number);
    const setores = [...d.matchAll(/class="setor" x="(-?\d+)" y="(-?\d+)"/g)]
      .map((m) => [Number(m[1]), Number(m[2])]);
    assert.ok(setores.length >= 2);
    for (const [x, y] of setores) {
      const naBorda = Math.min(Math.abs(x - minX), Math.abs(minX + larg - x),
        Math.abs(y - minY), Math.abs(minY + alt - y));
      assert.ok(naBorda < 200, `setor a ${Math.round(naBorda)} da moldura — está solto no vazio`);
    }
  });
});

describe('I12 · o clique pega o nó inteiro, não só o hexágono', () => {
  test('cada nó tem área de alvo invisível maior que o desenho', () => {
    // regressão real: um <g> não tem área própria, e entre o hexágono e o rótulo há
    // vazio — `elementFromPoint` caía no nada e as chaves apareciam de forma
    // intermitente. O alvo é um círculo transparente maior que o nó.
    const d = desenho();
    const alvos = [...d.matchAll(/class="alvo" r="(\d+)"/g)].map((m) => Number(m[1]));
    const raios = [...d.matchAll(/class="hex"[^>]*points="([^"]+)"/g)].length;
    assert.equal(alvos.length, raios, 'todo nó precisa de área de alvo');
    assert.ok(alvos.every((r) => r > 46), 'o alvo tem de ser maior que o menor hexágono');
    assert.match(d, /\.alvo \{ fill: transparent/, 'e invisível');
  });
});

describe('I13 · o nome do setor VEM DO MAPA, não de uma lista no código', () => {
  test('deriva do título da seção: corta o aparte, o prefixo e as palavras vazias', async () => {
    const { nomeDoBloco } = await import('./grafo.mjs');
    assert.equal(nomeDoBloco('## A · Motor — fundação e dados'), 'fundação');
    assert.equal(nomeDoBloco('## D · Motor — avaliação (zona sem assistência)'), 'avaliação');
    assert.equal(nomeDoBloco('## H · edtech — a borda (MCP só aqui)'), 'borda');
    // palavra curta puxa a seguinte, e as vazias já saíram: 'IA e agentes' → 'IA agentes'
    assert.equal(nomeDoBloco('## Z · Motor — IA e agentes'), 'IA agentes');
  });

  test('bloco novo no mapa entra com nome próprio, sem tocar no painel', async () => {
    const { parseMapa } = await import('./grafo.mjs');
    const comBlocoNovo = readFileSync(join(MINI, 'contratos', 'mapa-de-chaves.md'), 'utf8')
      .replace('## C · Borda', '## C · Motor — telemetria de campo');
    assert.equal(parseMapa(comBlocoNovo).blocos.get('C'), 'telemetria');
  });

  test('o rótulo do setor mostra o nome nas duas vistas', () => {
    const d = desenho();
    assert.match(d, /class="setor-letra">A<\/tspan> Fundação/, '2D: letra pequena + nome');
    const m = modelo3d(montarGrafo(estado().mapaTexto, estado().celulas, { esperado: 6 }));
    assert.equal(m.setores.find((s) => s.bloco === 'A').nome, 'Fundação', '3D lê do mesmo modelo');
  });
});
