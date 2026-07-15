(function (window, document) {
  'use strict';

  var assets = window.AURORA_ASSETS || {};
  var loaded = {};

  function loadCss(href) {
    if (!href || loaded[href] || document.querySelector('link[href="' + href + '"]')) return Promise.resolve();
    loaded[href] = true;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
    return Promise.resolve();
  }

  function loadScript(src) {
    if (!src || loaded[src]) return Promise.resolve();
    loaded[src] = true;
    return new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = src;
      script.defer = true;
      script.onload = resolve;
      script.onerror = reject;
      document.body.appendChild(script);
    });
  }

  function initDataTablesWhenNeeded() {
    if (!document.querySelector('table.datatable-app')) return;

    var hasServicioTables = Boolean(document.querySelector('table.st-data-table'));
    var css = [loadCss(assets.datatablesCss)];
    if (hasServicioTables) css.push(loadCss(assets.servicioTecnicoTablesCss));

    Promise.all(css)
      .then(function () { return loadScript(assets.datatablesCore); })
      .then(function () { return loadScript(assets.datatablesBootstrap); })
      .then(function () { return loadScript(assets.datatablesResponsive); })
      .then(function () { return loadScript(assets.datatablesResponsiveBootstrap); })
      .then(function () { return loadScript(assets.appDatatables); })
      .then(function () {
        if (window.initAppDataTables) window.initAppDataTables();
      })
      .catch(function (error) {
        if (window.console) console.warn('No se pudieron cargar los assets de DataTables.', error);
      });
  }

  document.addEventListener('DOMContentLoaded', initDataTablesWhenNeeded);
})(window, document);
