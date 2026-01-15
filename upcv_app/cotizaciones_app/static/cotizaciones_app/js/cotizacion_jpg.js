document.addEventListener('DOMContentLoaded', () => {
  const target = document.getElementById('cotizacion-print');
  if (!target || !window.html2canvas) {
    return;
  }

  window.html2canvas(target, { scale: 2, useCORS: true }).then((canvas) => {
    const link = document.createElement('a');
    const correlativo = target.getAttribute('data-correlativo') || Date.now();
    link.download = `cotizacion_${correlativo}.jpg`;
    link.href = canvas.toDataURL('image/jpeg', 0.95);
    link.click();
  });
});
