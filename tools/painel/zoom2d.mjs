// zoom2d.mjs — roda no BROWSER. Dá à planta baixa os MESMOS gestos do corte 3D:
// arrastar move, roda amplia, e o botão encaixa de volta. Duas vistas do mesmo modelo
// não podem exigir duas gramáticas de mão.
//
// O estado do zoom vive AQUI, fora do SVG — porque o SSE troca o SVG a cada escrita no
// vault, e a ampliação não pode se perder quando você anota uma linha.
export function criarZoom2d(host) {
  const estado = { x: 0, y: 0, k: 1 };
  let arrastando = false;
  let pendente = null;          // pointerdown que ainda não virou arrasto
  let ultimo = [0, 0];
  const LIMIAR = 4;             // px antes de virar arrasto

  const aplicar = () => {
    const svg = host.querySelector('svg');
    if (!svg) return;
    svg.style.transformOrigin = '0 0';
    svg.style.transform = `translate(${estado.x}px, ${estado.y}px) scale(${estado.k})`;
  };

  // NÃO capturar o ponteiro no pointerdown: com a captura ativa, o `click` seguinte tem
  // como alvo o CONTAINER, não o <g> do nó — e o clique na célula deixava de achar o nó.
  // O arrasto só começa depois de 4px de movimento; clique simples nunca captura.
  host.addEventListener('pointerdown', (e) => {
    pendente = { id: e.pointerId, x: e.clientX, y: e.clientY };
    ultimo = [e.clientX, e.clientY];
  });

  const soltar = (e) => {
    if (arrastando) {
      // marca que houve arrasto, para o clique que vem logo atrás não selecionar nó
      host.dataset.arrastou = '1';
      setTimeout(() => { delete host.dataset.arrastou; }, 0);
    }
    arrastando = false; pendente = null;
    host.style.cursor = '';
    if (host.hasPointerCapture?.(e.pointerId)) host.releasePointerCapture(e.pointerId);
  };
  host.addEventListener('pointerup', soltar);
  host.addEventListener('pointercancel', soltar);

  host.addEventListener('pointermove', (e) => {
    if (pendente && !arrastando) {
      if (Math.hypot(e.clientX - pendente.x, e.clientY - pendente.y) < LIMIAR) return;
      arrastando = true;
      host.setPointerCapture(pendente.id);
      host.style.cursor = 'grabbing';
    }
    if (!arrastando) return;
    estado.x += e.clientX - ultimo[0];
    estado.y += e.clientY - ultimo[1];
    ultimo = [e.clientX, e.clientY];
    aplicar();
  });

  // zoom ancorado no cursor: o ponto sob o mouse fica onde está, que é o que a mão espera
  host.addEventListener('wheel', (e) => {
    e.preventDefault();
    const r = host.getBoundingClientRect();
    const cx = e.clientX - r.left; const cy = e.clientY - r.top;
    const k = Math.min(8, Math.max(0.3, estado.k * (e.deltaY > 0 ? 0.9 : 1.1)));
    const fator = k / estado.k;
    estado.x = cx - (cx - estado.x) * fator;
    estado.y = cy - (cy - estado.y) * fator;
    estado.k = k;
    aplicar();
  }, { passive: false });

  return {
    aplicar,
    encaixar() { estado.x = 0; estado.y = 0; estado.k = 1; aplicar(); },

    // Aproxima um ponto do MODELO (unidades do viewBox) e o centraliza — o equivalente
    // 2D do `orbita.focar` do 3D. É o que faz clicar num nó reagir igual nas duas vistas.
    focar(ux, uy, k = 2.4) {
      const svg = host.querySelector('svg');
      if (!svg || !Number.isFinite(ux)) return;
      const [minX, minY, vbL, vbA] = svg.getAttribute('viewBox').split(/\s+/).map(Number);
      const caixa = host.getBoundingClientRect();
      // O SVG preenche o host, mas o DESENHO dentro dele é escalado pelo menor fator e
      // centralizado (preserveAspectRatio="meet") — sobra letterbox. Ignorar essa folga
      // era o que fazia o foco cair fora do nó e o zoom parecer bugado.
      const escala = Math.min(caixa.width / vbL, caixa.height / vbA);
      const folgaX = (caixa.width - vbL * escala) / 2;
      const folgaY = (caixa.height - vbA * escala) / 2;
      const px = folgaX + (ux - minX) * escala;
      const py = folgaY + (uy - minY) * escala;
      estado.k = k;
      estado.x = caixa.width / 2 - px * k;
      estado.y = caixa.height / 2 - py * k;
      aplicar();
    },
  };
}
