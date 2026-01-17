document.addEventListener('DOMContentLoaded', () => {
  const target = document.getElementById('cotizacion-print');
  if (!target || !window.html2canvas) {
    return;
  }

  const width = 1305;
  const height = 1485;
  window.html2canvas(target, {
    scale: 1,
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
});
