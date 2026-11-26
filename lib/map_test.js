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
    const d=document.querySelector('#gmap .dot[data-open^="#m/"]');
    d.onmouseenter();ok('point previews',q('#hov path')>0&&q('.pl.tmp')===1);d.onmouseleave();ok('moving away clears',q('#hov path')===0);
    fire(d,'click');d.onmouseleave();ok('click holds',q('#hov path')>0);fire(document.querySelector('#gmap'),'click');ok('click elsewhere releases',q('#hov path')===0);
    const want=d.dataset.open;fire(d,'click');fire(d,'click');fire(d,'dblclick');await go(location.hash,1500);
    ok('double-click zooms in',location.hash===want,location.hash);ok('zoomed map draws',q('#gmap .dot')>0,q('#gmap .dot')+' dots');
    const f=window.TAPROOT_TEST_FILE;
    await go('f/'+f,1500);
    ok('descent draws',q('#tend .dot.td')>3,q('#tend .dot.td')+' dots, '+q('#tend path.tw')+' into mathlib');
    const c=document.querySelector('#tend .dot.td.car')||document.querySelector('#tend .dot.td.named')||document.querySelector('#tend .dot.td');
    fire(c,'click');ok('holding in the descent lights a route',q('#tend .dot.td.lit')>0);fire(document.querySelector('#tend'),'click');
    await go('f/'+f+'?up=1',1500);
    ok('upward view draws',q('#tend .dot.td')>=1,q('#tend .dot.td')+' dots');
    await go('m/Languages',2500);ok('a level with many directories draws',q('#gmap .dot')>50,q('#gmap .dot')+' dots');
    document.title='RESULT '+(bad.length?'FAILED':'PASSED')+' | '+log.join(' | ');
  })();
})();
