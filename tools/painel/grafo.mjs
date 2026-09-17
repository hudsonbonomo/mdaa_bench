// grafo.mjs — lê contratos/mapa-de-chaves.md e monta o GRAFO DE PACOTES (não das 45
// chaves): quem é cada pacote, de que bloco, com que cor, e quais arestas de injeção.
// O layout mora no grafo3d.mjs e o desenho no svg2d.mjs — aqui é só a leitura do contrato.
// Cravadas em vault/estado/celulas/painel-v1-grafo.md.

// Paleta da v2b: contraste contra o fundo conferido por teste (I2), nao estimado.
// TOKENS.estado aponta para AQUI — uma fonte de cor para pagina, SVG e cena 3D.
export const CORES = { '✔': '#3ddc97', '🔵': '#4aa8ff', '⏸': '#f5a524', '📋': '#8892ab', sem: '#3a4049' };
const ESCAPE = '\u0000';

function fatiar(linha) {
  const p = linha.replaceAll('\\|', ESCAPE).split('|');
  if (p[0].trim() === '') p.shift();
  if (p.length && p[p.length - 1].trim() === '') p.pop();
  return p.map((c) => c.replaceAll(ESCAPE, '|').trim());
}

// Chave = token entre crases COM ponto e sem espaço. 'static' e 'derived-from-catalog'
// não passam; `nll.cell-catalog` passa. Nunca fatiar por '·' (cravada 4).
function chavesEm(celula) {
  const achadas = [];
  let dentro = false; let atual = '';
  for (const ch of celula) {
    if (ch === '`') {
      if (dentro && atual.includes('.') && !atual.includes(' ')) achadas.push(atual);
      dentro = !dentro; atual = '';
    } else if (dentro) atual += ch;
  }
  return achadas;
}

// Nome curto do bloco, DERIVADO do título da seção — nunca uma lista no código. Bloco
// novo no mapa entra com nome próprio sem ninguém tocar no painel.
// '## E · Motor — superfícies de leitura' → 'superfícies'
export function nomeDoBloco(titulo) {
  const IGNORA = new Set(['de', 'da', 'do', 'e', 'o', 'a', 'os', 'as', 'em', 'no', 'na', 'que']);
  let t = titulo.slice(titulo.indexOf('·') + 1);
  const parenteses = t.indexOf('(');
  if (parenteses >= 0) t = t.slice(0, parenteses);          // corta o aparte
  const travessao = t.indexOf('—');
  if (travessao >= 0) t = t.slice(travessao + 1);           // 'Motor —' / 'edtech —' fora
  const palavras = t.trim().split(/\s+/).filter((p) => p && !IGNORA.has(p.toLowerCase()));
  if (!palavras.length) return '';
  // primeira palavra basta quando ela já distingue; senão, duas
  return palavras[0].length >= 4 ? palavras[0] : palavras.slice(0, 2).join(' ');
}

export function parseMapa(texto) {
  const chaves = new Map();
  const pacotes = new Map();
  const blocos = new Map();          // letra → nome curto, vindo do próprio mapa
  let bloco = null; let modo = null; let col = null;
  let prosaDiz = null; let prosaChaves = null;

  for (const bruta of texto.split('\n')) {
    const linha = bruta.trim();
    if (prosaChaves === null && linha.includes(' chaves')) {
      const antes = linha.slice(0, linha.indexOf(' chaves')).split(' ');
      const n = Number(antes[antes.length - 1]);
      if (Number.isInteger(n)) prosaChaves = n;
    }
    if (prosaDiz === null && linha.includes(' pacotes')) {
      const antes = linha.slice(0, linha.indexOf(' pacotes')).split(' ');
      const n = Number(antes[antes.length - 1]);
      if (Number.isInteger(n)) prosaDiz = n;
    }
    if (linha.startsWith('## ')) {
      const letra = linha.slice(3).split(' ')[0];
      bloco = letra.length === 1 && letra >= 'A' && letra <= 'H' ? letra : null;
      if (bloco) blocos.set(bloco, nomeDoBloco(linha));
      modo = null; col = null; continue;
    }
    if (linha.startsWith('### ')) { modo = null; col = null; continue; }
    if (!linha.startsWith('|')) { col = null; continue; }
    const partes = fatiar(linha);
    if (partes.every((c) => c.length >= 3 && /^:?-+:?$/.test(c))) continue;
    if (col === null) {
      col = {};
      // casamento EXATO: 'Chaves'.startsWith('Chave') é true e faria a tabela de
      // pacotes se passar por tabela de chaves — os pacotes sumiriam em silêncio
      partes.forEach((c, i) => {
        if (c === 'Chave') col.chave = i;
        else if (c === 'Injeta') col.injeta = i;
        else if (c === 'Pacote') col.pacote = i;
        else if (c === 'Chaves') col.chaves = i;
      });
      modo = col.chave !== undefined ? 'chaves' : (col.pacote !== undefined ? 'pacotes' : 'ignorar');
      continue;
    }
    if (modo === 'chaves' && bloco) {
      const nome = chavesEm(partes[col.chave] ?? '')[0];
      if (nome) chaves.set(nome, { bloco, injeta: chavesEm(partes[col.injeta] ?? '') });
    } else if (modo === 'pacotes') {
      const nome = (partes[col.pacote] ?? '').split('`')[1];
      // corta a anotação depois do travessão: ela CITA chave de outro pacote para
      // dizer que não é dela ('provider de X, não chave nova')
      const cel = (partes[col.chaves] ?? '').split(' — ')[0];
      if (nome) pacotes.set(nome, chavesEm(cel));
    }
  }
  return { chaves, pacotes, blocos, prosaDiz, prosaChaves };
}

export function montarGrafo(texto, celulas = [], opcoes = {}) {
  const { chaves, pacotes, blocos, prosaDiz, prosaChaves } = parseMapa(texto);
  // O painel recebe o PROJETO como argumento: a contagem esperada vem da prosa do próprio
  // mapa ("45 chaves em 17 pacotes"), nunca de um 45 cravado no código. A cravada é
  // "não perder chave em silêncio" — 45 é a contagem DESTE projeto, não do mundo.
  const esperado = opcoes.esperado ?? prosaChaves ?? chaves.size;
  if (chaves.size !== esperado) {
    throw new Error(`o mapa tem ${chaves.size} chaves, esperava ${esperado} — parser perdeu chave ou o contrato mudou`);
  }
  const dono = new Map();
  for (const [p, ks] of pacotes) for (const k of ks) dono.set(k, p);
  // Pacote citando chave que não existe na tabela de chaves: isso É divergência de
  // contrato e falha ALTO, nomeando os dois lados. Sem esta checagem virava um
  // TypeError cru em `chaves.get(...).bloco` — erro que não ensina nada a ninguém.
  for (const [p, ks] of pacotes) {
    const fantasmas = ks.filter((k) => !chaves.has(k));
    if (fantasmas.length) {
      throw new Error(`o pacote ${p} cita chave que não existe na tabela: ${fantasmas.join(', ')}`);
    }
  }

  const orfas = [...chaves.keys()].filter((k) => !dono.has(k));
  if (orfas.length) throw new Error(`chave sem pacote no mapa: ${orfas.join(', ')}`);

  // Pacote SEM chave nenhuma é estado LEGÍTIMO, não divergência: `nll-event-log-fixtures`
  // é o double in-memory da C3, fora do que a composição de produção alcança (N3). Ele
  // não tem bloco porque não tem chave — então não pode virar nó. Aparece nos avisos,
  // pela mesma doutrina do NÃO CASADA: expor, nunca sumir e nunca estourar.
  const semChave = [...pacotes].filter(([, ks]) => ks.length === 0).map(([p]) => p);
  const comChave = [...pacotes].filter(([, ks]) => ks.length > 0);

  const status = new Map();
  const naoCasadas = [];
  for (const c of celulas) {
    const i = (c.area ?? '').indexOf('packages/');
    if (i < 0) continue;
    let nome = '';
    for (const ch of c.area.slice(i + 9)) { if (/[a-z0-9-]/.test(ch)) nome += ch; else break; }
    // '`packages/`' sozinho é a PASTA (a linha da C3), não uma referência a pacote:
    // marcá-la NÃO CASADA encheria a página de ruído e esvaziaria o marcador
    if (nome === '') continue;
    // dedupe: duas células podem apontar para o mesmo pacote fora do mapa (hoje a C6 e
    // a célula do carimbo apontam ambas para packages/nll-event-log). Repetir o aviso
    // na página é ruído; a primeira célula que referenciou basta para achar a origem.
    if (!pacotes.has(nome)) {
      if (!naoCasadas.some((n) => n.pacote === nome)) {
        naoCasadas.push({ pacote: nome, status: c.status, celula: c.nome });
      }
    }
    else if (!status.has(nome)) status.set(nome, c.status);
  }

  const nos = comChave.map(([pacote, ks]) => ({
    pacote,
    bloco: chaves.get(ks[0]).bloco,          // coluna = bloco da PRIMEIRA chave
    chaves: ks.length,
    listaChaves: ks,
    status: status.get(pacote) ?? null,
  }));
  const colunas = [...new Set(nos.map((n) => n.bloco))].sort();

  const vistas = new Set();
  const arestas = [];
  let injecoesBrutas = 0; let autoArestas = 0;
  for (const [k, v] of chaves) for (const alvo of v.injeta) {
    injecoesBrutas += 1;
    const de = dono.get(k); const para = dono.get(alvo);
    if (!de || !para) continue;
    if (de === para) { autoArestas += 1; continue; }
    const id = `${de}->${para}`;
    if (vistas.has(id)) continue;
    vistas.add(id); arestas.push({ de, para });
  }

  return {
    chaves: chaves.size,
    blocos,
    nos,
    arestas,
    colunas,
    naoCasadas,
    semChave,
    injecoesBrutas,
    autoArestas,
    prosaDiz,
    divergenciaDeContagem: prosaDiz !== null && prosaDiz !== pacotes.size,
  };
}
