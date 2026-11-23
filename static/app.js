'use strict';
const $ = id => document.getElementById(id);
const state = {name:'',last2:'',questions:[],answers:[],index:0,busy:false};
const typeNames = {proverb:'01 · 그림 속담',ticket:'02 · 주인의 서재',chocolate:'03 · 마지막 봉인'};
let flipBusy=false;
const hasAnswer=a=>typeof a==='string'?a.trim().length>0:a!==null&&a!==undefined;
function visible(id){
  document.querySelectorAll('.step').forEach(el=>el.classList.add('hidden'));
  $(id).classList.remove('hidden');window.scrollTo({top:0,behavior:'instant'});
}
async function post(path,payload){
  let r;try{r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});}
  catch{throw new Error('서버와 연결할 수 없어요. Wi-Fi를 확인해 주세요.');}
  let d;try{d=await r.json();}catch{throw new Error('서버 응답을 확인할 수 없어요.');}
  if(!r.ok)throw new Error(d.error||'요청 중 문제가 발생했어요.');return d;
}
$('entry-form').addEventListener('submit',async e=>{
  e.preventDefault();if(state.busy)return;
  const name=$('participant-name').value.trim(),last2=$('last2').value.trim();
  $('entry-error').textContent='';
  if(!/^[가-힣A-Za-z .-]{2,30}$/.test(name)||!/^[0-9]{2}$/.test(last2)){
    $('entry-error').textContent='이름과 학번 끝 두 자리(숫자)를 확인해 주세요.';return;
  }
  state.busy=true;$('start-btn').disabled=true;
  try{
    const data=await post('/api/start',{name,last2});state.name=name;state.last2=last2;
    if(data.status==='completed'){showInvitation(data,false);return;}
    state.questions=data.questions;state.answers=Array(data.questions.length).fill(null);state.index=0;
    renderQuestion();visible('quiz');
  }catch(err){$('entry-error').textContent=err.message;}
  finally{state.busy=false;$('start-btn').disabled=false;if(!$('quiz').classList.contains('hidden'))renderQuestion();}
});
function renderQuestion(){
  const n=state.index,q=state.questions[n];if(!q)return;
  $('quiz-count').textContent=`${String(n+1).padStart(2,'0')} / ${String(state.questions.length).padStart(2,'0')}`;
  $('progress-fill').style.width=`${(n/state.questions.length)*100}%`;
  $('quiz-type').textContent=typeNames[q.group]||'그림 퀴즈';
  $('quiz-prompt').textContent=q.question;$('quiz-error').textContent='';
  $('text-answer-wrap').classList.toggle('hidden',q.kind!=='text');
  $('text-answer').value=typeof state.answers[n]==='string'?state.answers[n]:'';
  $('prev-btn').disabled=n===0||state.busy;
  if(q.image){$('quiz-image').src='/assets/'+encodeURIComponent(q.image);$('quiz-image-wrap').classList.remove('hidden');}
  else{$('quiz-image').removeAttribute('src');$('quiz-image-wrap').classList.add('hidden');}
  const el=$('quiz-options');el.replaceChildren();
  const pictures=Array.isArray(q.option_images)&&q.option_images.length===q.options.length;
  el.className=pictures?'answers picture-answers':'answers';
  q.options.forEach((label,i)=>{
    const btn=document.createElement('button');btn.type='button';btn.className='answer'+(state.answers[n]===i?' selected':'');
    btn.setAttribute('aria-pressed',String(state.answers[n]===i));
    if(pictures){const img=document.createElement('img');img.className='answer-picture';img.src='/assets/'+encodeURIComponent(q.option_images[i]);img.alt='';btn.append(img);}
    const num=document.createElement('span');num.className='answer-num';num.textContent=String(i+1).padStart(2,'0');
    const txt=document.createElement('span');txt.className='answer-label';txt.textContent=label;btn.append(num,txt);
    btn.addEventListener('click',()=>{state.answers[n]=i;renderQuestion();});el.append(btn);
  });
  $('next-btn').disabled=!hasAnswer(state.answers[n])||state.busy;
  $('next-btn').textContent=n===state.questions.length-1?'정답 확인하고 초대장 받기':'다음 문제';
}
$('next-btn').addEventListener('click',async()=>{
  if(state.busy||!hasAnswer(state.answers[state.index]))return;
  if(state.index<state.questions.length-1){state.index++;renderQuestion();return;}
  state.busy=true;renderQuestion();
  let message='';
  try{
    const data=await post('/api/quiz',{name:state.name,last2:state.last2,answers:state.answers});
    if(data.status==='retry'){
      state.index=data.missed?.[0]??0;(data.missed||[]).forEach(i=>state.answers[i]=null);
      renderQuestion();message=data.error||'아쉬워요! 다시 도전해 보세요.';return;
    }
    if(data.status==='completed')showInvitation(data,true);
  }catch(err){message=err.message;}
  finally{state.busy=false;if(!$('quiz').classList.contains('hidden')){renderQuestion();$('quiz-error').textContent=message;}}
});
$('text-answer').addEventListener('input',()=>{state.answers[state.index]=$('text-answer').value;$('next-btn').disabled=!hasAnswer(state.answers[state.index])||state.busy;});
$('text-answer').addEventListener('keydown',e=>{if(e.key==='Enter'&&hasAnswer(state.answers[state.index]))$('next-btn').click();});
$('prev-btn').addEventListener('click',()=>{if(state.index>0&&!state.busy){state.index--;renderQuestion();}});
$('copy-btn').addEventListener('click',async()=>{
  const content=$('invite-code').textContent;
  try{await navigator.clipboard.writeText(content);$('copy-btn').textContent='복사했어요 ✓';}
  catch{$('copy-btn').textContent='번호를 길게 눌러 복사해 주세요';}
});
$('print-btn').addEventListener('click',()=>window.print());
