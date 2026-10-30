"""Draggable ELP architecture canvas with repeatable manual motif groups.

Single-motif runs remain compact. Multiple selected adjacent runs can be
grouped into a repeatable ordered architecture block. Dragging, hover editing
and exact sequence generation use the same serialized model.
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
.elp-run:hover .elp-tools,.elp-run:focus-within .elp-tools,.elp-run.toolbar-open .elp-tools{display:flex}
.elp-tool{min-width:26px;height:25px;padding:0 5px;border:1px solid transparent;border-radius:6px;color:var(--st-text-color);background:transparent;font-size:12px;cursor:pointer}
.elp-tool:hover,.elp-tool:focus-visible{background:var(--st-secondary-background-color,#eee);border-color:var(--st-border-color,#ccd3dc)}
.elp-tool:disabled{opacity:.35;cursor:not-allowed}
.elp-num{width:47px;height:26px;border:1px solid var(--st-border-color,#ccd3dc);border-radius:6px;background:var(--st-background-color,#fff);color:var(--st-text-color);font:inherit;font-size:12px;text-align:center}
.elp-bottom{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px;font-size:12px;opacity:.8;flex-wrap:wrap}
.elp-empty{font-size:13px;opacity:.7;padding:10px}


.elp-run.selected{border:2px solid var(--st-primary-color,#f43f5e);background:var(--st-secondary-background-color,#edf3fa)}
.elp-group{border:1.5px solid var(--st-primary-color,#9c8beb);background:var(--st-secondary-background-color,#f5f0fa);padding:9px 12px 12px;min-width:74px}
.elp-group .elp-beads{gap:5px}
.elp-group .elp-bracket{width:calc(100% - 5px)}
.elp-unit{display:flex;flex-direction:column;align-items:center;gap:2px}
.elp-unitcount{font-size:9px;opacity:.7}
.elp-group-title{font-size:10px;font-weight:600;opacity:.8;margin-top:2px}
.elp-selection{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
.elp-selection button{border:1px solid var(--st-border-color,#bbc6d1);border-radius:9px;padding:7px 11px;background:var(--st-background-color,#fff);color:var(--st-text-color);cursor:pointer;font-size:12px}
.elp-selection button.primary{background:var(--st-primary-color,#b89ecf);color:white;border-color:transparent}
.elp-selection button:disabled{opacity:.4;cursor:not-allowed}
"""


JS = r"""
export default function(component) {
  const {parentElement,data,setStateValue}=component;
  const host=parentElement.querySelector(".elp-motif-root");
  if(!host)return;
  const motifs=data?.motifs||{},revision=data?.revision??0;
  const initial=Array.isArray(data?.groups)?data.groups:[];
  const clean=(block)=>({
    segments:(block.segments||[]).map(s=>({motif:s.motif,count:s.count})),
    repeat:block.repeat||1,
    manual:!!block.manual||(block.segments||[]).length>1,
    split_before:!!block.split_before
  });
  if(!host.__model||host.__model.revision!==revision){
    host.__model={blocks:initial.map(clean),selected:new Set(),toolbarIndex:null,revision};
  }
  const model=host.__model;
  const elt=(tag,cls,label)=>{
    const n=document.createElement(tag);if(cls)n.className=cls;
    if(label!==undefined)n.textContent=label;return n;
  };
  const known=(name)=>Object.prototype.hasOwnProperty.call(motifs,name);
  const copy=()=>model.blocks.map(b=>({...b,segments:b.segments.map(s=>({...s}))}));
  function normalize(blocks){
    const out=[];
    for(const b of blocks){
      if(!b.segments||!b.segments.length)continue;
      const manual=!!b.manual||b.segments.length>1;
      const repeat=Number(b.repeat||1);
      const segments=b.segments.map(s=>({...s}));
      const block={segments,repeat,manual,split_before:!!b.split_before};
      const previous=out[out.length-1];
      if(!manual&&repeat===1&&previous&&!previous.manual&&previous.repeat===1&&
         previous.segments[0].motif===segments[0].motif&&!block.split_before&&
         previous.segments[0].count+segments[0].count<=5000){
        previous.segments[0].count+=segments[0].count;
      }else out.push(block);
    }
    return out;
  }
  function valid(blocks){
    if(blocks.length>2000)return false;
    let total=0;
    for(const block of blocks){
      if(!Number.isInteger(block.repeat)||block.repeat<1||block.repeat>5000||
         !Array.isArray(block.segments)||!block.segments.length)return false;
      for(const seg of block.segments){
        if(!known(seg.motif)||!Number.isInteger(seg.count)||seg.count<1||seg.count>5000)return false;
        total+=(motifs[seg.motif].sequence||"").length*seg.count*block.repeat;
        if(total>50000)return false;
      }
    }
    return true;
  }
  function commit(blocks){
    const norm=normalize(blocks);
    if(!valid(norm)){window.alert("Maximum: 50,000 amino acids, 2,000 blocks or 5,000 repetitions per block.");return;}
    model.blocks=norm;model.selected.clear();
    // Keep the control panel expanded after +1/-1, repeat edits and split.
    // It closes only when the pointer leaves the block and its popup.
    if(model.toolbarIndex!==null && model.toolbarIndex>=norm.length)model.toolbarIndex=null;
    setStateValue("groups",norm.map(b=>{
      const record={segments:b.segments.map(s=>({...s}))};
      if(b.manual){record.manual=true;record.repeat=b.repeat;}
      if(b.split_before)record.split_before=true;
      return record;
    }));
    draw();
  }
  function add(name){if(known(name))commit([...copy(),{segments:[{motif:name,count:1}],repeat:1,manual:false}]);}
  function move(source,target){
    if(!Number.isInteger(source)||source<0||source>=model.blocks.length)return;
    model.toolbarIndex=null;
    const blocks=copy(),[item]=blocks.splice(source,1);
    const dest=Math.max(0,Math.min(blocks.length,source<target?target-1:target));
    blocks.splice(dest,0,item);commit(blocks);
  }
  function groupSelection(){
    const indices=[...model.selected].sort((a,b)=>a-b);
    if(indices.length<2||indices.some((v,i)=>i&&v!==indices[0]+i))return;
    const start=indices[0],stop=indices[indices.length-1],blocks=copy(),parts=[];
    for(const block of blocks.slice(start,stop+1)){
      for(let r=0;r<block.repeat;r++){
        for(const seg of block.segments){
          const prev=parts[parts.length-1];
          if(prev&&prev.motif===seg.motif&&prev.count+seg.count<=5000)prev.count+=seg.count;
          else parts.push({...seg});
        }
      }
    }
    blocks.splice(start,stop-start+1,{segments:parts,repeat:1,manual:true});
    commit(blocks);
  }
  function updateCount(i,delta){
    const blocks=copy(),b=blocks[i];if(!b)return;
    if(b.manual){
      const next=b.repeat+delta;
      if(next===0)blocks.splice(i,1);
      else if(next>=1&&next<=5000)b.repeat=next;
      else return;
    }else{
      const next=b.segments[0].count+delta;
      if(next===0)blocks.splice(i,1);
      else if(next>=1&&next<=5000)b.segments[0].count=next;
      else return;
    }
    commit(blocks);
  }
  function ungroup(i){
    const blocks=copy(),b=blocks[i];if(!b||!b.manual)return;
    const expanded=[];
    // Converting the group to its motif runs preserves the exact sequence.
    for(let r=0;r<b.repeat;r++)
      for(const s of b.segments)expanded.push({segments:[{...s}],repeat:1,manual:false,split_before:true});
    blocks.splice(i,1,...expanded);commit(blocks);
  }
  function split(i){
    const blocks=copy(),b=blocks[i];if(!b)return;
    if(b.manual){
      if(b.repeat>1){
        const a=Math.floor(b.repeat/2),rest=b.repeat-a;
        blocks.splice(i,1,{...b,repeat:a},{...b,repeat:rest});
        commit(blocks);
      }else{
        ungroup(i);
      }
    }else if(b.segments[0].count>1){
      const a=Math.floor(b.segments[0].count/2),rest=b.segments[0].count-a;
      blocks.splice(i,1,
        {segments:[{motif:b.segments[0].motif,count:a}],repeat:1,manual:false},
        {segments:[{motif:b.segments[0].motif,count:rest}],repeat:1,manual:false,split_before:true});
      commit(blocks);
    }
  }
  function tool(label,title,handler,disabled=false){
    const b=elt("button","elp-tool",label);b.type="button";b.title=title;
    b.setAttribute("aria-label",title);b.disabled=disabled;
    b.onclick=e=>{e.stopPropagation();if(!disabled)handler();};
    b.ondragstart=e=>e.preventDefault();return b;
  }
  function draw(){
    host.replaceChildren();
    const root=elt("div","elp-board");host.append(root);
    root.onpointerleave=()=>{model.toolbarIndex=null;};
    const head=elt("div","elp-header");
    head.append(elt("span","elp-title","ELP motif architecture"),
      elt("span","elp-hint","Click / Shift-click blocks to select · drag to reorder"));
    root.append(head);
    const palette=elt("div","elp-palette");root.append(palette);
    for(const [name,m] of Object.entries(motifs)){
      const button=elt("button","elp-add");button.type="button";
      const ball=elt("span","elp-dot");ball.style.backgroundColor=m.color||"#9CA3AF";
      button.append(ball,elt("span","",(m.label||name)+" +"));
      button.title="Add "+name+" ("+m.sequence+")";button.onclick=()=>add(name);palette.append(button);
    }
    const selection=elt("div","elp-selection");root.append(selection);
    const indices=[...model.selected].sort((a,b)=>a-b);
    const consecutive=indices.length>=2 && indices.every((v,i)=>v===indices[0]+i);
    const group=elt("button",consecutive?"primary":"","Group selected ("+indices.length+")");
    group.type="button";group.disabled=!consecutive;group.title="Group two or more adjacent blocks into one repeatable unit";
    group.onclick=groupSelection;selection.append(group);
    const clear=elt("button","","Clear selection");clear.type="button";clear.disabled=!indices.length;
    clear.onclick=()=>{model.selected.clear();draw();};selection.append(clear);
    selection.append(elt("span","elp-hint",indices.length
      ?(consecutive?"Ready to group selected blocks":"Select adjacent blocks to group")
      :"Click blocks to select; Shift-click to add more"));
    const lane=elt("div","elp-lane");root.append(lane);
    if(!model.blocks.length)lane.append(elt("div","elp-empty","Add motifs from the palette to begin."));
    const gap=(index)=>{
      const n=elt("div","elp-gap");n.title="Drop block here";
      n.ondragover=e=>{e.preventDefault();n.classList.add("over");};
      n.ondragleave=()=>n.classList.remove("over");
      n.ondrop=e=>{e.preventDefault();e.stopPropagation();n.classList.remove("over");
        const raw=e.dataTransfer.getData("application/x-elp-run");if(raw!=="")move(Number(raw),index);
      };lane.append(n);
    };
    gap(0);
    model.blocks.forEach((b,i)=>{
      const manual=b.manual,repeat=manual?b.repeat:b.segments[0].count;
      const run=elt("div","elp-run"+(manual?" elp-group":"")+(model.selected.has(i)?" selected":"")+(model.toolbarIndex===i?" toolbar-open":""));
      run.tabIndex=0;run.draggable=true;
      run.onpointerenter=()=>{model.toolbarIndex=i;};
      run.onpointerleave=()=>{
        if(model.toolbarIndex===i)model.toolbarIndex=null;
        run.classList.remove("toolbar-open");
      };
      run.title=manual?"Drag this repeatable motif group":"Drag this motif block";
      run.onclick=e=>{
        if(e.shiftKey||e.ctrlKey||e.metaKey){
          if(model.selected.has(i))model.selected.delete(i);else model.selected.add(i);
        }else if(model.selected.has(i)){model.selected.delete(i);}
        else{model.selected.clear();model.selected.add(i);}
        draw();
      };
      run.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();if(model.selected.has(i))model.selected.delete(i);else model.selected.add(i);draw();}};
      run.ondragstart=e=>{model.toolbarIndex=null;e.dataTransfer.setData("application/x-elp-run",String(i));e.dataTransfer.effectAllowed="move";run.classList.add("dragging");};
      run.ondragend=()=>run.classList.remove("dragging");
      const tools=elt("div","elp-tools");
      tools.onpointerenter=()=>{model.toolbarIndex=i;};
      tools.append(
        tool("+1",manual?"Add one complete group":"Add one motif",()=>updateCount(i,1),repeat>=5000),
        tool("−1",manual?"Remove one complete group":"Remove one motif",()=>updateCount(i,-1)),
        tool("⫽",manual?"Split group repetitions or ungroup motifs":"Split motif block",()=>split(i),!manual&&repeat<2),
        tool("×",manual?"Delete entire group":"Delete motif block",()=>{model.toolbarIndex=null;const blocks=copy();blocks.splice(i,1);commit(blocks);})
      );
      const number=elt("input","elp-num");number.type="number";number.min="1";number.max="5000";number.value=String(repeat);
      number.title=manual?"Complete-group repetitions":"Motif repetitions";
      number.onclick=e=>e.stopPropagation();
      number.onfocus=()=>{model.toolbarIndex=i;};
      number.ondragstart=e=>e.stopPropagation();
      number.onchange=()=>{
        const next=Number(number.value);
        if(Number.isInteger(next)&&next>=1&&next<=5000)updateCount(i,next-repeat);
        else number.value=String(repeat);
      };
      tools.append(number);
      if(manual)tools.append(tool("Ungroup","Expand back into individual motif blocks",()=>ungroup(i)));
      run.append(tools);
      const beads=elt("div","elp-beads");
      for(const seg of b.segments){
        const unit=elt("div","elp-unit"),ball=elt("span","elp-bead");
        ball.style.backgroundColor=motifs[seg.motif]?.color||"#9CA3AF";
        ball.title=seg.motif+" ×"+seg.count+" ("+motifs[seg.motif]?.sequence+")";
        unit.append(ball,elt("span","elp-unitcount","×"+seg.count));beads.append(unit);
      }
      run.append(beads,elt("div","elp-bracket"),
        elt("span","elp-count","×"+repeat),
        elt("span",manual?"elp-group-title":"elp-runname",
          manual?"Manual group":(motifs[b.segments[0].motif]?.label||b.segments[0].motif)));
      lane.append(run);gap(i+1);
      run.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect="move";};
      run.ondrop=e=>{
        e.preventDefault();e.stopPropagation();const raw=e.dataTransfer.getData("application/x-elp-run");
        if(raw==="")return;const rect=run.getBoundingClientRect();
        move(Number(raw),i+(e.clientX>rect.left+rect.width/2?1:0));
      };
    });
    const aa=model.blocks.reduce((v,b)=>v+b.repeat*b.segments.reduce((a,s)=>a+(motifs[s.motif]?.sequence.length||0)*s.count,0),0);
    const n=model.blocks.reduce((v,b)=>v+b.repeat*b.segments.reduce((a,s)=>a+s.count,0),0);
    const foot=elt("div","elp-bottom");
    foot.append(elt("span","",n+" motifs · "+aa+" amino acids · "+model.blocks.length+" blocks"),
      elt("span","","Manual groups repeat their entire ordered motif pattern"));
    root.append(foot);
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
