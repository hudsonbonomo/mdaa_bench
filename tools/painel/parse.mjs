// parse.mjs — lê o estado de um projeto em Modo Celular. Varredura LINEAR de linhas,
// sem regex sobre entrada livre (lição do backlog: dois regex perderam 4 chaves em silêncio).
import { readFileSync, existsSync } from 'node:fs';
import { join, basename, resolve } from 'node:path';

export const STATUS = ['✔', '🔵', '⏸', '📋'];
export const ARQUIVOS = ['INDICE.md', 'CELULA-ATUAL.md'];
const ESCAPE = '\u0000'; // marcador para '\|' — nunca aparece em markdown

function fatiar(linha) {
  const partes = linha.replaceAll('\\|', ESCAPE).split('|');
  if (partes[0].trim() === '') partes.shift();
  if (partes.length && partes[partes.length - 1].trim() === '') partes.pop();
  return partes.map((p) => p.replaceAll(ESCAPE, '|').trim());
}

function ehSeparador(celulas) {
  return celulas.length > 0 && celulas.every((c) => c.length >= 3 && /^:?-+:?$/.test(c));
}

// Cabeçalho vira mapa nome→índice. Só tabelas com 'Célula' E 'Status' são de células.
function mapearColunas(celulas) {
  const col = {};
  celulas.forEach((c, i) => {
    if (c.startsWith('Célula')) col.nome = i;
    else if (c.startsWith('Plugin')) col.area = i;
    else if (c.startsWith('Status')) col.status = i;
    else if (c.startsWith('Última')) col.ultimaVisita = i;
    else if (c.startsWith('Próximo')) col.proximoPasso = i;
  });
  return col.nome !== undefined && col.status !== undefined ? col : 'ignorar';
}

// Nome da célula no topo. Duas formas reais convivem no vault:
//   '[C4 · nll.config](celulas/c4.md)'          → o nome é o texto do link
//   'Painel v1 — [projeção completa](...)'      → o nome é o que vem ANTES do link
function nomeDaCelula(texto) {
  if (texto.startsWith('[')) return separarLink(texto).nome;
  const abre = texto.indexOf('[');
  const base = abre >= 0 ? texto.slice(0, abre) : texto;
  return base.trim().replace(/[\s—·-]+$/, '').trim();
}

// '[nome](destino)' → { nome, slug }; texto simples → { nome, slug: null }.
function separarLink(texto) {
  if (texto.startsWith('[') && texto.endsWith(')')) {
    const fim = texto.indexOf('](');
    if (fim > 0) return { nome: texto.slice(1, fim), slug: texto.slice(fim + 2, -1) };
  }
  return { nome: texto, slug: null };
}

export function parseIndice(texto) {
  const celulas = [];
  let col = null;
  for (const bruta of texto.split('\n')) {
    const linha = bruta.trim();
    if (!linha.startsWith('|')) { col = null; continue; }
    const partes = fatiar(linha);
    if (ehSeparador(partes)) continue;
    if (col === null) { col = mapearColunas(partes); continue; }
    if (col === 'ignorar') continue;
    const bruto = partes[col.status] ?? '';
    celulas.push({
      ...separarLink(partes[col.nome] ?? ''),
      area: partes[col.area] ?? '',
      status: STATUS.find((s) => bruto.includes(s)) ?? bruto,
      ultimaVisita: partes[col.ultimaVisita] ?? '',
      proximoPasso: partes[col.proximoPasso] ?? '',
    });
  }
  return celulas;
}

// A alma: o PRÓXIMO PASSO vem da SEÇÃO '## ➜', nunca do status — a religação vale MAIS
// quando não há célula ativa (cravada de 25/08/2026).
export function parseCelulaAtual(texto) {
  const linhas = texto.split('\n');
  let celula = null;
  let proximoPasso = null;
  for (let i = 0; i < linhas.length; i += 1) {
    const linha = linhas[i].trim();
    if (celula === null && linha.startsWith('**Célula:**')) {
      celula = nomeDaCelula(linha.slice('**Célula:**'.length).trim());
    }
    if (proximoPasso === null && linha.startsWith('## ➜')) {
      const corpo = [];
      for (let j = i + 1; j < linhas.length; j += 1) {
        if (linhas[j].trim().startsWith('#')) break;
        corpo.push(linhas[j].trim());
      }
      proximoPasso = corpo.join(' ').replaceAll('  ', ' ').trim();
    }
  }
  return { celula, proximoPasso };
}

export function contar(celulas) {
  const contagens = {};
  for (const s of STATUS) contagens[s] = 0;
  for (const c of celulas) if (contagens[c.status] !== undefined) contagens[c.status] += 1;
  return contagens;
}

// Fail-fast ALTO: sem vault/estado não há painel. A mensagem cita o caminho procurado.
export function lerProjeto(caminho) {
  const raiz = resolve(caminho);
  const estado = join(raiz, 'vault', 'estado');
  if (!existsSync(estado)) {
    throw new Error(`nao encontrei o estado do Modo Celular em: ${estado}`);
  }
  const indice = join(estado, 'INDICE.md');
  if (!existsSync(indice)) throw new Error(`nao encontrei o indice em: ${indice}`);

  const celulas = parseIndice(readFileSync(indice, 'utf8'));
  const caminhoAtual = join(estado, 'CELULA-ATUAL.md');
  const atual = existsSync(caminhoAtual)
    ? parseCelulaAtual(readFileSync(caminhoAtual, 'utf8'))
    : { celula: null, proximoPasso: null };

  return {
    projeto: basename(raiz),
    raiz,
    estado,
    celulas,
    contagens: contar(celulas),
    celulaAtual: atual.celula,
    proximoPasso: atual.proximoPasso,
    temMapa: existsSync(join(raiz, 'contratos', 'mapa-de-chaves.md')),
    mapaTexto: existsSync(join(raiz, 'contratos', 'mapa-de-chaves.md'))
      ? readFileSync(join(raiz, 'contratos', 'mapa-de-chaves.md'), 'utf8') : null,
    observados: ARQUIVOS.filter((a) => existsSync(join(estado, a))),
  };
}
