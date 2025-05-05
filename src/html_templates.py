"""
Pixel‑perfect statblock5e bundle for LLMOutputWidget.

Copy to src/html_templates.py  (UTF‑8, no BOM).
"""

html_content = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>D&D Assistant Log</title>

  <!-- App header style -->
  <style>
    body      { margin:0; background:#111; color:#ddd; font-family:'Noto Sans',sans-serif; }
    #header   { margin:0; padding:8px 12px; background:#000; color:#eee;
                font-weight:700; border-bottom:1px solid #444; }
  </style>

  <!-- Google fonts used by statblock.css -->
  <link href="https://fonts.googleapis.com/css?family=Noto+Sans:400,700,400italic,700italic"
        rel="stylesheet" type="text/css">
  <link href="https://fonts.googleapis.com/css?family=Libre+Baskerville:700"
        rel="stylesheet" type="text/css">

  <!-- Guard: ignore duplicate customElements.define() on fast relaunch -->
  <script>
    (function(){
      const orig = customElements.define.bind(customElements);
      customElements.define = function(n,c,o){
        if(!customElements.get(n)){ return orig(n,c,o); }
      };
    })();
  </script>

  <!-- =================  original statblock5e templates  ================= -->
  <!-- ***** EVERYTHING BELOW IS VERBATIM FROM Valloric/statblock5e ***** -->

  <script>
  /* helper shared by templates */
  function createCustomElement(name, contentNode, elementClass=null){
    if(elementClass===null){
      customElements.define(name,
        class extends HTMLElement{
          constructor(){
            super();
            this.attachShadow({mode:'open'})
                .appendChild(contentNode.cloneNode(true));
          }}
      );
    }else{
      customElements.define(name, elementClass(contentNode));
    }
  }
  </script>

  <!-- stat-block -->
  <template id="stat-block">
    <style>
      .bar{height:5px;background:#E69A28;border:1px solid #000;position:relative;z-index:1;}
      :host{display:inline-block;}
      #content-wrap{
        font-family:'Noto Sans','Myriad Pro',Calibri,Helvetica,Arial,sans-serif;
        font-size:13.5px;background:#FDF1DC;padding:0.6em 0.6em 0.5em;
        border:1px #DDD solid;box-shadow:0 0 1.5em #867453;position:relative;
        z-index:0;margin:0 2px;width:400px;
        -webkit-columns:400px;   columns:400px;
        -webkit-column-gap:40px; column-gap:40px;
        height:var(--data-content-height);
        -webkit-column-fill:auto;column-fill:auto;
      }
      :host([data-two-column]) #content-wrap{width:840px;}
      ::slotted(h3){
        border-bottom:1px solid #7A200D;color:#7A200D;font-size:21px;
        font-variant:small-caps;letter-spacing:1px;margin:0 0 0.3em 0;
        break-inside:avoid-column;break-after:avoid-column;
      }
      ::slotted(p){margin:0.3em 0 0.9em 0;line-height:1.5;}
      ::slotted(*:last-child){margin-bottom:0;}
    </style>
    <div class="bar"></div>
    <div id="content-wrap"><slot></slot></div>
    <div class="bar"></div>
  </template>
  <script>{
    const tpl=document.getElementById('stat-block');
    createCustomElement('stat-block', tpl.content);
  }</script>

  <!-- creature-heading -->
  <template id="creature-heading">
    <style>
      ::slotted(h1){
        font-family:'Libre Baskerville','Lora','Calisto MT','Bookman Old Style',
                     Bookman,'Goudy Old Style',Garamond,'Hoefler Text',
                     'Bitstream Charter',Georgia,serif;
        color:#7A200D;font-weight:700;margin:0;font-size:23px;
        letter-spacing:1px;font-variant:small-caps;
      }
      ::slotted(h2){font-weight:normal;font-style:italic;font-size:12px;margin:0;}
    </style>
    <slot></slot>
  </template>
  <script>{
    const tpl=document.getElementById('creature-heading');
    createCustomElement('creature-heading', tpl.content);
  }</script>

  <!-- tapered-rule -->
  <template id="tapered-rule">
    <style>
      svg{fill:#922610;stroke:#922610;margin:0.6em 0 0.35em 0;}
    </style>
    <svg height="5" width="400">
      <polyline points="0,0 400,2.5 0,5"></polyline>
    </svg>
  </template>
  <script>{
    const tpl=document.getElementById('tapered-rule');
    createCustomElement('tapered-rule', tpl.content);
  }</script>

  <!-- top-stats -->
  <template id="top-stats">
    <style>::slotted(*){color:#7A200D;}</style>
    <tapered-rule></tapered-rule><slot></slot><tapered-rule></tapered-rule>
  </template>
  <script>{
    const tpl=document.getElementById('top-stats');
    createCustomElement('top-stats', tpl.content);
  }</script>

  <!-- abilities-block -->
  <template id="abilities-block">
    <style>
      table{width:100%;border-collapse:collapse;}
      th,td{width:50px;text-align:center;}
    </style>
    <tapered-rule></tapered-rule>
    <table>
      <tr><th>STR</th><th>DEX</th><th>CON</th><th>INT</th><th>WIS</th><th>CHA</th></tr>
      <tr>
        <td id="str"></td><td id="dex"></td><td id="con"></td>
        <td id="int"></td><td id="wis"></td><td id="cha"></td>
      </tr>
    </table>
    <tapered-rule></tapered-rule>
  </template>
  <script>{
    function abilityModifier(s){return Math.floor((parseInt(s,10)-10)/2);}
    function fmt(m){return (m>=0?'+':'\u2013')+Math.abs(m);}
    function abilityText(s){return s+' ('+fmt(abilityModifier(s))+')';}
    const tpl=document.getElementById('abilities-block');
    createCustomElement('abilities-block', tpl.content, node=>class extends HTMLElement{
      constructor(){super();this.attachShadow({mode:'open'})
                               .appendChild(node.cloneNode(true));}
      connectedCallback(){
        ['str','dex','con','int','wis','cha'].forEach(attr=>{
          const v=this.getAttribute('data-'+attr); if(v){
            this.shadowRoot.getElementById(attr).textContent=abilityText(v);
          }
        });
      }
    });
  }</script>

  <!-- property-line -->
  <template id="property-line">
    <style>
      :host{line-height:1.4;display:block;text-indent:-1em;padding-left:1em;}
      ::slotted(h4){margin:0;display:inline;font-weight:bold;}
      ::slotted(p:first-of-type){display:inline;text-indent:0;}
      ::slotted(p){text-indent:1em;margin:0;}
    </style>
    <slot></slot>
  </template>
  <script>{
    const tpl=document.getElementById('property-line');
    createCustomElement('property-line', tpl.content);
  }</script>

  <!-- property-block -->
  <template id="property-block">
    <style>
      :host{margin:0.3em 0 0.9em 0;line-height:1.5;display:block;}
      ::slotted(h4){margin:0;display:inline;font-weight:bold;font-style:italic;}
      ::slotted(p:first-of-type){display:inline;text-indent:0;}
      ::slotted(p){text-indent:1em;margin:0;}
    </style>
    <slot></slot>
  </template>
  <script>{
    const tpl=document.getElementById('property-block');
    createCustomElement('property-block', tpl.content);
  }</script>

  <!-- ================= end of statblock5e templates ================= -->
</head>

<body>
  <h2 id="header">D&D Assistant Log</h2>
  <!-- LLMOutputWidget.append_html() will insert each <stat-block> below -->
</body>
</html>
"""
