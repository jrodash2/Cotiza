document.addEventListener('DOMContentLoaded', () => {
  const target = document.querySelector('.page');
  if (!target || !window.html2canvas) {
    return;
  }

  const width = 1275;
  const height = 1650;
  window.html2canvas(target, {
    scale: 3,
    useCORS: true,
    width,
    height,
    windowWidth: width,
    windowHeight: height,
    backgroundColor: '#ffffff',
  }).then((canvas) => {
    const link = document.createElement('a');
    const filename = target.getAttribute('data-filename') || `documento_${Date.now()}`;
    link.download = `${filename}.jpg`;
    link.href = canvas.toDataURL('image/jpeg', 0.95);
    link.click();
  });
});
