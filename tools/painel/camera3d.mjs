// camera3d.mjs — roda no BROWSER. Câmera ORTOGRÁFICA (nó da direita não vira formiga) e
// enquadramento calculado dos `limites` que o servidor manda, nunca posição fixa.
// A pose inicial tem de ser legível sozinha: quase frontal ao plano A→H, 15° elevada.
import * as THREE from '/vendor/three@0.180.0/three.module.min.js';

export const POSE = { teta: 0, fi: Math.PI / 2 - (15 * Math.PI) / 180 };   // 15° acima
const MARGEM = 1.02;   // apertado ao maximo: o disco ja e o conteudo inteiro

export function direcaoDa(pose) {
  return new THREE.Vector3(
    Math.sin(pose.fi) * Math.sin(pose.teta),
    Math.cos(pose.fi),
    Math.sin(pose.fi) * Math.cos(pose.teta),
  ).normalize();
}

// Enquadra os PONTOS REAIS, não os cantos da caixa envolvente. A constelação é um
// disco: os cantos da caixa são vazios, e fitá-los custava 12% de altura de graça.
// Fitar a esfera envolvente seria à prova de rotação, mas deixaria o grafo bem menor
// do que cabe — a pose inicial é que tem de ficar legível; girar é do usuário.
export function enquadrar(pontos, pose = POSE) {
  const centro = new THREE.Vector3(...[0, 1, 2].map((k) => {
    const vs = pontos.map((p) => p[k]);
    return (Math.min(...vs) + Math.max(...vs)) / 2;
  }));
  const dir = direcaoDa(pose);
  const direita = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0)).normalize();
  const cima = new THREE.Vector3().crossVectors(direita, dir).normalize();

  let meiaL = 1; let meiaA = 1;
  for (const p of pontos) {
    const v = new THREE.Vector3(...p).sub(centro);
    meiaL = Math.max(meiaL, Math.abs(v.dot(direita)));
    meiaA = Math.max(meiaA, Math.abs(v.dot(cima)));
  }
  return { centro, meiaL: meiaL * MARGEM, meiaA: meiaA * MARGEM };
}

export function criarCamera(modelo, largura, altura) {
  const pontos = [...modelo.nos.map((n) => n.pos), ...modelo.setores.map((s) => s.pos)];
  const { centro, meiaL, meiaA } = enquadrar(pontos);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -20000, 20000);

  // ortográfica com near/far generosos: girar nunca corta o grafo pelo plano de corte
  camera.ajustar = (l, a) => {
    const proporcao = l / a;
    let altoMeio = meiaA;
    if (meiaL / proporcao > altoMeio) altoMeio = meiaL / proporcao;
    camera.left = -altoMeio * proporcao;
    camera.right = altoMeio * proporcao;
    camera.top = altoMeio;
    camera.bottom = -altoMeio;
    camera.updateProjectionMatrix();
  };
  camera.ajustar(largura, altura);
  return { camera, centro: centro.toArray() };
}
