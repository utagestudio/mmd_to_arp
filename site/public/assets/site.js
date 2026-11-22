// Theme toggle, copy-to-clipboard, and the latest version from the extension repository.
// The initial theme is applied by the inline script in <head> (so the page does not flash).
(function () {
  var root = document.documentElement;

  function currentTheme() {
    var stamped = root.getAttribute("data-theme");
    if (stamped === "dark" || stamped === "light") return stamped;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-copy]"), function (btn) {
    var label = btn.textContent;
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      function done() {
        btn.setAttribute("data-copied", "true");
        btn.textContent = btn.getAttribute("data-copied-label") || "Copied";
        setTimeout(function () { btn.removeAttribute("data-copied"); btn.textContent = label; }, 1800);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { window.prompt("Copy this URL:", text); });
      } else {
        window.prompt("Copy this URL:", text);
      }
    });
  });

  // Autoplaying videos: stop them for people who ask for less motion (the poster stays),
  // and add controls so they can still play them.
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    Array.prototype.forEach.call(document.querySelectorAll("video[autoplay]"), function (v) {
      v.removeAttribute("autoplay");
      v.pause();
      v.controls = true;
    });
  }

  // Latest release from the extension repository (written by tools/make_repository.py).
  // Without JavaScript the download links keep pointing to GitHub Releases.
  var base = new URL("/repository/", location.href);
  fetch(new URL("index.json", base), { cache: "no-cache" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      var entries = (data && data.data) || [];
      var latest = entries.filter(function (e) { return e.id === "mmd_to_arp"; }).sort(function (a, b) {
        var pa = a.version.split(".").map(Number), pb = b.version.split(".").map(Number);
        for (var i = 0; i < 3; i++) { if (pa[i] !== pb[i]) return pb[i] - pa[i]; }
        return 0;
      })[0];
      if (!latest) return;
      var zip = new URL(latest.archive_url, base).href;
      Array.prototype.forEach.call(document.querySelectorAll("[data-zip]"), function (a) { a.href = zip; });
      Array.prototype.forEach.call(document.querySelectorAll("[data-version]"), function (el) { el.textContent = latest.version; });
    })
    .catch(function () {});
})();
