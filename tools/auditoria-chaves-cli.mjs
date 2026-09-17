// CLI da auditoria de chaves: `node tools/auditoria-chaves-cli.mjs [raiz-do-projeto]`.
//
// Arquivo SEPARADO do módulo, e não um `if (import.meta.url === ...)` no rodapé: no
// Windows aquela comparação silenciosamente não casa, e a ferramenta ficaria muda na
// linha de comando sem nenhum teste perceber — os testes importam o módulo, não o
// executam. Separar torna a detecção desnecessária.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { auditar } from './auditoria-chaves.mjs';

const raiz = process.argv[2] ?? process.cwd();

function varrer(dir, saida = []) {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) varrer(caminho, saida);
    else if (nome.endsWith('.ts')) saida.push({ arquivo: caminho, texto: readFileSync(caminho, 'utf8') });
  }
  return saida;
}

const pacotes = join(raiz, 'packages');
const fontes = readdirSync(pacotes)
  .map((p) => join(pacotes, p, 'src'))
  .filter((d) => { try { return statSync(d).isDirectory(); } catch { return false; } })
  .flatMap((d) => varrer(d));

console.log(auditar(readFileSync(join(raiz, 'contratos', 'mapa-de-chaves.md'), 'utf8'), fontes));
