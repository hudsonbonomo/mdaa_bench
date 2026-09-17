// orbita.mjs — controle de câmera próprio, no lugar do OrbitControls de examples/jsm
// (que importa do bare specifier 'three' e exigiria import map — ver vendor/VENDOR.md).
// Roda no BROWSER. Coordenadas esféricas: mesma matemática, sem dependência.
// Com câmera ORTOGRÁFICA o zoom é `camera.zoom`, não distância — mover a câmera para
// perto não aproximaria nada numa projeção paralela.

export function criarOrbita(camera, tela, alvoInicial, raio, pose) {
  const estado = { alvo: [...alvoInicial], teta: pose.teta, fi: pose.fi, zoom: 1 };
  const inicial = JSON.parse(JSON.stringify(estado));
  let arrastando = null; let ultimo = [0, 0]; let espaco = false;

  // Eixos de TELA na orientação atual. Arrastar tem de mover o conteúdo para onde o
  // cursor vai — em qualquer ângulo. Mover em X/Y do MUNDO só coincide com a tela na
  // pose inicial; depois de girar, o arrasto ia para o lado errado.
  const eixos = () => {
    const st = Math.sin(estado.teta); const ct = Math.cos(estado.teta);
    const sf = Math.sin(estado.fi); const cf = Math.cos(estado.fi);
    return { direita: [-ct, 0, st], cima: [-st * cf, sf, -ct * cf] };
  };

  const aplicar = () => {
    const [ax, ay, az] = estado.alvo;
    camera.position.set(
      ax + raio * Math.sin(estado.fi) * Math.sin(estado.teta),
      ay + raio * Math.cos(estado.fi),
      az + raio * Math.sin(estado.fi) * Math.cos(estado.teta),
    );
    camera.lookAt(ax, ay, az);
    camera.zoom = estado.zoom;
    camera.updateProjectionMatrix();
  };

  // Canvas de verdade: arrasta com botão direito, botão do meio OU espaço segurado.
  addEventListener('keydown', (e) => {
    // sem o preventDefault, o espaço rola a página por baixo da cena
    if (e.code === 'Space') { e.preventDefault(); espaco = true; tela.style.cursor = 'grab'; }
  });
  addEventListener('keyup', (e) => {
    if (e.code === 'Space') { espaco = false; tela.style.cursor = ''; }
  });

  tela.addEventListener('pointerdown', (e) => {
    arrastando = (e.button === 2 || e.button === 1 || espaco) ? 'pan' : 'girar';
    if (arrastando === 'pan') { e.preventDefault(); tela.style.cursor = 'grabbing'; }
    ultimo = [e.clientX, e.clientY];
    tela.setPointerCapture(e.pointerId);
  });
  tela.addEventListener('pointerup', (e) => {
    arrastando = null;
    tela.style.cursor = espaco ? 'grab' : '';
    if (tela.hasPointerCapture(e.pointerId)) tela.releasePointerCapture(e.pointerId);
  });
  tela.addEventListener('contextmenu', (e) => e.preventDefault());

  tela.addEventListener('pointermove', (e) => {
    if (!arrastando) return;
    const dx = e.clientX - ultimo[0]; const dy = e.clientY - ultimo[1];
    ultimo = [e.clientX, e.clientY];
    if (arrastando === 'girar') {
      estado.teta -= dx * 0.005;
      estado.fi = Math.min(Math.PI - 0.05, Math.max(0.05, estado.fi - dy * 0.005));
    } else {
      const escala = (camera.top - camera.bottom) / (estado.zoom * tela.clientHeight);
      const { direita, cima } = eixos();
      for (let k = 0; k < 3; k += 1) {
        estado.alvo[k] -= direita[k] * dx * escala;
        estado.alvo[k] += cima[k] * dy * escala;
      }
    }
    aplicar();
  });

  // Roda pura = zoom. Shift ou dois dedos na horizontal = arrastar, como em canvas.
  tela.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
      const escala = (camera.top - camera.bottom) / (estado.zoom * tela.clientHeight);
      const { direita, cima } = eixos();
      const dx = e.shiftKey ? e.deltaY : e.deltaX;
      for (let k = 0; k < 3; k += 1) estado.alvo[k] += direita[k] * dx * escala;
      return aplicar();
    }
    estado.zoom = Math.min(12, Math.max(0.2, estado.zoom * (e.deltaY > 0 ? 0.9 : 1.1)));
    aplicar();
  }, { passive: false });

  aplicar();
  return {
    aplicar,
    focar(alvo, zoom) { estado.alvo = [...alvo]; estado.zoom = zoom; aplicar(); },
    resetar() { Object.assign(estado, JSON.parse(JSON.stringify(inicial))); aplicar(); },
  };
}
