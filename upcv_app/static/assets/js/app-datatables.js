(function (window, document) {
  'use strict';

  var spanishLanguage = {
    processing: 'Procesando...',
    search: 'Buscar:',
    lengthMenu: 'Mostrar _MENU_ registros',
    info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
    infoEmpty: 'Mostrando 0 a 0 de 0 registros',
    infoFiltered: '(filtrado de _MAX_ registros totales)',
    loadingRecords: 'Cargando...',
    zeroRecords: 'No se encontraron resultados',
    emptyTable: 'No hay datos disponibles en la tabla',
    paginate: {
      first: 'Primero',
      previous: 'Anterior',
      next: 'Siguiente',
      last: 'Último'
    },
    aria: {
      sortAscending: ': activar para ordenar ascendente',
      sortDescending: ': activar para ordenar descendente'
    }
  };

  function normalizeBoolean(value, fallback) {
    if (typeof value === 'undefined') {
      return fallback;
    }
    return value !== false && value !== 'false' && value !== '0';
  }

  function initAppDataTables(context) {
    if (!window.jQuery || !jQuery.fn || !jQuery.fn.DataTable) {
      return;
    }

    var $context = context ? jQuery(context) : jQuery(document);
    $context.find('table.datatable-app').each(function () {
      var $table = jQuery(this);

      if (!jQuery.contains(document, this)) {
        return;
      }

      if (jQuery.fn.DataTable.isDataTable(this)) {
        return;
      }

      var hasOnlyEmptyColspanRow = $table.find('tbody tr').length === 1 && $table.find('tbody tr:first td[colspan]').length > 0;
      if (hasOnlyEmptyColspanRow) {
        $table.closest('.table-responsive').addClass('st-table-shell');
        return;
      }

      var pageLength = parseInt($table.data('pageLength'), 10);
      if (Number.isNaN(pageLength) || pageLength <= 0) {
        pageLength = 10;
      }

      var ordering = normalizeBoolean($table.data('ordering'), true);
      var searching = normalizeBoolean($table.data('searching'), true);
      var paging = normalizeBoolean($table.data('paging'), true);
      var info = normalizeBoolean($table.data('info'), true);
      var isServicioTecnico = $table.hasClass('st-data-table');

      var options = {
        responsive: true,
        autoWidth: false,
        pageLength: pageLength,
        lengthMenu: [[5, 10, 25, 50, 100, -1], [5, 10, 25, 50, 100, 'Todos']],
        ordering: ordering,
        searching: searching,
        paging: paging,
        info: info,
        language: spanishLanguage
      };

      if (isServicioTecnico) {
        options.dom = '<"row align-items-center g-2 st-dt-controls"<"col-md-6"l><"col-md-6"f>>rt<"row align-items-center g-2"<"col-md-6"i><"col-md-6"p>>';
        options.columnDefs = [
          { responsivePriority: 1, targets: 0 },
          { responsivePriority: 2, targets: -1, orderable: false }
        ];
      }

      var dataTable = $table.DataTable(options);

      if (isServicioTecnico) {
        jQuery(dataTable.table().container()).addClass('st-datatable-wrapper');
      }
    });
  }

  window.initAppDataTables = initAppDataTables;

  document.addEventListener('DOMContentLoaded', function () {
    initAppDataTables();
  });
})(window, document);
