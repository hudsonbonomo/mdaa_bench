#!/usr/bin/env node
// painel.mjs — servidor: serve a página, mantém viva por SSE, entrega o modelo 3D em JSON
// e o vendor local. READ-ONLY: nunca escreve no projeto-alvo.
// uso: node painel.mjs <caminho-do-projeto> [--porta 3007]
import http from 'node:http';
import { watch, readFileSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { lerProjeto, ARQUIVOS } from './parse.mjs';
import { montarGrafo } from './grafo.mjs';
import { modelo3d } from './grafo3d.mjs';
import { pagina, fragmentos } from './pagina.mjs';

const DEBOUNCE = 80;   // fs.watch do Windows duplica evento; 80ms coalesce numa emissão
const AQUI = dirname(fileURLToPath(import.meta.url));
const VENDOR = join(AQUI, 'vendor');
const CLIENTE = ['cena3d.mjs', 'orbita.mjs', 'camera3d.mjs', 'rotulos.mjs', 'zoom2d.mjs', 'interacao2d.mjs', 'selecao.mjs'];   // modulos servidos ao browser
const JS = 'text/javascript; charset=utf-8';
const TIPOS = { '.js': JS, '.mjs': JS, '.md': 'text/plain; charset=utf-8' };

// Caminho de vendor é lista branca de caracteres, em exatamente dois segmentos.
// Sem '..', sem barra invertida: path traversal não passa por aqui.
function arquivoDeVendor(url) {
  const partes = url.slice('/vendor/'.length).split('/');
  if (partes.length !== 2) return null;
  if (!partes.every((p) => /^[A-Za-z0-9@._-]+$/.test(p) && !p.includes('..'))) return null;
  const caminho = join(VENDOR, partes[0], partes[1]);
  return existsSync(caminho) ? caminho : null;
}

function responderJson(res, codigo, dado) {
  res.writeHead(codigo, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(dado));
}

export async function criarPainel(caminho, opcoes = {}) {
  const raiz = resolve(caminho);
  let estado = lerProjeto(raiz);              // fail-fast ANTES de abrir a porta
  const clientes = new Set();
  let temporizador = null;

  const servidor = http.createServer((req, res) => {
    if (req.url === '/eventos') {
      res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache',
        connection: 'keep-alive' });
      res.write(': conectado\n\n');            // comentário, não evento: conectar não dispara
      clientes.add(res);
      req.on('close', () => clientes.delete(res));
      return;
    }
    if (req.url === '/modelo.json') {
      if (!estado.temMapa) return responderJson(res, 404, { erro: 'sem grafo: mapa ausente' });
      try {
        return responderJson(res, 200, modelo3d(montarGrafo(estado.mapaTexto, estado.celulas)));
      } catch (erro) { return responderJson(res, 500, { erro: erro.message }); }
    }
    if (req.url && CLIENTE.includes(req.url.slice(1))) {
      res.writeHead(200, { 'content-type': JS });
      return res.end(readFileSync(join(AQUI, req.url.slice(1))));
    }
    if (req.url?.startsWith('/vendor/')) {
      const arquivo = arquivoDeVendor(req.url);
      if (!arquivo) { res.writeHead(404); return res.end('nao encontrado'); }
      const ext = arquivo.slice(arquivo.lastIndexOf('.'));
      res.writeHead(200, { 'content-type': TIPOS[ext] ?? 'application/octet-stream' });
      return res.end(readFileSync(arquivo));
    }
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(pagina(estado));
  });

  const emitir = () => {
    try { estado = lerProjeto(raiz); } catch { return; }   // arquivo em meio à escrita
    const dado = JSON.stringify(fragmentos(estado));
    for (const c of clientes) c.write(`event: estado\ndata: ${dado}\n\n`);
  };

  // Watch no DIRETÓRIO, filtrado por nome: o fs.watch do Windows perde o watch quando o
  // arquivo é substituído por rename, e duplica evento na mesma escrita.
  const observador = watch(estado.estado, (_tipo, nome) => {
    if (nome && !ARQUIVOS.includes(nome)) return;
    if (temporizador) clearTimeout(temporizador);
    temporizador = setTimeout(emitir, DEBOUNCE);
  });
  observador.on('error', () => {});

  const porta = await new Promise((ok, erro) => {
    servidor.once('error', (e) => erro(e.code === 'EADDRINUSE'
      ? new Error(`a porta ${opcoes.porta} ja esta em uso`) : e));
    servidor.listen(opcoes.porta ?? 3007, '127.0.0.1', () => ok(servidor.address().port));
  });

  return {
    porta,
    raiz,
    observados: estado.observados,
    fechar: () => new Promise((ok) => {
      if (temporizador) clearTimeout(temporizador);
      observador.close();
      for (const c of clientes) c.end();
      clientes.clear();
      servidor.close(() => ok());
    }),
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const argumentos = process.argv.slice(2);
  const i = argumentos.indexOf('--porta');
  const porta = i >= 0 ? Number(argumentos[i + 1]) : 3007;
  const projeto = argumentos.find((a) => !a.startsWith('--') && a !== argumentos[i + 1]);
  if (!projeto) {
    console.error('uso: node painel.mjs <caminho-do-projeto> [--porta 3007]');
    process.exit(1);
  }
  try {
    const p = await criarPainel(projeto, { porta });
    // anúncio ANTES de esperar — e honesto sobre o mecanismo (watch é de diretório)
    console.log(`servindo ${p.raiz} na porta ${p.porta} — observando ${join('vault', 'estado')}`
      + ` (${p.observados.length} arquivos: ${p.observados.join(', ')})`);
    console.log(`http://127.0.0.1:${p.porta}/`);
  } catch (erro) {
    console.error(`erro: ${erro.message}`);
    process.exit(1);
  }
}
