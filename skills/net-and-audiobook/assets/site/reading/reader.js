/* Shared reading layer: native MathML, precise unit navigation, no network dependencies. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/1998/Math/MathML';
  const commands = {alpha:'α',beta:'β',gamma:'γ',delta:'δ',epsilon:'ε',varepsilon:'ϵ',zeta:'ζ',eta:'η',theta:'θ',vartheta:'ϑ',iota:'ι',kappa:'κ',lambda:'λ',mu:'μ',nu:'ν',xi:'ξ',pi:'π',rho:'ρ',sigma:'σ',tau:'τ',upsilon:'υ',phi:'φ',varphi:'ϕ',chi:'χ',psi:'ψ',omega:'ω',Gamma:'Γ',Delta:'Δ',Theta:'Θ',Lambda:'Λ',Xi:'Ξ',Pi:'Π',Sigma:'Σ',Phi:'Φ',Psi:'Ψ',Omega:'Ω',infty:'∞',partial:'∂',nabla:'∇',times:'×',cdot:'·',pm:'±',mp:'∓',gg:'≫',ll:'≪',ge:'≥',geq:'≥',le:'≤',leq:'≤',ne:'≠',neq:'≠',approx:'≈',sim:'∼',propto:'∝',perp:'⊥',parallel:'∥',to:'→'};
  const node = (tag, text, children) => { const n = document.createElementNS(NS, tag); if (text != null) n.textContent = text; if (children) n.append(...children); return n; };
  const scripts = { '²':'2','³':'3','¹':'1','⁰':'0','⁻':'−','⁺':'+','₀':'0','₁':'1','₂':'2','₃':'3','₄':'4','₅':'5','₆':'6','₇':'7','₈':'8','₉':'9','ₑ':'e','ᵢ':'i','ₚ':'p' };
  const operators = new Set([...'+−-×·⋅÷=<>≥≤≠≈∼≫≪±∓∝∈∉∑∫∂∇∞⊥∥→|,:;!%']);
  function parseMath(source) {
    let s = source.replace(/\\([A-Za-z]+)/g, (all, key) => commands[key] || all).replace(/>>/g,'≫').replace(/<</g,'≪').replace(/>=/g,'≥').replace(/<=/g,'≤').replace(/!=/g,'≠');
    if (/\\/.test(s)) return null; // Unknown commands are review items, never guessed.
    let i = 0, valid = true;
    const skip = () => { while (/\s/.test(s[i] || '') && i < s.length) i++; };
    function atom(script = false) {
      skip(); const c = s[i]; if (!c) return null;
      let n;
      if ('({['.includes(c)) {
        i++; const end = {'(':')','{':'}','[':']'}[c], inner = row(end); if (s[i] !== end) { valid=false; return null; } i++;
        n = c === '{' ? inner : node('mrow',null,[node('mo',c),inner,node('mo',end)]);
      } else if (script && /^[+−-]\d/.test(s.slice(i))) { const m=s.slice(i).match(/^[+−-]\d+(?:\.\d+)?/)[0];i+=m.length;n=node('mn',m.replace('-','−')); }
      else if (/\d/.test(c)) { const m = s.slice(i).match(/^\d+(?:\.\d+)?/)[0]; i += m.length; n=node('mn',m); }
      else if (/[A-Za-zΑ-ωϵϑϕℓ]/.test(c)) {
        let m;
        if (script) m = s.slice(i).match(/^[A-Za-zΑ-ωϵϑϕℓ]+/)[0];
        else m = s.slice(i).match(/^(?:sin|cos|tan|exp|log|ln|max|min|cm|km|keV|MeV|eV|nT|nPa|Pa|mHz|Hz|kg)(?![A-Za-z])/)?.[0] || c;
        i += m.length; n=node('mi',m); if (m.length > 1) n.setAttribute('mathvariant','normal');
      } else if (operators.has(c)) { i++; n=node('mo',c === '-' ? '−' : c); }
      else { valid=false; return null; }
      if (script) return n;
      let sub=null,sup=null;
      while (i < s.length) {
        if (s[i] === '_' || s[i] === '^') { const op=s[i++], value=atom(true); if (!value || (op==='_'?sub:sup)) { valid=false;return null; } if(op==='_')sub=value;else sup=value; }
        else if (scripts[s[i]]) { const isSub='₀₁₂₃₄₅₆₇₈₉ₑᵢₚ'.includes(s[i]); let value='';while(scripts[s[i]] && '₀₁₂₃₄₅₆₇₈₉ₑᵢₚ'.includes(s[i])===isSub)value+=scripts[s[i++]];if(isSub)sub=node('mi',value);else sup=node(/^\d+$/.test(value)?'mn':'mrow',value); }
        else break;
      }
      return sub && sup ? node('msubsup',null,[n,sub,sup]) : sub ? node('msub',null,[n,sub]) : sup ? node('msup',null,[n,sup]) : n;
    }
    function row(end) {
      const children=[];
      while(i<s.length) { skip(); if(i>=s.length || s[i]===end)break;
        if(s[i]==='/') { i++;const a=children.pop(),b=atom();if(!a||!b){valid=false;break;}children.push(node('mfrac',null,[a,b])); }
        else { const n=atom();if(!n)break;children.push(n); }
      }
      return node('mrow',null,children);
    }
    const result=row(); return valid && i===s.length && result.childNodes.length ? result : null;
  }
  // A math island must contain explicit notation. Ordinary words, filenames and code stay text.
  const base = String.raw`(?:\\[A-Za-z]+|cm|km|keV|MeV|eV|nT|nPa|Pa|mHz|Hz|kg|[A-Za-zΑ-ωϵϑϕℓ]|\d+(?:\.\d+)?)`;
  const script = String.raw`(?:[_^](?:\{[^{}\n]+\}|[A-Za-zΑ-ωϵϑϕℓ]+|[+−-]?\d+)|[²³¹⁰⁻⁺₀₁₂₃₄₅₆₇₈₉ₑᵢₚ]+)`;
  const atomPattern = String.raw`(?<![A-Za-z0-9_.\\])${base}(?:${script})*(?![A-Za-z0-9_.])`;
  const tokenPattern = new RegExp(`${atomPattern}|${script}|[+−×·⋅÷=<>≥≤≠≈∼≫≪±∓∝⊥∥→/(){}\\[\\]|,:;%!-]`, 'gu');
  function islands(text) {
    const tokens=[...text.matchAll(tokenPattern)], out=[]; let group=[];
    const flush=()=>{if(!group.length)return;let a=group[0].index,b=group.at(-1).index+group.at(-1)[0].length;
      let value=text.slice(a,b);
      const wordStart=text.slice(0,a).search(/[^\s，。；：！？（）]+$/),wordEnd=text.slice(b).search(/[\s，。；：！？（）]/);
      const word=text.slice(wordStart<0?a:wordStart,wordEnd<0?text.length:b+wordEnd);
      if(/:\/\/|[A-Za-z]:\\|\.(?:json|js|css|html|pdf|png|jpg|mp3|zip)\b/i.test(word)){group=[];return;}
      // Punctuation at an island edge belongs to the surrounding sentence.
      while(/^[,;:!/)+−-]/.test(value)){a++;value=value.slice(1);}while(/[,;:!(+−-]$/.test(value)){b--;value=value.slice(0,-1);}
      if(/[_^\\²³₀₁₂₃₄₅₆₇₈₉]/.test(value) || (/[Α-ωϵϑϕℓ]/.test(value)&&/[=<>≥≤≠≈≫≪]/.test(value)) || /^[A-Za-z]\s*[=<>≥≤≠≈≫≪]/.test(value)) {
        // Do not absorb an unmatched sentence parenthesis into the formula.
        while(value.startsWith('(')&&[...value].filter(c=>c==='(').length>[...value].filter(c=>c===')').length){a++;value=value.slice(1);}
        while(value.endsWith(')')&&[...value].filter(c=>c===')').length>[...value].filter(c=>c==='(').length){b--;value=value.slice(0,-1);}
        if(value && parseMath(value))out.push({start:a,end:b,source:value});
      }group=[];};
    for(const t of tokens){if(group.length && !/^\s*$/.test(text.slice(group.at(-1).index+group.at(-1)[0].length,t.index)))flush();group.push(t);}flush();return out;
  }
  const skipSelector='script,style,svg,math,pre,code,kbd,samp,textarea,input,select,[contenteditable],[data-no-math],.page-text,.img-missing-name';
  function typeset(root=document.body) {
    if(!root || root.nodeType!==1 || root.closest(skipSelector))return 0;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>/[_^\\²³₀₁₂₃₄₅₆₇₈₉=≥≤≫≪]/.test(n.data)&&!n.parentElement.closest(skipSelector)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT});
    const texts=[];while(walker.nextNode())texts.push(walker.currentNode);let count=0;
    for(const t of texts){const found=islands(t.data);if(!found.length)continue;const f=document.createDocumentFragment();let last=0;
      for(const m of found){f.append(document.createTextNode(t.data.slice(last,m.start)));const math=node('math',null,[parseMath(m.source)]);math.classList.add('reader-math');math.setAttribute('display','inline');math.setAttribute('aria-label',m.source);math.dataset.mathSource=m.source;f.append(math);last=m.end;count++;}f.append(document.createTextNode(t.data.slice(last)));t.replaceWith(f);
    }return count;
  }
  let adapter=null, units=[], links=new Map(), current='', frame=0, hold=null, navQuietUntil=0, refreshQueued=false;
  const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
  const visible=n=>!n.hidden && n.getClientRects().length>0;
  function headerOffset(){const h=document.querySelector('.topbar')||document.querySelector('body > header');const b=h?.getBoundingClientRect().bottom||0;return Math.max(0,b)+20;}
  function setOffset(){document.documentElement.style.setProperty('--reader-offset',`${Math.ceil(headerOffset())}px`);}
  function identify(){
    if(document.querySelector('.toc-nav'))return {kind:'course',nav:document.querySelector('.toc'),selector:'.unit[data-unit]',link:'.toc-sub',id:n=>n.dataset.unit,linkId:n=>decodeURIComponent(n.hash.slice(1))};
    if(window.PAPER_DATA || document.querySelector('.block-nav'))return {kind:'paper',nav:document.querySelector('.study-nav'),selector:'.reading-block[data-block-id]',link:'[data-scroll-block]',id:n=>n.dataset.blockId,linkId:n=>n.dataset.scrollBlock};
    if(window.LEARNING_PROJECT && document.querySelector('#chapters'))return {kind:'project',nav:document.querySelector('#nav'),selector:'.unit[data-unit]',link:'[data-reader-unit]',id:n=>n.dataset.unit,linkId:n=>n.dataset.readerUnit};
    return null;
  }
  function projectLinks(){
    if(!window.LEARNING_PROJECT)return;
    for(const c of window.LEARNING_PROJECT.chapters){const b=document.querySelector(`#chapters [data-chapter="${CSS.escape(c.id)}"]`);if(!b || b.nextElementSibling?.dataset.readerChapter===c.id)continue;
      const list=document.createElement('div');list.className='reader-unit-list';list.dataset.readerChapter=c.id;
      for(const u of c.units){const a=document.createElement('a');a.href='#'+encodeURIComponent(u.id);a.dataset.readerUnit=u.id;a.dataset.readerChapterId=c.id;a.textContent=u.title_zh;list.append(a);}b.after(list);
    }
  }
  function follow(link,force=false){
    if(!adapter?.nav || !visible(link) || (!force&&performance.now()<navQuietUntil))return;
    const box=adapter.nav.getBoundingClientRect(),r=link.getBoundingClientRect(),pad=24;
    if(r.top>=box.top+pad && r.bottom<=box.bottom-pad)return;
    const target=adapter.nav.scrollTop+r.top-box.top-Math.max(pad,(box.height-r.height)*.42);
    adapter.nav.scrollTo({top:Math.max(0,target),behavior:reduced()?'instant':'smooth'});
  }
  function activate(id,force=false){
    const changed=current!==id;current=id;
    for(const [key,link] of links){const yes=key===id;link.classList.toggle('reader-current',yes);if(yes)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');
      if(adapter.kind==='paper')link.classList.toggle('active',yes);
    }
    document.querySelectorAll('.reader-context').forEach(n=>n.classList.remove('reader-context'));
    const chosen=links.get(id);if(chosen){chosen.closest('.toc-row')?.classList.add('reader-context');if(changed||force)follow(chosen,force);}
    if(changed||force)document.dispatchEvent(new CustomEvent('reader:unit',{detail:{id,kind:adapter.kind}}));
  }
  function spy(){frame=0;if(!adapter)return;const shown=units.filter(visible);if(!shown.length){activate('');return;}
    if(hold){const target=document.getElementById(hold.id);if(target && performance.now()<hold.until && Math.abs(target.getBoundingClientRect().top-headerOffset())>3){activate(hold.id);return;}hold=null;}
    const threshold=headerOffset()+4;let best=null;
    for(const n of shown){if(n.getBoundingClientRect().top<=threshold)best=n;else break;}
    if(!best && shown[0].getBoundingClientRect().top<innerHeight*.7)best=shown[0];
    if(window.scrollY+innerHeight>=document.documentElement.scrollHeight-3)best=shown.at(-1);
    activate(best?adapter.id(best):'');
  }
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(spy);};
  function refresh(){refreshQueued=false;projectLinks();
    const synopsis=document.querySelector('.topbar .sub-title'),intro=document.querySelector('.content .intro');
    if(synopsis&&intro&&!intro.querySelector('.course-synopsis')){const copy=document.createElement('p');copy.className='course-synopsis';copy.append(...[...synopsis.childNodes].map(n=>n.cloneNode(true)));intro.append(copy);}
    typeset(document.body);adapter=identify();units=adapter?[...document.querySelectorAll(adapter.selector)]:[];links=new Map(adapter?[...document.querySelectorAll(adapter.link)].map(n=>[adapter.linkId(n),n]):[]);
    if(adapter){document.documentElement.dataset.reader=adapter.kind;if(adapter.nav){adapter.nav.classList.add('reader-nav');if(!adapter.nav.dataset.readerEvents){adapter.nav.dataset.readerEvents='1';for(const e of ['wheel','touchstart','pointerdown','keydown'])adapter.nav.addEventListener(e,()=>{navQuietUntil=performance.now()+1600;},{passive:true});}}}
    setOffset();schedule();
  }
  function queueRefresh(){if(!refreshQueued){refreshQueued=true;requestAnimationFrame(refresh);}}
  function navigate(id){const n=document.getElementById(id);if(!n || !visible(n))return false;hold={id,until:performance.now()+1000};activate(id,true);
    const top=window.scrollY+n.getBoundingClientRect().top-headerOffset();window.scrollTo({top:Math.max(0,top),behavior:reduced()?'instant':'smooth'});return true;
  }
  document.addEventListener('click',e=>{const a=e.target.closest('.toc-sub,[data-scroll-block],[data-reader-unit]');if(!a||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
    const id=a.dataset.scrollBlock||a.dataset.readerUnit||decodeURIComponent(a.hash.slice(1));
    if(a.dataset.readerUnit){const b=document.querySelector(`#chapters [data-chapter="${CSS.escape(a.dataset.readerChapterId)}"]`);b?.click();requestAnimationFrame(()=>{refresh();navigate(id);if(visible(document.getElementById(id)))history.replaceState(null,'','#'+encodeURIComponent(id));});}
    else if(navigate(id)){if(!a.dataset.scrollBlock)history.replaceState(null,'','#'+encodeURIComponent(id));document.body.classList.remove('toc-open');document.getElementById('tocBtn')?.setAttribute('aria-expanded','false');}
    else return;e.preventDefault();e.stopImmediatePropagation();
  },true);
  for(const event of ['scroll','resize','hashchange'])window.addEventListener(event,event==='resize'?()=>{setOffset();schedule();}:schedule,{passive:true});
  for(const event of ['wheel','touchstart','pointerdown','keydown'])window.addEventListener(event,()=>{hold=null;},{passive:true});
  const observer=new MutationObserver(records=>{if(records.some(r=>r.type==='childList'&&[...r.addedNodes].some(n=>n.nodeType===1&&!n.matches('math,.reader-unit-list')&&!n.closest('math')) || r.type==='attributes'&&['hidden','data-lang'].includes(r.attributeName)))queueRefresh();});
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden']});
  observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-lang']});
  const header=document.querySelector('.topbar')||document.querySelector('body > header');if(header&&window.ResizeObserver)new ResizeObserver(()=>{setOffset();schedule();}).observe(header);
  document.addEventListener('load',schedule,true);document.addEventListener('toggle',schedule,true);
  window.NBAReader={version:'2026.10.31',typeset,parseMath,refresh,navigate,current:()=>current,unresolved:(root=document.body)=>{const out=[],w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);while(w.nextNode()){const n=w.currentNode;if(/[_^\\]/.test(n.data)&&!n.parentElement.closest(skipSelector))out.push(n.data.trim());}return out;}};
  refresh();
})();
