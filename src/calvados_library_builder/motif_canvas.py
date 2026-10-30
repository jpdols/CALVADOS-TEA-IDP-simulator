"""Draggable mono-motif ELP architecture canvas (Streamlit v2 component).

Each colored ball denotes one motif instance. Consecutive identical motifs
form one bracketed run with a repeat badge. Hover/focus on a run exposes the
four requested operations; reorder via HTML Drag and Drop or arrow controls.
"""
from __future__ import annotations

import streamlit as st

CSS = """
.elp-board{font-family:"Suisse Intl","Suisse","Helvetica Neue",Arial,sans-serif;color:var(--st-text-color);padding:16px;border:1px solid var(--st-border-color,#d6dbe1);border-radius:14px;background:var(--st-secondary-background-color,#f8fafc)}
.elp-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.elp-title{font-size:15px;font-weight:700}.elp-hint{font-size:12px;opacity:.7}
.elp-palette{display:flex;flex-wrap:wrap;gap:7px;margin-top:13px}
.elp-add{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--st-border-color,#ccd3dc);border-radius:18px;padding:5px 10px;background:var(--st-background-color,#fff);color:var(--st-text-color,#222);font:inherit;font-size:12px;cursor:pointer}
.elp-add:hover,.elp-add:focus-visible{border-color:var(--st-primary-color,#a78bfa)}
.elp-dot{display:inline-block;width:16px;height:16px;flex:none;border:1px solid #0002;border-radius:50%;box-shadow:inset 0 -2px 3px #0002}
.elp-lane{display:flex;flex-wrap:wrap;align-items:center;min-height:90px;padding:18px 12px 22px;margin-top:14px;border:1px dashed var(--st-border-color,#d2dae3);border-radius:12px;background:var(--st-background-color,#fff);gap:0}
.elp-run{display:inline-flex;position:relative;flex-direction:column;align-items:center;min-width:53px;padding:6px 8px 10px;margin:10px 0 5px;border-radius:11px;cursor:grab;border:1px solid transparent;user-select:none}
.elp-run:hover,.elp-run:focus-within,.elp-run:focus-visible{border-color:var(--st-primary-color,#a78bfa);background:var(--st-secondary-background-color,#eef2f7);z-index:5}
.elp-run.dragging{opacity:.35}.elp-run:active{cursor:grabbing}
.elp-beads{display:flex;align-items:center;justify-content:center;min-width:42px;padding:2px 4px}
.elp-bead{display:inline-block;flex:0 0 25px;width:25px;height:25px;border-radius:50%;border:1px solid #0002;box-shadow:inset 0 -3px 4px #0002}
.elp-more{font-size:11px;font-weight:600;opacity:.65}
.elp-bracket{margin-top:6px;width:calc(100% - 13px);height:8px;border-left:1.5px solid var(--st-text-color,#333);border-right:1.5px solid var(--st-text-color,#333);border-bottom:1.5px solid var(--st-text-color,#333);opacity:.55}
.elp-count{font-size:11px;font-weight:700;margin-top:3px;white-space:nowrap}
.elp-runname{font-size:10px;opacity:.65;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.elp-gap{width:12px;min-height:54px;border-radius:8px;align-self:center}
.elp-gap.over{background:var(--st-primary-color,#a78bfa)}
.elp-tools{display:none;position:absolute;z-index:20;top:-36px;left:50%;transform:translateX(-50%);align-items:center;gap:3px;padding:5px 6px;border:1px solid var(--st-border-color,#ccd3dc);border-radius:9px;background:var(--st-background-color,#fff);box-shadow:0 5px 18px #0002;white-space:nowrap;cursor:default}
.elp-run:hover .elp-tools,.elp-run:focus-within .elp-tools{display:flex}
.elp-tool{min-width:26px;height:25px;padding:0 5px;border:1px solid transparent;border-radius:6px;color:var(--st-text-color);background:transparent;font-size:12px;cursor:pointer}
.elp-tool:hover,.elp-tool:focus-visible{background:var(--st-secondary-background-color,#eee);border-color:var(--st-border-color,#ccd3dc)}
.elp-tool:disabled{opacity:.35;cursor:not-allowed}
.elp-num{width:47px;height:26px;border:1px solid var(--st-border-color,#ccd3dc);border-radius:6px;background:var(--st-background-color,#fff);color:var(--st-text-color);font:inherit;font-size:12px;text-align:center}
.elp-bottom{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px;font-size:12px;opacity:.8;flex-wrap:wrap}
.elp-empty{font-size:13px;opacity:.7;padding:10px}
"""


JS = r"""
export default function(component) {
  const {parentElement, data, setStateValue} = component;
  const host = parentElement.querySelector(".elp-motif-root");
  if (!host) return;
  const motifs = data?.motifs || {};
  const revision = data?.revision ?? 0;
  const initial = Array.isArray(data?.groups) ? data.groups : [];
  if (!host.__model || host.__model.revision !== revision) {
    host.__model = {runs: initial.flatMap(g => (g.segments||[]).map((s,j) => ({
      motif:s.motif,count:s.count,split_before: !!g.split_before && j===0
    }))),revision};
  }
  const model=host.__model;
  const elt=(tag, cls, label)=> {
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(label!==undefined)node.textContent=label;
    return node;
  };
  const isKnown=(name)=>Object.prototype.hasOwnProperty.call(motifs,name);
  function compact(runs, keepSplit=true) {
    const out=[];
    for(const raw of runs) {
      if(!isKnown(raw.motif)||!Number.isInteger(raw.count)||raw.count<1||raw.count>5000)continue;
      const item={motif:raw.motif,count:raw.count,split_before:!!raw.split_before && keepSplit};
      const prev=out[out.length-1];
      if(prev && prev.motif===item.motif && !item.split_before && prev.count+item.count<=5000) {
        prev.count+=item.count;
      } else out.push(item);
    }
    return out;
  }
  function validate(runs) {
    if(runs.length>2000)return false;
    let residues=0;
    for(const r of runs) {
      if(!isKnown(r.motif)||!Number.isInteger(r.count)||r.count<1||r.count>5000)return false;
      residues+=(motifs[r.motif].sequence||"").length*r.count;
    }
    return residues<=50000;
  }
  function commit(runs, keepSplit=true) {
    const changed=compact(runs,keepSplit);
    if(!validate(changed)) { window.alert("Sequence limit: 50,000 residues, 2,000 blocks, or 5,000 repeats per block.");return; }
    model.runs=changed;
    setStateValue("groups",changed.map(r=>({
      segments:[{motif:r.motif,count:r.count}],
      ...(r.split_before?{split_before:true}:{})
    })));
    draw();
  }
  function move(source, gap) {
    if(!Number.isInteger(source)||source<0||source>=model.runs.length)return;
    const copy=model.runs.map(r=>({...r}));
    const [item]=copy.splice(source,1);
    const index=source<gap?gap-1:gap;
    copy.splice(Math.max(0,Math.min(index,copy.length)),0,item);
    commit(copy,false);
  }
  function add(name) {
    if(!isKnown(name))return;
    commit([...model.runs,{motif:name,count:1}]);
  }
  function tool(label,title,handler,disabled=false) {
    const b=elt("button","elp-tool",label);
    b.type="button";b.title=title;b.setAttribute("aria-label",title);b.disabled=disabled;
    b.onclick=e=>{e.stopPropagation();if(!b.disabled)handler();};
    b.ondragstart=e=>e.preventDefault();
    return b;
  }
  function draw() {
    host.replaceChildren();
    const root=elt("div","elp-board");host.append(root);
    const header=elt("div","elp-header");root.append(header);
    header.append(elt("span","elp-title","ELP motif architecture"),
      elt("span","elp-hint","Drag blocks to reorder · hover for controls"));
    const palette=elt("div","elp-palette");root.append(palette);
    for(const [name,m] of Object.entries(motifs)) {
      const b=elt("button","elp-add");b.type="button";
      const dot=elt("span","elp-dot");dot.style.backgroundColor=m.color||"#9CA3AF";
      b.title="Add "+(m.label||name)+" ("+m.sequence+")";b.append(dot,elt("span","",(m.label||name)+" +"));
      b.onclick=()=>add(name);palette.append(b);
    }
    const lane=elt("div","elp-lane");root.append(lane);
    if(!model.runs.length)lane.append(elt("div","elp-empty","Choose any motif above to start building your ELP."));
    const gap=(index)=>{
      const n=elt("div","elp-gap");n.title="Drop block here";
      n.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect="move";n.classList.add("over");};
      n.ondragleave=()=>n.classList.remove("over");
      n.ondrop=e=>{e.preventDefault();e.stopPropagation();n.classList.remove("over");
        const raw=e.dataTransfer.getData("application/x-elp-run");
        if(raw!=="")move(Number(raw),index);
      };lane.append(n);
    };
    gap(0);
    model.runs.forEach((item,i)=>{
      const run=elt("div","elp-run");run.tabIndex=0;run.draggable=true;
      run.setAttribute("role","group");run.setAttribute("aria-label",item.motif+" repeated "+item.count+" times");
      run.title="Drag to reorder "+item.motif+" ×"+item.count;
      run.ondragstart=e=>{
        e.dataTransfer.setData("application/x-elp-run",String(i));
        e.dataTransfer.effectAllowed="move";run.classList.add("dragging");
      };
      run.ondragend=()=>run.classList.remove("dragging");
      const controls=elt("div","elp-tools");
      controls.append(
        tool("+1","Add one "+item.motif,()=>{const copy=model.runs.map(r=>({...r}));if(copy[i].count<5000){copy[i].count++;commit(copy);}},item.count>=5000),
        tool("−1","Remove one "+item.motif,()=>{const copy=model.runs.map(r=>({...r}));if(copy[i].count===1)copy.splice(i,1);else copy[i].count--;commit(copy);}),
        tool("⫽","Split this block into two draggable parts",()=>{
          if(item.count<2)return;
          const copy=model.runs.map(r=>({...r})),a=Math.floor(item.count/2),b=item.count-a;
          copy.splice(i,1,{...item,count:a},{motif:item.motif,count:b,split_before:true});commit(copy);
        },item.count<2),
        tool("×","Delete entire block",()=>{const copy=model.runs.map(r=>({...r}));copy.splice(i,1);commit(copy);})
      );
      const number=elt("input","elp-num");number.type="number";number.min="1";number.max="5000";number.value=String(item.count);
      number.title="Edit repeats directly";number.setAttribute("aria-label","Repeat count for "+item.motif);
      number.onclick=e=>e.stopPropagation();
      number.ondragstart=e=>e.stopPropagation();
      number.onchange=()=>{
        const count=Number(number.value);if(Number.isInteger(count)&&count>=1&&count<=5000){
          const copy=model.runs.map(r=>({...r}));copy[i].count=count;commit(copy);
        }else number.value=item.count;
      };
      controls.append(number);run.append(controls);
      const beads=elt("div","elp-beads");
      const b=elt("span","elp-bead");
      b.style.backgroundColor=motifs[item.motif]?.color||"#9CA3AF";
      b.title=item.motif+" ("+motifs[item.motif]?.sequence+")";
      beads.append(b);
      run.append(beads,elt("div","elp-bracket"),elt("span","elp-count","×"+item.count),
        elt("span","elp-runname",motifs[item.motif]?.label||item.motif));
      lane.append(run);gap(i+1);
      // The left and right edges of a block act as reorder drop zones.
      run.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect="move";};
      run.ondrop=e=>{
        e.preventDefault();e.stopPropagation();
        const raw=e.dataTransfer.getData("application/x-elp-run");
        if(raw==="")return;
        const rect=run.getBoundingClientRect();
        move(Number(raw),i+(e.clientX>rect.left+rect.width/2?1:0));
      };
    });
    const aa=model.runs.reduce((sum,r)=>sum+(motifs[r.motif]?.sequence.length||0)*r.count,0);
    const total=model.runs.reduce((sum,r)=>sum+r.count,0);
    const footer=elt("div","elp-bottom");
    footer.append(elt("span","",total+" motifs · "+aa+" amino acids · "+model.runs.length+" blocks"),
      elt("span","","Hover a block: +1 · −1 · split · delete · edit count"));
    root.append(footer);
  }
  draw();
}
"""


def motif_canvas(*, groups: list[dict], motifs: dict, revision: int):
    component = st.components.v2.component(
        name="elp_motif_canvas_v2",
        html='<div class="elp-motif-root"></div>',
        css=CSS,
        js=JS,
    )
    return component(
        key=f"elp_motif_canvas_{revision}",
        data={"groups": groups, "motifs": motifs, "revision": revision},
        default={"groups": groups},
        on_groups_change=lambda: None,
    )
