'use strict';
const $=id=>document.getElementById(id);
let csrf='',questionCache=[],loaded=false;
async function api(url,data=null,method='POST'){
  const init={method,credentials:'same-origin',headers:{...(method==='POST'?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF':csrf}:{})}};
  if(method==='POST')init.body=JSON.stringify(data||{});
  let r;try{r=await fetch(url,init);}catch{throw new Error('서버에 연결할 수 없습니다.');}
  let body;try{body=await r.json();}catch{throw new Error('응답을 읽지 못했습니다.');}
  if(!r.ok)throw new Error(body.error||'요청을 완료하지 못했습니다.');return body;
}
function loginScreen(message=''){$('admin-login').classList.remove('hidden');$('admin-main').classList.add('hidden');$('login-error').textContent=message;csrf='';loaded=false;}
async function refresh(){
  const d=await api('/api/admin/state',null,'GET');csrf=d.csrf;$('admin-login').classList.add('hidden');$('admin-main').classList.remove('hidden');
  ['joined','completed','checked'].forEach(key=>$(key+'-count').textContent=d.counts[key]);
  const list=$('recent-body');list.replaceChildren();
  for(const p of d.recent){const tr=document.createElement('tr');
    [p.name,p.last2,p.invite_code,p.completed_at?new Date(p.completed_at).toLocaleString('ko-KR'):'-',p.checked_at?'확인 완료':'미확인'].forEach(t=>{const td=document.createElement('td');td.textContent=t??'-';tr.append(td);});list.append(tr);
  }
  if(!d.recent.length){const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=5;td.textContent='아직 발급된 초대장이 없습니다.';tr.append(td);list.append(tr);}
  if(!loaded){await loadQuestions();loaded=true;}
}
$('login-form').addEventListener('submit',async event=>{event.preventDefault();$('login-error').textContent='';
  try{const d=await api('/api/admin/login',{password:$('password').value});csrf=d.csrf;await refresh();$('password').value='';}
  catch(e){$('login-error').textContent=e.message;}
});
$('logout-btn').addEventListener('click',async()=>{try{await api('/api/admin/logout',{});}finally{loginScreen();}});
$('refresh-btn').addEventListener('click',()=>refresh().catch(e=>$('global-error').textContent=e.message));

function participantCard(p){
  const card=document.createElement('div');card.className='participant-card';
  const time=p.joined_at?new Date(p.joined_at).toLocaleString('ko-KR'):'-';
  for(const [k,v] of [['이름',p.name],['학번 끝 두 자리',p.last2],['참여 시작',time],['초대장 번호',p.invite_code||'아직 발급되지 않았어요'],['현장 확인',p.checked_at?'확인 완료':p.completed_at?'미확인':'퀴즈 진행 중']]){
    const row=document.createElement('div'),label=document.createElement('strong');label.textContent=k+' : ';row.append(label,document.createTextNode(v||'-'));card.append(row);
  }
  if(p.completed_at&&!p.checked_at){
    const btn=document.createElement('button');btn.type='button';btn.className='redeem-button';btn.textContent='현장 확인 완료 처리';
    btn.addEventListener('click',async()=>{
      if(!confirm(p.name+' 님의 초대장을 현장에서 확인했나요?'))return;
      btn.disabled=true;
      try{await api('/api/admin/check',{invite_code:p.invite_code});await refresh();await searchParticipants();}
      catch(e){$('redeem-msg').textContent=e.message;btn.disabled=false;}
    });card.append(btn);
  }
  return card;
}
async function searchParticipants(){
  const query=$('search').value.trim(),box=$('search-result'),btn=$('search-btn');
  if(!query)return;
  $('redeem-msg').textContent='';btn.disabled=true;btn.textContent='찾는 중';box.setAttribute('aria-busy','true');
  try{
    const d=await api('/api/admin/search',{query});box.replaceChildren();box.classList.remove('muted');
    const matches=d.participants||(d.participant?[d.participant]:[]);
    if(!matches.length){box.textContent='일치하는 참가자가 없어요. 이름이나 학번 끝 두 자리, 초대장 전체 번호를 다시 확인해 주세요.';return;}
    const summary=document.createElement('p');summary.className='search-summary';summary.textContent=d.truncated?'검색 결과가 많아 최근 50명을 표시합니다. 이름과 학번 끝 두 자리로 좁혀 주세요.':matches.length+'명의 참가자를 찾았어요.';box.append(summary);
    for(const p of matches)box.append(participantCard(p));
  }catch(e){$('redeem-msg').textContent=e.message;}
  finally{btn.disabled=false;btn.textContent='검색';box.removeAttribute('aria-busy');}
}
$('search-form').addEventListener('submit',async event=>{event.preventDefault();await searchParticipants();});
$('generate-qr').addEventListener('click',()=>{const url=$('public-url').value.trim();let valid=false;
  try{const p=new URL(url);valid=['http:','https:'].includes(p.protocol)&&!!p.hostname;}catch{}
  if(!valid){alert('http:// 또는 https://로 시작하는 주소를 넣어 주세요.');return;}
  const src='/api/admin/qr.svg?url='+encodeURIComponent(url);$('qr-image').src=src;$('qr-download').href=src;$('qr-address').textContent=url;$('qr-box').classList.remove('hidden');
});
function editorField(parent,label,value,callback,tag='input',hint=''){
  const l=document.createElement('label');l.textContent=label;parent.append(l);
  const field=document.createElement(tag);field.value=value??'';field.addEventListener('input',()=>callback(field.value));parent.append(field);
  if(hint){const p=document.createElement('div');p.className='field-hint';p.textContent=hint;parent.append(p);}
  return field;
}
function renderQuestions(){
  const box=$('question-list');box.replaceChildren();
  for(const [i,q] of questionCache.entries()){
    const wrap=document.createElement('div');wrap.className='question-editor';
    const head=document.createElement('div');head.className='editor-row';
    const title=document.createElement('strong');title.textContent=`문제 ${i+1}`;
    const del=document.createElement('button');del.type='button';del.className='danger-text';del.textContent='삭제';del.addEventListener('click',()=>{questionCache.splice(i,1);renderQuestions();});head.append(title,del);wrap.append(head);
    const grp=document.createElement('select');
    [['proverb','이미지 속담'],['ticket','서재의 추리'],['chocolate','봉인된 초대']].forEach(([v,label])=>{const option=document.createElement('option');option.value=v;option.textContent=label;grp.append(option);});
    grp.value=q.group;grp.addEventListener('change',()=>q.group=grp.value);
    const l=document.createElement('label');l.textContent='퀴즈 유형';wrap.append(l,grp);
    editorField(wrap,'문제 문장',q.question,v=>q.question=v,'textarea');
    const cols=document.createElement('div');cols.className='editor-two';
    const a=document.createElement('div');const b=document.createElement('div');
    const kind=document.createElement('select');
    for(const [value,label] of [['choice','객관식'],['text','서술형']]){const o=document.createElement('option');o.value=value;o.textContent=label;kind.append(o);}
    kind.value=q.accepted_answers?.length?'text':'choice';
    kind.addEventListener('change',()=>{q.accepted_answers=kind.value==='text'?['정답']:[];if(kind.value==='choice'&&!q.options.length)q.options=['보기 1','보기 2'];renderQuestions();});
    wrap.append(kind);
    if(q.accepted_answers?.length){
      editorField(a,'인정 정답 (한 줄당 한 개)',q.accepted_answers.join('\n'),v=>q.accepted_answers=v.split('\n'),'textarea','띄어쓰기를 제거하고 서버에서 비교합니다.');
    }else{
      editorField(a,'보기 (한 줄당 한 개)',q.options.join('\n'),v=>q.options=v.split('\n'),'textarea');
      const ans=editorField(b,'정답 번호 (1부터)',q.answer+1,v=>q.answer=Number(v)-1,'input');ans.type='number';ans.min='1';ans.max='5';
    }
    cols.append(a,b);wrap.append(cols);
    editorField(wrap,'문제에 표시할 이미지 파일명 (선택)',q.image||'',v=>q.image=v,'input','예: quiz-well.jpg');
    editorField(wrap,'보기 이미지 파일명 (선택 · 줄마다 1개)',(q.option_images||[]).join('\n'),v=>q.option_images=v.split('\n').map(x=>x.trim()).filter(Boolean),'textarea','보기마다 이미지를 넣을 때는 파일명을 보기 개수에 맞춰 입력하세요.');
    const images=[q.image,...(q.option_images||[])].filter(Boolean);
    if(images.length){const previews=document.createElement('div');previews.className='photo-previews';
      for(const img of images){const item=document.createElement('img');item.src='/assets/'+encodeURIComponent(img);item.alt=img;previews.append(item);}wrap.append(previews);
    }
    box.append(wrap);
  }
}
async function loadQuestions(){const d=await api('/api/admin/questions',null,'GET');questionCache=d.questions;renderQuestions();}
$('add-question').addEventListener('click',()=>{questionCache.push({group:'proverb',question:'',options:['','','',''],answer:0,image:'',option_images:[]});renderQuestions();$('question-list').lastElementChild?.scrollIntoView({behavior:'smooth',block:'center'});});
$('save-questions').addEventListener('click',async()=>{$('questions-msg').textContent='';
  try{const questions=questionCache.map(q=>({group:q.group,question:String(q.question).trim(),options:q.options.map(x=>String(x).trim()),answer:q.answer,accepted_answers:(q.accepted_answers||[]).map(x=>String(x).trim()).filter(Boolean),image:(q.image||'').trim(),option_images:(q.option_images||[]).map(x=>x.trim()).filter(Boolean)}));
    const res=await api('/api/admin/questions',{questions});$('questions-msg').textContent=res.message;await loadQuestions();}
  catch(e){$('questions-msg').textContent=e.message;}
});
refresh().catch(()=>loginScreen());

