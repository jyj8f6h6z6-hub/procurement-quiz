
const BANK = window.QUESTION_BANK || [];
const $ = s => document.querySelector(s);
const els = {
  home: $('#homeView'), quiz: $('#quizView'), total: $('#totalQuestions'), answered: $('#answeredCount'), accuracy: $('#accuracy'),
  category: $('#categorySelect'), type: $('#typeSelect'), order: $('#orderSelect'), selectionCount: $('#selectionCount'), startNumber: $('#startQuestionInput'), startHint: $('#startQuestionHint'),
  start: $('#startBtn'), wrong: $('#wrongBtn'), fav: $('#favoriteBtn'), wrongCount: $('#wrongCount'), favoriteCount: $('#favoriteCount'),
  reset: $('#resetStatsBtn'), fill: $('#progressFill'), progressText: $('#progressText'), theme: $('#themeBtn'),
  back: $('#backBtn'), qCategory: $('#quizCategory'), qProgress: $('#quizProgress'), qFill: $('#quizProgressFill'), star: $('#starBtn'),
  qType: $('#questionType'), qNum: $('#questionNumber'), qText: $('#questionText'), options: $('#options'), result: $('#resultBox'), legal: $('#legalBasisBox'),
  prev: $('#prevBtn'), next: $('#nextBtn')
};
const KEY='procurementQuizV1';
let state = JSON.parse(localStorage.getItem(KEY) || '{}');
state.answers ||= {}; state.favorites ||= {}; state.dark ||= false;
let chosenCount = 20, session=[], current=0, mode='normal';

function save(){localStorage.setItem(KEY,JSON.stringify(state));}
function categories(){return [...new Set(BANK.map(q=>q.category))];}
function init(){
  document.documentElement.classList.toggle('dark', !!state.dark);
  els.total.textContent = BANK.length.toLocaleString();
  els.category.innerHTML = `<option value="all">全部分類</option>` + categories().map(c=>`<option value="${escapeAttr(c)}">${c}</option>`).join('');
  updateHome(); updateSelection(); updateStartRange();
}
function escapeAttr(s){return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');}
function filtered(){
  return BANK.filter(q => (els.category.value==='all'||q.category===els.category.value) && (els.type.value==='all'||q.type===els.type.value));
}
function globalQuestionNumber(q){
  const m=String(q.id||"").match(/(\d+)/);
  return m ? Number(m[1]) : 0;
}
function updateStartRange(){
  if(!els.startNumber || !els.startHint) return;
  const isRandom=els.order.value==='random';
  els.startNumber.disabled=isRandom;
  if(isRandom){
    els.startHint.textContent='隨機模式會忽略起始題號；切回「依原題號」即可指定。';
    return;
  }
  const arr=filtered();
  if(!arr.length){
    els.startNumber.min=1;
    els.startNumber.removeAttribute('max');
    els.startHint.textContent='目前篩選條件沒有題目。';
    return;
  }
  if(els.category.value==='all'){
    const nums=arr.map(globalQuestionNumber).filter(Number.isFinite);
    const min=Math.min(...nums), max=Math.max(...nums);
    els.startNumber.min=min; els.startNumber.max=max;
    els.startNumber.placeholder=String(min);
    els.startHint.textContent=`全部分類時使用「全題庫序號」${min.toLocaleString()}–${max.toLocaleString()}；例如輸入 1200，會從全題庫第 1200 題附近開始。`;
  }else{
    const nums=arr.map(q=>Number(q.number)).filter(Number.isFinite);
    const min=Math.min(...nums), max=Math.max(...nums);
    els.startNumber.min=min; els.startNumber.max=max;
    els.startNumber.placeholder=String(min);
    els.startHint.textContent=`目前分類使用原題號 ${min.toLocaleString()}–${max.toLocaleString()}；若該題號因題型篩選不存在，會從下一個符合題型的題目開始。`;
  }
}
function updateSelection(){els.selectionCount.textContent=`${filtered().length.toLocaleString()} 題`; updateStartRange();}
function updateHome(){
  const vals=Object.values(state.answers); const answered=vals.length; const correct=vals.filter(x=>x.correct).length;
  els.answered.textContent=answered.toLocaleString(); els.accuracy.textContent=answered?`${Math.round(correct/answered*100)}%`:'—';
  const wrongIds=new Set(vals.filter(x=>!x.correct).map(x=>x.id));
  els.wrongCount.textContent=wrongIds.size; els.favoriteCount.textContent=Object.keys(state.favorites).filter(k=>state.favorites[k]).length;
  const pct=BANK.length?Math.min(100,answered/BANK.length*100):0; els.fill.style.width=`${pct}%`;
  els.progressText.textContent=answered?`已作答 ${answered.toLocaleString()} 題，其中答對 ${correct.toLocaleString()} 題。`:'尚未開始作答';
}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function startSession(source, name='normal'){
  let arr=[...source];

  if(name==='normal' && els.order.value==='sequential'){
    const raw=els.startNumber ? els.startNumber.value.trim() : '';
    if(raw!==''){
      const startNo=Number(raw);
      if(!Number.isInteger(startNo) || startNo<1){
        alert('請輸入有效的起始題號。');
        els.startNumber?.focus();
        return;
      }
      arr = els.category.value==='all'
        ? arr.filter(q => globalQuestionNumber(q) >= startNo)
        : arr.filter(q => Number(q.number) >= startNo);
      if(!arr.length){
        alert('此起始題號之後沒有符合目前篩選條件的題目。');
        els.startNumber?.focus();
        return;
      }
    }
  }

  if(els.order.value==='random' || name!=='normal') shuffle(arr);
  if(name==='normal' && chosenCount!=='all') arr=arr.slice(0,Number(chosenCount));
  if(!arr.length){alert('目前沒有符合條件的題目。'); return;}
  session=arr; current=0; mode=name; els.home.classList.remove('active'); els.quiz.classList.add('active'); renderQuestion(); window.scrollTo({top:0});
}
function renderQuestion(){
  const q=session[current]; if(!q)return;
  const rec=state.answers[q.id];
  els.qCategory.textContent=q.category; els.qProgress.textContent=`${current+1} / ${session.length}`; els.qFill.style.width=`${(current+1)/session.length*100}%`;
  els.qType.textContent=q.type==='choice'?'選擇題':'是非題'; els.qNum.textContent=`原題號 ${q.number}`; els.qText.textContent=q.question;
  els.star.textContent=state.favorites[q.id]?'★':'☆'; els.star.classList.toggle('active',!!state.favorites[q.id]);
  els.result.className='result-box hidden'; els.result.textContent=''; els.legal.className='legal-box hidden'; els.legal.textContent='';
  els.options.innerHTML='';
  if(q.type==='choice'){
    const letters=['A','B','C','D'];
    q.options.forEach((opt,i)=>{
      const b=document.createElement('button'); b.className='option-btn'; b.innerHTML=`<span class="option-key">${letters[i]}</span><span>${escapeHtml(opt)}</span>`;
      b.addEventListener('click',()=>answer(q,i+1)); els.options.appendChild(b);
    });
  }else{
    [[true,'O','正確'],[false,'X','錯誤']].forEach(([v,key,label])=>{
      const b=document.createElement('button'); b.className='option-btn tf-btn'; b.innerHTML=`<span class="option-key">${key}</span><span>${label}</span>`; b.addEventListener('click',()=>answer(q,v)); els.options.appendChild(b);
    });
  }
  if(rec) reveal(q,rec.value,false);
  els.prev.disabled=current===0; els.next.textContent=current===session.length-1?'完成':'下一題';
}
function escapeHtml(s){return String(s).replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
function answer(q,value){if(state.answers[q.id])return; const correct=value===q.answer; state.answers[q.id]={id:q.id,value,correct,at:Date.now()}; save(); reveal(q,value,true); updateHome();}
function reveal(q,value,animate){
  const correct=value===q.answer; const btns=[...els.options.children];
  btns.forEach((b,i)=>{b.disabled=true; const v=q.type==='choice'?i+1:(i===0); if(v===value)b.classList.add('selected',correct?'correct':'wrong'); if(v===q.answer)b.classList.add('reveal-correct');});
  els.result.className=`result-box ${correct?'good':'bad'}`;
  const ansText=q.type==='choice'?['A','B','C','D'][Number(q.answer)-1]:(q.answer?'O（正確）':'X（錯誤）');
  els.result.innerHTML=`<strong>${correct?'✓ 答對了':'✕ 答錯了'}</strong><br>正確答案：${ansText}`;
  if(q.legalBasis){els.legal.className='legal-box'; els.legal.textContent=`依據法源：${q.legalBasis}`;}
}
function goHome(){els.quiz.classList.remove('active'); els.home.classList.add('active'); updateHome(); window.scrollTo({top:0});}

document.querySelectorAll('#countButtons button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('#countButtons button').forEach(x=>x.classList.remove('active'));b.classList.add('active');chosenCount=b.dataset.count==='all'?'all':Number(b.dataset.count);}));
els.category.addEventListener('change',updateSelection); els.type.addEventListener('change',updateSelection); els.order.addEventListener('change',updateStartRange);
els.start.addEventListener('click',()=>startSession(filtered(),'normal'));
els.wrong.addEventListener('click',()=>{const ids=new Set(Object.values(state.answers).filter(x=>!x.correct).map(x=>x.id));startSession(BANK.filter(q=>ids.has(q.id)),'wrong');});
els.fav.addEventListener('click',()=>startSession(BANK.filter(q=>state.favorites[q.id]),'favorite'));
els.back.addEventListener('click',goHome);
els.prev.addEventListener('click',()=>{if(current>0){current--;renderQuestion();window.scrollTo({top:0,behavior:'smooth'});}});
els.next.addEventListener('click',()=>{if(current<session.length-1){current++;renderQuestion();window.scrollTo({top:0,behavior:'smooth'});}else goHome();});
els.star.addEventListener('click',()=>{const q=session[current];state.favorites[q.id]=!state.favorites[q.id];if(!state.favorites[q.id])delete state.favorites[q.id];save();renderQuestion();updateHome();});
els.reset.addEventListener('click',()=>{if(confirm('要清除所有答題紀錄、錯題與收藏嗎？')){state.answers={};state.favorites={};save();updateHome();}});
els.theme.addEventListener('click',()=>{state.dark=!state.dark;document.documentElement.classList.toggle('dark',state.dark);save();});
init();


/* ===== v2：註解／法規／串珠／概念 ===== */
(function () {
  const K = window.KNOWLEDGE || { annotations:{}, concepts:{} };
  let activeStudyTab = "notes";

  function getVisibleQuestion() {
    // 本題庫實際使用 session[current] 保存目前題目。
    try {
      if (typeof session !== "undefined" && typeof current !== "undefined" && session && session[current]) {
        return session[current];
      }
    } catch(e) {}
    try {
      if (typeof currentQuestion !== "undefined" && currentQuestion) return currentQuestion;
    } catch(e) {}
    try {
      if (typeof currentIndex !== "undefined" && typeof quizQuestions !== "undefined" && quizQuestions[currentIndex]) {
        return quizQuestions[currentIndex];
      }
    } catch(e) {}
    return null;
  }

  function annotationFor(q) {
    if (!q) return null;
    const ids = [q.id, q.questionId, q.uid, q.number].filter(v => v !== undefined && v !== null).map(String);
    for (const id of ids) if (K.annotations[id]) return K.annotations[id];
    return null;
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  }

  // v2.5.1：法規與串珠頁籤共用 helper。
  // v2.5.0 的 renderer 已呼叫這些函式，但函式未真正寫入 script.js，
  // 因此點擊「法規／串珠」時瀏覽器會拋出 ReferenceError，畫面停留在註解。
  function renderLawText(text, highlights=[]) {
    let out = esc(text);
    const keys = [...new Set((highlights || []).filter(Boolean).map(String))]
      .sort((a,b) => b.length - a.length);
    keys.forEach(key => {
      const safe = esc(key);
      out = out.split(safe).join(`<u class="law-key">${safe}</u>`);
    });
    return out.replace(/\n/g, "<br>");
  }

  function getQuestionById(id) {
    return BANK.find(q => String(q.id) === String(id)) || null;
  }

  function crossrefAnswerText(q) {
    if (!q) return "";
    if (q.type === "choice") {
      const letters = ["A","B","C","D"];
      const idx = Number(q.answer) - 1;
      return `${letters[idx] || q.answer}｜${q.options?.[idx] || ""}`;
    }
    return q.answer ? "O｜正確" : "X｜錯誤";
  }

  function crossrefOptionsHtml(q) {
    if (!q) return "";
    if (q.type === "choice") {
      const letters = ["A","B","C","D"];
      return `<div class="crossref-options">${(q.options || []).map((opt,i) =>
        `<div class="crossref-option ${Number(q.answer) === i+1 ? "is-answer" : ""}">
          <span>${letters[i]}</span><div>${esc(opt)}</div>
        </div>`
      ).join("")}</div>`;
    }
    return `<div class="crossref-options tf-crossref">
      <div class="crossref-option ${q.answer === true ? "is-answer" : ""}"><span>O</span><div>正確</div></div>
      <div class="crossref-option ${q.answer === false ? "is-answer" : ""}"><span>X</span><div>錯誤</div></div>
    </div>`;
  }

  function jumpToQuestionById(id) {
    const target = getQuestionById(id);
    if (!target) return;

    const existing = session.findIndex(q => String(q.id) === String(id));
    if (existing >= 0) {
      current = existing;
    } else {
      // 由串珠進入目前作答清單以外的題目時，插入下一題位置，保留原本作答工作階段。
      const insertAt = Math.min(current + 1, session.length);
      session.splice(insertAt, 0, target);
      current = insertAt;
    }
    renderQuestion();
    window.scrollTo({top:0, behavior:"smooth"});
  }

  function renderStudyTab(tab) {
    activeStudyTab = tab;
    document.querySelectorAll(".study-tab").forEach(b => b.classList.toggle("active", b.dataset.studyTab === tab));
    const q = getVisibleQuestion();
    const a = annotationFor(q);
    const box = document.getElementById("studyContent");
    if (!box) return;

    if (!a) {
      box.innerHTML = '<p class="study-empty">這一題目前只有題目與標準答案；註解、法規依據與串珠尚待查證建立。</p>';
      return;
    }

    if (tab === "notes") {
      const rows = a.notes || [];
      box.innerHTML = rows.length ? '<div class="study-list">' + rows.map(x =>
        `<div class="study-item"><strong>${esc(x.title || "註解")}</strong>${esc(x.text || "")}</div>`
      ).join("") + '</div>' : '<p class="study-empty">尚無註解。</p>';
    } else if (tab === "laws") {
      const rows = a.laws || [];
      box.innerHTML = rows.length ? '<div class="study-list">' + rows.map(x =>
        `<div class="study-item law-study-item">
          <strong>${esc(x.title || "法規依據")}</strong>
          ${x.lawText ? `<div class="law-text-box"><span class="law-text-label">對應法條</span><div class="law-text">${renderLawText(x.lawText,x.highlights)}</div></div>` : ""}
          ${x.text ? `<div class="law-explain"><span>本題重點</span>${esc(x.text)}</div>` : ""}
          <div class="study-meta">${esc(x.sourceType || "")}</div>
          ${x.url ? `<a class="official-source-link" href="${esc(x.url)}" target="_blank" rel="noopener">${String(x.sourceType || "").includes("函") ? "查看工程會函釋" : `查看${esc(x.sourceLabel || "官方")}現行法規`} ↗</a>` : ""}
          ${a.interpretationSearchUrl ? `<a class="interpretation-search-link" href="${esc(a.interpretationSearchUrl)}" target="_blank" rel="noopener">工程會解釋函查詢 ↗</a>` : ""}
        </div>`
      ).join("") + '</div>' : '<p class="study-empty">尚未建立法規／函釋資料。</p>';
    } else if (tab === "links") {
      const rows = a.links || [];
      box.innerHTML = rows.length ? '<div class="study-list">' + rows.map(x => {
        const rq = getQuestionById(x.questionId);
        if (!rq) return "";
        return `<div class="study-item crossref-item">
          <div class="crossref-top">
            <strong>${esc(x.label || `${rq.category}｜原題號 ${rq.number}`)}</strong>
            <span class="crossref-type">${rq.type==="choice"?"選擇題":"是非題"}</span>
          </div>
          <div class="crossref-question">${esc(rq.question)}</div>
          ${crossrefOptionsHtml(rq)}
          <div class="crossref-answer"><span>答案</span><strong>${esc(crossrefAnswerText(rq))}</strong></div>
          <button type="button" class="crossref-jump-btn" data-jump-question="${esc(rq.id)}">前往此題作答 →</button>
        </div>`;
      }).join("") + '</div>' : '<p class="study-empty">尚未建立相關題目串珠。</p>';
    } else {
      const ids = a.concepts || [];
      box.innerHTML = ids.length ? ids.map(id => {
        const c = K.concepts[id] || {title:id};
        const traps = (c.traps || []).map(t => `<li>${esc(t)}</li>`).join("");
        return `<div class="study-item concept-card"><strong>${esc(c.title)}</strong>${c.definition ? `<div class="concept-block"><span>概念是什麼</span>${esc(c.definition)}</div>` : ""}${c.examLogic ? `<div class="concept-block"><span>考題怎麼判斷</span>${esc(c.examLogic)}</div>` : ""}${traps ? `<div class="concept-block"><span>常見陷阱</span><ul>${traps}</ul></div>` : ""}${c.memory ? `<div class="concept-memory">記憶：${esc(c.memory)}</div>` : ""}</div>`;
      }).join("") : '<p class="study-empty">尚未建立核心概念。</p>';
    }
  }

  function refreshStudyPanel(forceShow=false) {
    const panel = document.getElementById("studyPanel");
    if (!panel) return;
    const q = getVisibleQuestion();
    const a = annotationFor(q);
    const note = document.getElementById("quickNote");
    if (note) note.textContent = a?.quickNote || "這一題的註解與法規串珠尚待建立。";
    const statusBadge = document.getElementById("reviewStatusBadge");
    if (statusBadge) {
      const lawStatus = a?.lawStatus || "";
      const verified = ["verified", "verified-regulation", "verified-interpretation"].includes(lawStatus);
      const sourceGiven = lawStatus === "source-given";
      const baseline = lawStatus === "source-benchmark" || lawStatus === "source-corrected";
      statusBadge.textContent = verified
        ? "已分析・法規已核對"
        : sourceGiven
          ? "已分析・題庫附法源"
          : baseline
            ? "已分析・第35版校正基準"
            : "已分析・法規已定位";
      statusBadge.classList.toggle("verified", verified);
      statusBadge.classList.toggle("structured", !verified);
    }
    const counts = {
      noteCount:(a?.notes || []).length,
      lawCount:(a?.laws || []).length,
      linkCount:(a?.links || []).length,
      conceptCount:(a?.concepts || []).length
    };
    Object.entries(counts).forEach(([id,n]) => { const el=document.getElementById(id); if(el) el.textContent=n; });
    if (forceShow) panel.classList.remove("hidden");
    renderStudyTab(activeStudyTab);
  }

  document.addEventListener("click", function(e) {
    const tab = e.target.closest(".study-tab");
    if (tab) renderStudyTab(tab.dataset.studyTab);
    const jump = e.target.closest("[data-jump-question]");
    if (jump) jumpToQuestionById(jump.dataset.jumpQuestion);
  });

  // 不侵入既有答題邏輯：監看答題區 DOM 變化；一旦答案回饋出現，就顯示延伸學習區。
  const observer = new MutationObserver(() => {
    const feedback = document.getElementById("resultBox");
    if (feedback && feedback.textContent.trim()) refreshStudyPanel(true);
  });
  document.addEventListener("DOMContentLoaded", () => {
    const feedback = document.getElementById("resultBox");
    if (feedback) observer.observe(feedback, {childList:true,subtree:true,characterData:true});
    document.querySelectorAll(".study-tab").forEach(b => b.addEventListener("click", () => renderStudyTab(b.dataset.studyTab)));
  });

  window.refreshStudyPanel = refreshStudyPanel;
})();

/* v2.1 hotfix：解析列跟隨 resultBox 顯示，並在換題時收合 */
(function(){
  function syncStudyPanel(){
    const result=document.getElementById("resultBox");
    const panel=document.getElementById("studyPanel");
    if(!result||!panel)return;
    const answered=!result.classList.contains("hidden") && result.textContent.trim().length>0;
    panel.classList.toggle("hidden",!answered);
    if(answered && typeof window.refreshStudyPanel==="function") window.refreshStudyPanel(true);
  }
  document.addEventListener("click",function(e){
    if(e.target.closest("#options button")) setTimeout(syncStudyPanel,10);
    if(e.target.closest("#nextBtn,#prevBtn")) setTimeout(syncStudyPanel,10);
  });
  document.addEventListener("DOMContentLoaded",function(){
    const result=document.getElementById("resultBox");
    if(result)new MutationObserver(syncStudyPanel).observe(result,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:["class"]});
  });
})();
