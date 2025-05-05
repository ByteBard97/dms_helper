<!--
  statblock_components.html.tpl
  Assets extracted from https://github.com/Valloric/statblock5e
  and stripped of <html>/<head>/<body> wrappers so they can be
  inlined into another <head>.  Encoding: UTF‑8 (no BOM).
-->

<!-- Google web‑font used by the stylesheet -->
<link href="https://fonts.googleapis.com/css?family=Noto+Sans" rel="stylesheet">

<!-- ────────  Statblock5e CSS  ──────── -->
<style>
/* Core colours / layout */
:root {
  --sb-bg: #fdfdfd;
  --sb-border: #a22;
  --sb-title-bg: #a22;
  --sb-title-fg: #fff;
  --sb-section-bg: #eee;
  --sb-section-fg: #000;
  --sb-heading-fg: #a22;
  --sb-body-fg: #000;
  --sb-serif: 'Noto Sans', sans-serif;
}

stat-block, .stat-block {
  display: block;
  box-sizing: border-box;
  width: 420px;
  margin: 8px;
  border: 1px solid var(--sb-border);
  background: var(--sb-bg);
  font-family: var(--sb-serif);
  color: var(--sb-body-fg);
  -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
}

/* Title bar ---------------------------------------------------------- */
stat-block h1, .stat-block h1 {
  margin: 0;
  padding: 4px 8px;
  font-size: 22px;
  font-weight: bold;
  line-height: 26px;
  letter-spacing: 0.5px;
  color: var(--sb-title-fg);
  background: var(--sb-title-bg);
}

/* Property rows ------------------------------------------------------ */
stat-block property-block,
.property-block {
  display: flex;
  padding: 4px 8px;
  justify-content: space-between;
  border-bottom: 1px solid var(--sb-border);
  font-size: 14px;
}
property-block[label]::before,
.property-block[label]::before {
  content: attr(label) ':';
  font-weight: bold;
  margin-right: 4px;
}

/* Ability scores bar ------------------------------------------------- */
top-stats-bar, .top-stats-bar {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid var(--sb-border);
  background: var(--sb-section-bg);
}
top-stats-bar stat-block-cell, .top-stats-bar .stat-block-cell {
  flex: 1 1 0;
  text-align: center;
  padding: 4px 0;
  font-size: 13px;
}
stat-block-cell[label]::before,
.stat-block-cell[label]::before {
  display: block;
  content: attr(label);
  font-weight: bold;
  color: var(--sb-heading-fg);
}

/* Section headings --------------------------------------------------- */
.stat-block-heading {
  padding: 0 8px;
  font-weight: bold;
  color: var(--sb-heading-fg);
  font-size: 15px;
}

/* Paragraphs inside stat‑block -------------------------------------- */
stat-block p, .stat-block p {
  margin: 0;
  padding: 0 8px 4px 8px;
  font-size: 13px;
  line-height: 17px;
}

/* Bullet lists ------------------------------------------------------- */
stat-block ul, .stat-block ul {
  margin: 4px 8px;
  padding-left: 16px;
  font-size: 13px;
}
</style>

<!-- ────────  Statblock5e JS  ──────── -->
<script>
/* Utility: converts modifier number to signed string */
function formatMod(mod) {
  return (mod >= 0 ? '+' : '') + mod;
}

/* <property-block> --------------------------------------------------- */
class PropertyBlock extends HTMLElement {
  connectedCallback() {
    const label = this.getAttribute('label') || '';
    const value = this.innerHTML.trim();
    this.innerHTML = '<span>' + label + ':</span><span>' + value + '</span>';
  }
}
customElements.define('property-block', PropertyBlock);

/* <stat-block-cell> -------------------------------------------------- */
class StatBlockCell extends HTMLElement {
  connectedCallback() {
    const label = this.getAttribute('label') || '';
    const value = this.innerHTML.trim();
    this.innerHTML = '<div>' + label + '</div><div>' + value + '</div>';
    this.style.fontSize = '13px';
  }
}
customElements.define('stat-block-cell', StatBlockCell);

/* <top-stats-bar> ---------------------------------------------------- */
class TopStatsBar extends HTMLElement {
  connectedCallback() { /* acts as a flex container */ }
}
customElements.define('top-stats-bar', TopStatsBar);

/* <stat-block> ------------------------------------------------------- */
class StatBlock extends HTMLElement {
  connectedCallback() {
    /* Nothing to do; children render themselves */
  }
}
customElements.define('stat-block', StatBlock);
</script>
