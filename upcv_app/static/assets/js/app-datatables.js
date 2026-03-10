(function (window, document) {
  'use strict';

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

      var pageLength = parseInt($table.data('pageLength'), 10);
      if (Number.isNaN(pageLength) || pageLength <= 0) {
        pageLength = 10;
      }

      var ordering = $table.data('ordering');
      if (typeof ordering === 'undefined') {
        ordering = true;
      }

      $table.DataTable({
        responsive: true,
        autoWidth: false,
        pageLength: pageLength,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'Todos']],
        ordering: ordering,
        language: {
          url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
        }
      });
    });
  }

  window.initAppDataTables = initAppDataTables;

  document.addEventListener('DOMContentLoaded', function () {
    initAppDataTables();
  });
})(window, document);
