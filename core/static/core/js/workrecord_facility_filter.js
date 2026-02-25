/**
 * İş kaydı formunda müşteri seçilince tesis dropdown'ı filtrelenir.
 * Facility autocomplete'a customer_id parametresi eklenir.
 */
(function () {
  const $ = window.django?.jQuery || window.jQuery;
  if (!$) return;

  function initFacilityFilter() {
    const $customer = $("#id_customer");
    const $facility = $("#id_facility");
    if (!$customer.length || !$facility.length) return;

    // Select2 zaten başlatılmış olabilir; destroy edip customer_id ile yeniden başlat
    if ($facility.hasClass("select2-hidden-accessible")) {
      $facility.select2("destroy");
    }

    const facilityEl = $facility[0];
    const url = facilityEl.getAttribute("data-ajax--url") || facilityEl.dataset?.ajaxUrl;
    const appLabel = facilityEl.dataset?.appLabel;
    const modelName = facilityEl.dataset?.modelName;
    const fieldName = facilityEl.dataset?.fieldName;

    const baseData = {
      app_label: appLabel,
      model_name: modelName,
      field_name: fieldName,
    };

    $facility.select2({
      ajax: {
        url: url || "/admin/autocomplete/",
        dataType: "json",
        delay: 250,
        data: function (params) {
          const data = {
            term: params.term || "",
            page: params.page || 1,
            ...baseData,
          };
          const customerId = $customer.val();
          if (customerId) {
            data.customer_id = customerId;
          }
          return data;
        },
        processResults: function (data) {
          return {
            results: data.results || [],
            pagination: data.pagination || { more: false },
          };
        },
        cache: true,
      },
      placeholder: "",
      allowClear: !$facility.prop("required"),
      minimumInputLength: 0,
    });

    // Müşteri değişince tesis seçimini temizle
    $customer.on("change", function () {
      $facility.val(null).trigger("change");
    });
  }

  $(function () {
    // Unfold/Django select2 init'ten sonra çalışsın
    setTimeout(initFacilityFilter, 150);
  });
})();
