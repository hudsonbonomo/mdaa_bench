// cena3d.mjs — roda no BROWSER. A CENA NÃO CALCULA NADA: posições, curvas e cores vêm
// prontas de /modelo.json (grafo3d.mjs, no servidor). Aqui só há three.js e eventos.
import * as THREE from '/vendor/three@0.180.0/three.module.min.js';
import { criarOrbita } from '/orbita.mjs';
import { criarCamera, POSE } from '/camera3d.mjs';
import { criarRotulos } from '/rotulos.mjs';
import { criarSelecao } from '/selecao.mjs';

const APAGADO = 0.10;   // o que desembaraça 39 arestas cruzadas nao e o 3D: e apagar o resto
const OPACO_MIN = 0.55; const OPACO_MAX = 0.95;   // clareza pela quantidade de dependentes
const RAIO = 8000;      // ortografica: a distancia so evita corte, nao afeta escala

export async function montarCena(host, lateral) {
  const modelo = await fetch('/modelo.json').then((r) => r.json());
  const cena = new THREE.Scene();
  const { camera, centro } = criarCamera(modelo, host.clientWidth, host.clientHeight);
  const renderizador = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderizador.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderizador.setSize(host.clientWidth, host.clientHeight);
  host.replaceChildren(renderizador.domElement);

  const orbita = criarOrbita(camera, renderizador.domElement, centro, RAIO, POSE);

  // Esfera, nao caixa: no radial a caixa alongada vira lasca inclinada. O RAIO carrega
  // a hierarquia e vem pronto do servidor (raioNo, proporcional aos dependentes).
  const maisDeps = Math.max(1, ...modelo.nos.map((n) => n.dependentes));
  const porPacote = new Map();
  // prisma hexagonal, nao esfera: o 2D virou hexagono na v2b e as duas vistas
  // tem de falar a mesma lingua. 6 lados radiais = hexagono deitado.
  const esfera = new THREE.CylinderGeometry(1, 1, 0.5, 6);
  for (const no of modelo.nos) {
    const peso = no.dependentes / maisDeps;
    const material = new THREE.MeshBasicMaterial({
      color: no.cor, transparent: true, opacity: OPACO_MIN + (OPACO_MAX - OPACO_MIN) * peso,
    });
    const malha = new THREE.Mesh(esfera, material);
    malha.opacidadeBase = material.opacity;
    malha.position.set(...no.pos);
    malha.scale.setScalar(no.raioNo);
    malha.rotation.x = Math.PI / 2;   // deita o prisma para o hexagono ficar de frente
    malha.userData = no;
    cena.add(malha);
    porPacote.set(no.pacote, malha);
  }
  const rotulos = criarRotulos(host, modelo, camera);

  const linhas = modelo.arestas.map((a) => {
    const geo = new THREE.BufferGeometry().setFromPoints(
      a.pontos.map((p) => new THREE.Vector3(...p)));
    const linha = new THREE.Line(geo, new THREE.LineBasicMaterial({
      color: 0x2f3742, transparent: true, opacity: 0.3,
    }));
    linha.userData = a;
    cena.add(linha);
    return linha;
  });

  // A MESMA máquina de estado do 2D (selecao.mjs). Aqui entram só as duas coisas que
  // realmente variam entre as vistas: como pintar e como aproximar. Vizinhos, foco,
  // painel lateral e limpar são idênticos — e por isso não são copiados.
  const selecao = criarSelecao({
    lateral,
    arestas: () => modelo.arestas,
    pintar: (perto) => {
      for (const [nome, malha] of porPacote) {
        const aceso = !perto || perto.has(nome);
        malha.material.opacity = aceso ? malha.opacidadeBase : APAGADO;
        malha.children.forEach((f) => { f.material.opacity = aceso ? f.opacidadeBase : APAGADO; });
      }
      rotulos.destacar(perto);
      for (const linha of linhas) {
        const a = linha.userData;
        const aceso = !perto || (perto.has(a.de) && perto.has(a.para));
        linha.material.opacity = aceso ? (perto ? 0.85 : 0.3) : 0.02;
      }
    },
    focar: (no) => orbita.focar(no.pos, 3.2),
  });

  const dadosDe = (no) => ({ ...no, chaves: no.listaChaves });

  const mira = new THREE.Raycaster();
  const ponteiro = new THREE.Vector2();
  const alvoDoEvento = (e) => {
    const r = renderizador.domElement.getBoundingClientRect();
    ponteiro.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    mira.setFromCamera(ponteiro, camera);
    return mira.intersectObjects([...porPacote.values()], false)[0]?.object ?? null;
  };

  renderizador.domElement.addEventListener('pointermove', (e) => {
    if (e.buttons) return;                       // arrastando: não repinta
    const alvo = alvoDoEvento(e);
    selecao.sobre(alvo ? dadosDe(alvo.userData) : null);
    renderizador.domElement.style.cursor = alvo ? 'pointer' : 'grab';
  });

  renderizador.domElement.addEventListener('click', (e) => {
    const alvo = alvoDoEvento(e);
    selecao.clicar(alvo ? dadosDe(alvo.userData) : null);
  });

  addEventListener('keydown', (e) => {
    if (e.key !== 'r' && e.key !== 'R') return;
    selecao.limpar(); orbita.resetar();
  });

  addEventListener('resize', () => {
    camera.ajustar(host.clientWidth, host.clientHeight);
    orbita.aplicar();
    renderizador.setSize(host.clientWidth, host.clientHeight);
  });

  const desenhar = () => {
    rotulos.atualizar();
    renderizador.render(cena, camera);
    requestAnimationFrame(desenhar);
  };
  desenhar();

  // O 2D é ao vivo por SSE; o 3D não pode congelar. Aqui só as CORES são repintadas —
  // a câmera fica onde o humano deixou, que é o oposto de recarregar a página.
  return {
    encaixar() { selecao.limpar(); orbita.resetar(); },

    async atualizar() {
      const novo = await fetch('/modelo.json').then((r) => r.json());
      for (const no of novo.nos) {
        const malha = porPacote.get(no.pacote);
        if (!malha) continue;
        malha.material.color.set(no.cor);
        malha.userData = no;
      }
      selecao.reaplicar();
    },
  };
}
