/**
 * Select2 dropdown mobilde bottom sheet gibi görünsün diye body'ye class ekler.
 * Sadece dropdown açıkken stiller uygulanır (gizli dropdown ekranda görünmez).
 */
(function () {
  const $ = window.django?.jQuery || window.jQuery;
  if (!$) return;

  function addOpenClass() {
    document.body.classList.add("select2-dropdown-open");
  }

  function removeOpenClass() {
    document.body.classList.remove("select2-dropdown-open");
  }

  $(document).on("select2:open", function () {
    addOpenClass();
  });

  $(document).on("select2:close", function () {
    removeOpenClass();
  });
})();
