/* DebtOut website: owner details from datos-titular.js (legal pages and footer). No tracking, no cookies. */
(function () {
  "use strict";
  var T = window.DEBTOUT_TITULAR && typeof window.DEBTOUT_TITULAR === "object" ? window.DEBTOUT_TITULAR : {};
  function has(k) { return String(T[k] || "").trim() !== ""; }
  var email = String(T.email || "").trim();
  if (!/^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]{2,}$/.test(email)) email = "";
  function mailLink() { var a = document.createElement("a"); a.href = "mailto:" + email; a.textContent = email; return a; }
  if (has("nombre") && !has("registro")) document.querySelectorAll('li[data-opt="registro"]').forEach(function (e) { e.remove(); });
  document.querySelectorAll("mark.ph[data-k]").forEach(function (m) {
    var k = m.getAttribute("data-k");
    if (k === "email") { if (email) m.replaceWith(mailLink()); return; }
    if (has(k)) m.replaceWith(document.createTextNode(String(T[k]).trim()));
  });
  document.querySelectorAll("[data-contact]").forEach(function (el) {
    if (!email) return;
    el.hidden = false;
    var slot = el.querySelector("[data-contact-link]");
    if (slot) slot.replaceWith(mailLink());
  });
})();
