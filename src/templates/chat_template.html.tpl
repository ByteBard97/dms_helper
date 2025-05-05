<head>
  <meta charset="UTF-8">
  <title>D&D Assistant Log</title>

  <!-- Global stylesheet -->
  <link rel="stylesheet" href="dnd_style.css">

  <!-- Guard: prevents duplicate custom‑element registrations
       when QtWebEngine re‑uses its renderer process -->
  <script>
    (function () {
      const origDefine = customElements.define.bind(customElements);

      /* Intercept every define() call */
      customElements.define = function (name, ctor, options) {
        if (!customElements.get(name)) {
          return origDefine(name, ctor, options);
        }
        /* already defined – ignore */
      };

      /* Optional helper if you want to call it manually later */
      window.safeDefine = function (name, ctor, options) {
        if (!customElements.get(name)) {
          return origDefine(name, ctor, options);
        }
      };
    })();
  </script>

  <!-- COMPONENTS_PLACEHOLDER -->
</head>
