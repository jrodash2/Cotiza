document.addEventListener('DOMContentLoaded', () => {
  const target = document.querySelector('.page');
  if (!target || !window.html2canvas) {
    return;
  }

  const width = 1275;
  const height = 1650;
  const textoIva = document.querySelector('#texto-iva-legal');
  console.log('texto legal IVA antes de exportar:', textoIva?.innerText || '(no encontrado)');

  const capturar = () => window.html2canvas(target, {
    scale: 3,
    useCORS: true,
    width,
    height,
    windowWidth: width,
    windowHeight: height,
    backgroundColor: '#ffffff',
  }).then((canvas) => {
    const link = document.createElement('a');
    const correlativo = target.getAttribute('data-correlativo') || Date.now();
    link.download = `cotizacion_${correlativo}.jpg`;
    link.href = canvas.toDataURL('image/jpeg', 0.95);
    link.click();
  });

  window.requestAnimationFrame(() => {
    setTimeout(capturar, 80);
  });
});
