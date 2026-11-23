'use strict';
(()=>{

const ticket=document.querySelector('#ticket'),flip=document.querySelector('#flip-btn'),indicator=document.querySelector('#indicator');let busy=false;
const scene=document.querySelector('#mail-scene'),layer=document.querySelector('#draw-layer'),paper=document.querySelector('#sleeve-front'),paperBack=document.querySelector('#sleeve-back'),controls=document.querySelector('#controls');
let revealed=false,extracting=false,settling=false,gesture=null,pull=0;
const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
function setPull(value,dx=0){pull=Math.min(155,Math.max(0,value));const tilt=Math.max(-5,Math.min(5,dx*.035));layer.style.transform=`translateY(${96-pull*1.3}px) rotateZ(${-3+tilt}deg) scale(${.92+pull/3100})`;paper.style.transform=`translateZ(12px) translateY(${pull*.9}px) rotateZ(${1+pull*.012}deg)`;paperBack.style.transform=`translateZ(-12px) translateY(${pull*.45}px) rotateZ(${1-pull*.007}deg)`}
async function extract(){
 if(revealed||extracting||settling)return;extracting=true;gesture=null;scene.classList.remove('dragging');paper.style.pointerEvents='none';ticket.setAttribute('aria-busy','true');
 const duration=reduced()?1:1380;
 const cardAnimation=layer.animate([{transform:getComputedStyle(layer).transform,offset:0},{transform:'translateY(-125px) rotateZ(-6deg) scale(1.015)',offset:.49},{transform:'translateY(-12px) rotateZ(2deg) scale(1.025)',offset:.84},{transform:'translateY(0) rotateZ(0) scale(1)',offset:1}],{duration,easing:'cubic-bezier(.3,0,.18,1)',fill:'forwards'});
 const paperAnimation=paper.animate([{transform:getComputedStyle(paper).transform,opacity:1},{transform:'translateZ(12px) translateY(315px) rotateZ(7deg)',opacity:1,offset:.6},{transform:'translateZ(12px) translateY(370px) rotateZ(9deg)',opacity:0}],{duration:duration*.88,easing:'cubic-bezier(.3,0,.18,1)',fill:'forwards'});
 const backAnimation=paperBack.animate([{transform:getComputedStyle(paperBack).transform,opacity:1},{transform:'translateZ(-12px) translateY(300px) rotateZ(-4deg)',opacity:0}],{duration:duration*.88,easing:'cubic-bezier(.3,0,.18,1)',fill:'forwards'});
 await Promise.all([cardAnimation.finished,paperAnimation.finished,backAnimation.finished]);
 layer.style.transform='translateY(0) rotateZ(0) scale(1)';paper.hidden=true;paperBack.hidden=true;[cardAnimation,paperAnimation,backAnimation].forEach(a=>a.cancel());revealed=true;extracting=false;pull=0;scene.classList.add('revealed');ticket.removeAttribute('aria-busy');ticket.setAttribute('aria-label','초대장 뒷면 보기');paper.setAttribute('tabindex','-1');controls.hidden=false;document.querySelector('#claim-box').hidden=false;
}
async function resetPull(){settling=true;
 const animations=[layer.animate([{transform:getComputedStyle(layer).transform},{transform:'translateY(96px) rotateZ(-3deg) scale(.92)'}],{duration:reduced()?1:320,easing:'cubic-bezier(.18,.8,.25,1)',fill:'forwards'}),paper.animate([{transform:getComputedStyle(paper).transform},{transform:'translateZ(12px) rotateZ(1deg)'}],{duration:reduced()?1:320,fill:'forwards'}),paperBack.animate([{transform:getComputedStyle(paperBack).transform},{transform:'translateZ(-12px) rotateZ(1deg)'}],{duration:reduced()?1:320,fill:'forwards'})];
 await Promise.all(animations.map(a=>a.finished));layer.style.transform='';paper.style.transform='';paperBack.style.transform='';animations.forEach(a=>a.cancel());pull=0;settling=false;
}
scene.addEventListener('pointerdown',e=>{if(revealed||extracting||settling||gesture||e.button!==0)return;gesture={id:e.pointerId,x:e.clientX,y:e.clientY,moved:false};scene.setPointerCapture(e.pointerId);scene.classList.add('dragging')});
scene.addEventListener('pointermove',e=>{if(!gesture||e.pointerId!==gesture.id||extracting)return;const dy=gesture.y-e.clientY,dx=e.clientX-gesture.x;gesture.moved=gesture.moved||Math.abs(dy)>6||Math.abs(dx)>6;setPull(dy,dx)});
scene.addEventListener('pointerup',e=>{if(!gesture||e.pointerId!==gesture.id)return;const moved=gesture.moved;gesture=null;scene.classList.remove('dragging');if(scene.hasPointerCapture(e.pointerId))scene.releasePointerCapture(e.pointerId);if(pull>=55||!moved)extract();else resetPull()});
scene.addEventListener('pointercancel',()=>{if(!gesture)return;gesture=null;scene.classList.remove('dragging');resetPull()});
paper.addEventListener('click',e=>{if(e.detail===0&&!gesture)extract()});
paper.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();extract()}});
function resetMail(){
 if(extracting||busy)return;revealed=false;controls.hidden=true;document.querySelector('#claim-box').hidden=true;scene.classList.remove('revealed');ticket.classList.remove('flipped','turn-back','turn-front');ticket.setAttribute('aria-pressed','false');ticket.setAttribute('aria-label','초대장 꺼내기');document.querySelector('.front').setAttribute('aria-hidden','false');document.querySelector('.back').setAttribute('aria-hidden','true');indicator.textContent='앞면';flip.textContent='초대 편지 읽기';paper.hidden=false;paperBack.hidden=false;paper.style.pointerEvents='';paper.setAttribute('tabindex','0');layer.style.transform='';paper.style.transform='';paperBack.style.transform='';pull=0;
}
document.querySelector('#again').addEventListener('click',resetMail);
ticket.setAttribute('aria-label','초대장 꺼내기');

function finish(){ticket.classList.remove('turn-back','turn-front');busy=false;flip.disabled=false}
function turn(){if(!revealed||busy)return;busy=true;flip.disabled=true;const back=!ticket.classList.contains('flipped');ticket.classList.toggle('flipped',back);ticket.classList.remove('turn-back','turn-front');void ticket.offsetWidth;ticket.classList.add(back?'turn-back':'turn-front');ticket.setAttribute('aria-pressed',String(back));ticket.setAttribute('aria-label',back?'초대장 앞면 보기':'초대장 뒷면 보기');document.querySelector('.front').setAttribute('aria-hidden',String(back));document.querySelector('.back').setAttribute('aria-hidden',String(!back));flip.textContent=back?'금색 티켓 앞면 보기':'초대 편지 읽기';indicator.textContent=back?'뒷면':'앞면';if(matchMedia('(prefers-reduced-motion: reduce)').matches)finish();else setTimeout(finish,1220)}
ticket.addEventListener('click',turn);flip.addEventListener('click',turn);ticket.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();if(revealed)turn();else extract()}});

window.showInvitation=function(data){
 document.querySelector('#recipient-name').textContent=data.name||'';
 document.querySelector('#ticket-no').textContent=data.invite_code.replace('INJ-','').slice(-8);
 document.querySelector('#invite-code').textContent=data.invite_code;
 document.querySelector('#ticket-mascot').src='/api/invite-art?code='+encodeURIComponent(data.invite_code);
 document.querySelector('#invite-status').textContent=data.checked?'이미 현장 확인이 완료된 초대장입니다.':'행사 당일, 운영진에게 이 초대장을 보여 주세요.';
 resetMail();visible('done');
};

})();
