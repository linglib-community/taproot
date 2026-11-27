// Appended to a copy of the page by test_map.sh: walks the views, performs the gestures, and
// writes what happened into the page title, where --dump-dom can read it.
(function(){
  const fire=(el,t)=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));
  const q=s=>document.querySelectorAll(s).length, log=[], bad=[];
  const ok=(name,cond,detail)=>{log.push((cond?'ok   ':'FAIL ')+name+(detail?' ('+detail+')':''));if(!cond)bad.push(name)};
  window.onerror=m=>{bad.push('error');log.push('FAIL script error: '+m)};
  const go=(hash,ms)=>new Promise(r=>{location.hash=hash;setTimeout(r,ms)});
  (async()=>{
    await go('',2500);
    ok('top map draws',q('#gmap .dot')>20,q('#gmap .dot')+' dots, '+q('#gmap .il')+' islands');
    ok('review priority is the default mode',/review priority/.test((document.querySelector('.lens a.on')||{}).textContent||''));
    const d=document.querySelector('#gmap .dot[data-open^="#m/"]:not([data-uses="0"])');
    d.onmouseenter();ok('point previews',q('#hov path')>0&&q('.pl.tmp')===1);ok('arrows show only what the dot uses',q('#hov path')===+d.dataset.uses,q('#hov path')+' of '+d.dataset.uses);d.onmouseleave();
    const hot=[...document.querySelectorAll('#gmap .dot')].find(e=>/review priority (?:[1-9]|0\.[1-9])/.test(e.dataset.full));
    hot.onmouseenter();ok('the preview says why',/%|no theorems/.test(document.querySelector('.pl.tmp').textContent),document.querySelector('.pl.tmp').textContent);hot.onmouseleave();d.onmouseenter();d.onmouseleave();ok('moving away clears',q('#hov path')===0);
    fire(d,'click');d.onmouseleave();ok('click holds',q('#hov path')>0);fire(document.querySelector('#gmap'),'click');ok('click elsewhere releases',q('#hov path')===0);
    const want=d.dataset.open;fire(d,'click');fire(d,'click');fire(d,'dblclick');await go(location.hash,1500);
    ok('double-click zooms in',location.hash===want,location.hash);ok('zoomed map draws',q('#gmap .dot')>0,q('#gmap .dot')+' dots');
    const fd=document.querySelector('#gmap .dot.fl0');if(fd){fire(fd,'click');const a=document.querySelector('#gmap .pl a.src');ok('a held file on the map links to its source',!!a&&/\/blob\/[0-9a-f]{7,40}\/(Linglib|Studies)\/.+\.lean$/.test(a.href),a&&a.href);fire(document.querySelector('#gmap'),'click');ok('releasing removes the link',q('#gmap .pl a.src')===0)}
    const f=window.TAPROOT_TEST_FILE;
    await go('f/'+f,1500);
    ok('descent draws',q('#tend .dot.td')>3,q('#tend .dot.td')+' dots, '+q('#tend path.tw')+' into mathlib');
    const sa=document.querySelector('.tside .fnr a.src'),want2='https://github.com/'+META.repo+'/blob/'+(META.sha||'main')+'/Linglib/'+f.replace(/\./g,'/')+'.lean';
    ok('the file view links to its source at the measured commit',!!sa&&sa.href===want2&&sa.target==='_blank',sa&&sa.href);
    ok('an editor link only where a checkout and an editor are known',q('.tside .fnr a.src')===(META.ed&&META.local?2:1),(META.ed||'no editor')+' '+(META.local||''));
    let opened='';const wo=window.open;window.open=u=>{opened=u};dispatchEvent(new KeyboardEvent('keydown',{key:'s'}));window.open=wo;ok('s opens the source of the file in view',opened===want2,opened);
    ok('side-panel rows link to their source',q('.tside .row').length===0||q('.tside .row a.src')===q('.tside .row'),q('.tside .row a.src')+' rows');
    const c=document.querySelector('#tend .dot.td.car')||document.querySelector('#tend .dot.td.named')||document.querySelector('#tend .dot.td');
    fire(c,'click');ok('holding in the descent lights a route',q('#tend .dot.td.lit')>0);fire(document.querySelector('#tend'),'click');
    await go('f/'+f+'?up=1',1500);
    ok('upward view draws',q('#tend .dot.td')>=1,q('#tend .dot.td')+' dots');ok('the upward view links to its source',q('.tside .fnr a.src')>=1);
    await go('m/Languages',2500);ok('a level with many directories draws',q('#gmap .dot')>50,q('#gmap .dot')+' dots');
    document.title='RESULT '+(bad.length?'FAILED':'PASSED')+' | '+log.join(' | ');
  })();
})();
