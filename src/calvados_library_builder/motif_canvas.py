"""Native Streamlit v2 drag-and-drop editor for colored motif groups.

Every group is draggable; dropping onto another group joins their segments,
while dropping between groups moves the group. The output is round-tripped to
the Python sequence model before FASTA generation and simulation.
"""
from __future__ import annotations

import streamlit as st

CSS = """
.canvas{font-family:var(--st-font,system-ui);color:var(--st-text-color);padding:16px;border:1px solid var(--st-border-color,#d1d5db);border-radius:14px;background:var(--st-secondary-background-color,#f8fafc)}
.canvas-head{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.canvas-title{font-weight:700;font-size:1rem}.hint{font-size:.79rem;opacity:.65}
.palette,.lane{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px}
.lane{padding:15px;min-height:80px;background:var(--st-background-color,#fff);border:1px dashed var(--st-border-color,#d1d5db);border-radius:12px}
.group{position:relative;display:flex;align-items:center;gap:2px;min-height:46px;padding:6px;border:2px solid transparent;border-radius:12px;cursor:grab;max-width:100%}
.group:hover{background:var(--st-secondary-background-color,#eee)}
.group.selected{border-color:var(--st-primary-color,#f43f5e);background:var(--st-secondary-background-color,#eee)}
.group.dragover{border-color:var(--st-primary-color,#f43f5e)}
.group:focus-visible,.ball:focus-visible{outline:2px solid var(--st-primary-color)}
.ball{width:32px;height:32px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;box-shadow:inset 0 -3px 5px #0002;border:1px solid #0002;font-size:10px;font-weight:750;color:#101828;cursor:inherit}
.overflow{font-size:11px;font-weight:650;opacity:.8;padding:0 4px}.group-label{font-size:11px;opacity:.75;max-width:180px;overflow-wrap:anywhere;margin-left:4px}
.dropgap{width:9px;min-height:40px;border-radius:8px;background:transparent}
.dropgap.over{background:var(--st-primary-color,#f43f5e)}
.palette-item{border:1px solid var(--st-border-color,#ddd);border-radius:20px;padding:5px 10px;display:inline-flex;gap:7px;align-items:center;background:var(--st-background-color,#fff);cursor:pointer;font:inherit;font-size:12px}
.palette-item .ball{width:16px;height:16px}
.palette-item:hover{border-color:var(--st-primary-color,#f43f5e)}
.inspector{display:flex;flex-wrap:wrap;align-items:end;gap:10px;margin-top:12px;padding:12px;border-radius:10px;background:var(--st-background-color,#fff);border:1px solid var(--st-border-color,#ddd)}
.inspector label{display:grid;gap:3px;font-size:12px;min-width:90px}
.inspector input,.inspector select{padding:7px;border:1px solid var(--st-border-color,#ccc);border-radius:7px;background:var(--st-background-color,#fff);color:var(--st-text-color);font:inherit}
.inspector input{width:90px}
.inspector button{padding:8px 10px;border-radius:8px;border:1px solid var(--st-border-color,#ccc);background:var(--st-secondary-background-color,#eee);color:var(--st-text-color);font:inherit;cursor:pointer;font-size:12px}
.summary{margin-top:10px;font-size:12px;opacity:.8}
"""

JS = """
export default function(component) {
  const {parentElement:root,data,setStateValue}=component;
  const host=root.querySelector(".elp-motif-root");
  if(!host)return;
  const initial=Array.isArray(data?.groups)?data.groups:[];
  const motifs=data?.motifs||{};
  const groupKey=data?.revision??0;
  if(!host.__elp || host.__elp.revision!==groupKey) {
    host.__elp={groups:structuredClone(initial),selected:-1,revision:groupKey};
  }
  const model=host.__elp;
  host.replaceChildren();
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const valid=()=>Array.isArray(model.groups)&&model.groups.length<=2000&&model.groups.every(g=>Array.isArray(g.segments));
  const commit=()=>{if(!valid())return;setStateValue("groups",structuredClone(model.groups));render();};
  const ball=(motif)=>{const b=el("span","ball");b.style.backgroundColor=motifs[motif]?.color||"#9CA3AF";b.title=motif+" ("+(motifs[motif]?.sequence||"")+")";return b;};
  const canvas=el("div","canvas");host.append(canvas);
  const head=el("div","canvas-head");head.append(el("div","canvas-title","Your ELP architecture"),el("div","hint","Drag a group to reorder • drop on a group to merge • click to edit"));canvas.append(head);
  const palette=el("div","palette");canvas.append(palette);
  const lane=el("div","lane");lane.setAttribute("aria-label","Drag-and-drop motif sequence");canvas.append(lane);
  const inspector=el("div","inspector");canvas.append(inspector);
  const summary=el("div","summary");canvas.append(summary);
  function add(name){model.groups.push({segments:[{motif:name,count:1}]});model.selected=model.groups.length-1;commit();}
  function actionButton(text,handler){const btn=el("button","",text);btn.type="button";btn.onclick=handler;return btn;}
  function dropInsert(target,source){
    if(source<0||source>=model.groups.length)return;
    const group=model.groups.splice(source,1)[0];
    const index=source<target?target-1:target;
    model.groups.splice(Math.max(0,index),0,group);model.selected=Math.max(0,index);commit();
  }
  function render(){
    palette.replaceChildren();lane.replaceChildren();inspector.replaceChildren();
    for(const name of Object.keys(motifs)){
      const chip=el("button","palette-item");chip.type="button";chip.append(ball(name),el("span","",name+" +"));chip.title="Add "+name+" to the end";chip.onclick=()=>add(name);palette.append(chip);
    }
    let dragIndex=null;
    const gap=(index)=>{
      const g=el("div","dropgap");g.title="Drop here to reorder";
      g.ondragover=e=>{e.preventDefault();g.classList.add("over");};
      g.ondragleave=()=>g.classList.remove("over");
      g.ondrop=e=>{e.preventDefault();g.classList.remove("over");const from=Number(e.dataTransfer.getData("text/plain"));if(Number.isInteger(from))dropInsert(index,from);};
      lane.append(g);
    };
    gap(0);
    model.groups.forEach((g,i)=>{
      const block=el("div","group"+(model.selected===i?" selected":""));block.draggable=true;block.tabIndex=0;
      block.title="Drag to change order; drop on a group to merge groups";
      block.ondragstart=e=>{dragIndex=i;e.dataTransfer.setData("text/plain",String(i));e.dataTransfer.effectAllowed="move";};
      block.ondragover=e=>{e.preventDefault();block.classList.add("dragover");};
      block.ondragleave=()=>block.classList.remove("dragover");
      block.ondrop=e=>{e.preventDefault();e.stopPropagation();block.classList.remove("dragover");const from=Number(e.dataTransfer.getData("text/plain"));if(Number.isInteger(from)&&from!==i&&model.groups[from]){const group=model.groups.splice(from,1)[0];const dest=from<i?i-1:i;model.groups[dest].segments.push(...group.segments);model.selected=dest;commit();}};
      block.onclick=()=>{model.selected=i;render();};
      block.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();model.selected=i;render();}};
      let shown=0;
      for(const seg of g.segments){
        for(let k=0;k<Math.min(seg.count,Math.max(0,60-shown));k++){block.append(ball(seg.motif));shown++;}
        if(seg.count>60-shown && shown>=60)break;
      }
      const total=g.segments.reduce((n,x)=>n+x.count,0);
      if(total>shown)block.append(el("span","overflow","+"+(total-shown)));
      block.append(el("span","group-label",g.segments.map(x=>x.motif+"×"+x.count).join(" + ")));
      lane.append(block);gap(i+1);
    });
    const n=model.groups.reduce((s,g)=>s+g.segments.reduce((v,x)=>v+(motifs[x.motif]?.sequence.length||0)*x.count,0),0);
    summary.textContent=model.groups.length+" groups · "+n+" amino acids · "+model.groups.reduce((s,g)=>s+g.segments.reduce((t,x)=>t+x.count,0),0)+" motifs";
    const index=model.selected;
    if(index<0||!model.groups[index]){
      inspector.append(el("span","hint","Click any group to edit its motif count, split it, or remove it."));return;
    }
    const group=model.groups[index];
    inspector.append(el("strong","", "Group "+(index+1)));
    if(group.segments.length===1){
      const segment=group.segments[0];
      const motifLabel=el("label","","Motif");const select=el("select");
      Object.keys(motifs).forEach(name=>{const option=el("option","",name);option.value=name;option.selected=name===segment.motif;select.append(option);});
      select.onchange=()=>{segment.motif=select.value;commit();};motifLabel.append(select);inspector.append(motifLabel);
      const countLabel=el("label","","Repeats");const input=el("input");input.type="number";input.min="1";input.max="5000";input.value=segment.count;
      input.onchange=()=>{const v=Number(input.value);if(Number.isInteger(v)&&v>=1&&v<=5000){segment.count=v;commit();}};
      countLabel.append(input);inspector.append(countLabel);
    } else {
      inspector.append(el("span","hint",group.segments.map(s=>s.motif+"×"+s.count).join(" + ")));
    }
    inspector.append(actionButton("← Left",()=>{if(index>0){[model.groups[index-1],model.groups[index]]=[model.groups[index],model.groups[index-1]];model.selected=index-1;commit();}}));
    inspector.append(actionButton("Right →",()=>{if(index<model.groups.length-1){[model.groups[index+1],model.groups[index]]=[model.groups[index],model.groups[index+1]];model.selected=index+1;commit();}}));
    inspector.append(actionButton("Ungroup",()=>{if(group.segments.length>1){model.groups.splice(index,1,...group.segments.map(s=>({segments:[{...s}]})));model.selected=index;commit();}else if(group.segments[0].count>1){const s=group.segments[0];const a=Math.floor(s.count/2);model.groups.splice(index,1,{segments:[{motif:s.motif,count:a}]},{segments:[{motif:s.motif,count:s.count-a}]});model.selected=index;commit();}}));
    inspector.append(actionButton("Delete",()=>{model.groups.splice(index,1);model.selected=-1;commit();}));
  }
  render();
}
"""


def motif_canvas(*, groups: list[dict], motifs: dict, revision: int):
    component = st.components.v2.component(
        name="elp_motif_canvas_v1",
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
