<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>D&D Assistant</title>

  <!-- Google fonts used by statblock5e -->
  <link href="https://fonts.googleapis.com/css?family=Noto+Sans:400,700,400italic,700italic" rel="stylesheet" type="text/css">
  <link href="https://fonts.googleapis.com/css?family=Libre+Baskerville:700" rel="stylesheet" type="text/css">

  <!-- Global D&D styling (parchment background, heading colours, etc.) -->
  <link rel="stylesheet" href="css/dnd_style.css">

  <!-- Basic page-level styling -->
  <style>
    body { margin: 0; }
    stat-block { /* margin so drop-shadow shows */
      margin-left: 20px;
      margin-top: 20px;
    }
    /* log container styling – adjust as desired */
    .log-body {
      font-family: 'Noto Sans', sans-serif;
      padding: 0 1rem;
    }
  </style>

  <!-- Helper to turn <template> nodes into real custom elements -->
  <script>
  function createCustomElement(name, contentNode, elementClass = null) {
    if (elementClass === null) {
      customElements.define(
        name,
        class extends HTMLElement {
          constructor() {
            super();
            this.attachShadow({mode: 'open'})
                .appendChild(contentNode.cloneNode(true));
          }
        }
      );
    } else {
      customElements.define(name, elementClass(contentNode));
    }
  }
  </script>

  <!-- ────────── statblock5e custom-element templates ────────── -->
  <!-- stat-block root -->
  <template id="stat-block"><style>
    .bar { height: 5px; background: #E69A28; border: 1px solid #000; position: relative; z-index: 1; }
    :host { display: inline-block; }
    #content-wrap {
      font-family: 'Noto Sans', 'Myriad Pro', Calibri, Helvetica, Arial, sans-serif;
      font-size: 13.5px;
      background: #FDF1DC;
      padding: 0.6em 0.6em 0.5em 0.6em;
      border: 1px #DDD solid;
      box-shadow: 0 0 1.5em #867453;
      position: relative; z-index: 0;
      margin: 0 2px; /* room for bars */
      width: 400px;
      -webkit-columns: 400px; -moz-columns: 400px; columns: 400px;
      -webkit-column-gap: 40px; -moz-column-gap: 40px; column-gap: 40px;
      height: var(--data-content-height);
      -webkit-column-fill: auto; -moz-column-fill: auto; column-fill: auto;
    }
    :host([data-two-column]) #content-wrap { width: 840px; }
    ::slotted(h3) {
      border-bottom: 1px solid #7A200D; color: #7A200D; font-size: 21px;
      font-variant: small-caps; font-weight: normal; letter-spacing: 1px;
      margin: 0 0 0.3em 0; break-inside: avoid-column; break-after: avoid-column;
    }
    ::slotted(p) { margin: 0.3em 0 0.9em 0; line-height: 1.5; }
    ::slotted(*:last-child) { margin-bottom: 0; }
  </style>
  <div class="bar"></div>
  <div id="content-wrap"><slot></slot></div>
  <div class="bar"></div>
  </template>
  <script>{
    let templateElement = document.getElementById('stat-block');
    createCustomElement('stat-block', templateElement.content);
  }</script>

  <!-- creature-heading -->
  <template id="creature-heading"><style>
    ::slotted(h1) {
      font-family: 'Libre Baskerville', 'Lora', 'Calisto MT', 'Bookman Old Style',
                   Bookman, 'Goudy Old Style', Garamond, 'Hoefler Text',
                   'Bitstream Charter', Georgia, serif;
      color: #7A200D; font-weight: 700; margin: 0; font-size: 23px;
      letter-spacing: 1px; font-variant: small-caps;
    }
    ::slotted(h2) { font-weight: normal; font-style: italic; font-size: 12px; margin: 0; }
  </style><slot></slot></template>
  <script>{
    let t = document.getElementById('creature-heading');
    createCustomElement('creature-heading', t.content);
  }</script>

  <!-- tapered rule -->
  <template id="tapered-rule"><style>
    svg { fill: #922610; stroke: #922610; margin: 0.6em 0 0.35em 0; }
  </style>
  <svg height="5" width="400"><polyline points="0,0 400,2.5 0,5"></polyline></svg>
  </template>
  <script>{ let t = document.getElementById('tapered-rule'); createCustomElement('tapered-rule', t.content); }</script>

  <!-- top-stats wrapper -->
  <template id="top-stats"><style> ::slotted(*) { color: #7A200D; } </style>
    <tapered-rule></tapered-rule><slot></slot><tapered-rule></tapered-rule>
  </template>
  <script>{ let t = document.getElementById('top-stats'); createCustomElement('top-stats', t.content); }</script>

  <!-- abilities-block -->
  <template id="abilities-block"><style>
    table { width: 100%; border-collapse: collapse; }
    th, td { width: 50px; text-align: center; }
  </style>
    <tapered-rule></tapered-rule>
    <table>
      <tr><th>STR</th><th>DEX</th><th>CON</th><th>INT</th><th>WIS</th><th>CHA</th></tr>
      <tr><td id="str"></td><td id="dex"></td><td id="con"></td><td id="int"></td><td id="wis"></td><td id="cha"></td></tr>
    </table>
    <tapered-rule></tapered-rule>
  </template>
  <script>{
    function abilityModifier(score){ return Math.floor((parseInt(score,10)-10)/2); }
    function formattedModifier(mod){ return (mod>=0?'+':'–')+Math.abs(mod); }
    function abilityText(score){ return `${score} (${formattedModifier(abilityModifier(score))})`; }
    function elementClass(node){ return class extends HTMLElement{
      constructor(){ super(); this.attachShadow({mode:'open'}).appendChild(node.cloneNode(true)); }
      connectedCallback(){
        let root=this.shadowRoot;
        for(let i=0;i<this.attributes.length;i++){
          let attr=this.attributes[i];
          let key=attr.name.split('-')[1];
          root.getElementById(key).textContent=abilityText(attr.value);
        }
      }
    }; }
    let t=document.getElementById('abilities-block');
    createCustomElement('abilities-block', t.content, elementClass);
  }</script>

  <!-- property-line -->
  <template id="property-line"><style>
    :host { line-height:1.4; display:block; text-indent:-1em; padding-left:1em; }
    ::slotted(h4){ margin:0; display:inline; font-weight:bold; }
    ::slotted(p:first-of-type){ display:inline; text-indent:0; }
    ::slotted(p){ text-indent:1em; margin:0; }
  </style><slot></slot></template>
  <script>{ let t=document.getElementById('property-line'); createCustomElement('property-line', t.content); }</script>

  <!-- property-block -->
  <template id="property-block"><style>
    :host { margin:0.3em 0 0.9em 0; line-height:1.5; display:block; }
    ::slotted(h4){ margin:0; display:inline; font-weight:bold; font-style:italic; }
    ::slotted(p:first-of-type){ display:inline; text-indent:0; }
    ::slotted(p){ text-indent:1em; margin:0; }
  </style><slot></slot></template>
  <script>{ let t=document.getElementById('property-block'); createCustomElement('property-block', t.content); }</script>
  <!-- ────────── end statblock5e templates ────────── -->
</head>

<body class="log-body">
  <h1>D&D Assistant Log</h1>
  <p>LLM Suggestions will appear here…</p>
  <hr>
</body>
</html> 