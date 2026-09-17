// rotulos.mjs — roda no BROWSER. Rótulos como HTML sobreposto ao canvas, não como
// sprite dentro da cena. Três motivos, todos vistos na tela:
//   1. texto de DOM é nítido em qualquer zoom; textura de canvas escalada vira mingau;
//   2. tamanho CONSTANTE em pixels — sprite tem tamanho em unidades de mundo;
//   3. fica ACIMA do canvas, então aresta nenhuma corta o texto.
import * as THREE from '/vendor/three@0.180.0/three.module.min.js';

const FOLGA = 60;        // afastamento do chip em relação ao nó, em unidades de mundo
const APAGADO = 0.10;

export function criarRotulos(host, modelo, camera) {
  const camada = document.createElement('div');
  camada.className = 'rotulos';
  host.appendChild(camada);

  const novo = (texto, classe) => {
    const chip = document.createElement('div');
    chip.className = classe;
    chip.textContent = texto;
    camada.appendChild(chip);
    return chip;
  };

  const itens = modelo.nos.map((no) => {
    const chip = novo(no.pacote, 'chip');
    chip.style.borderLeftColor = no.cor;
    // alterna acima/abaixo: dois nós vizinhos do mesmo setor não colidem o rótulo
    return { chip, ponto: new THREE.Vector3(), pacote: no.pacote, pos: no.pos, acima: no.rotuloAcima };
  });

  // rótulo do bloco: UMA vez por setor, na borda de fora — nunca repetido por nó
  const marcos = modelo.setores.map((s) => ({
    chip: novo(s.nome ? `${s.bloco} ${s.nome}` : s.bloco, 'chip setor'), ponto: new THREE.Vector3(), pos: s.pos, acima: true, pacote: null,
  }));

  let perto = null;

  const situar = ({ chip, ponto, pos, acima, pacote }, l, a) => {
    ponto.set(pos[0], pos[1] + (acima ? FOLGA : -FOLGA), pos[2]).project(camera);
    const x = (ponto.x * 0.5 + 0.5) * l;
    const y = (-ponto.y * 0.5 + 0.5) * a;
    const dentro = ponto.z < 1 && x > -160 && x < l + 160 && y > -60 && y < a + 60;
    chip.style.display = dentro ? 'block' : 'none';
    if (!dentro) return;
    const desloca = acima ? '-100%' : '0%';
    chip.style.transform = `translate(-50%, ${desloca}) translate(${Math.round(x)}px, ${Math.round(y)}px)`;
    if (pacote) chip.style.opacity = !perto || perto.has(pacote) ? 1 : APAGADO;
  };

  return {
    destacar(conjunto) { perto = conjunto; },
    atualizar() {
      const l = host.clientWidth; const a = host.clientHeight;
      for (const item of itens) situar(item, l, a);
      for (const marco of marcos) situar(marco, l, a);
    },
    limpar() { camada.remove(); },
  };
}
