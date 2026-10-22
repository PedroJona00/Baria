const $=s=>document.querySelector(s);let busy=false;
function element(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e}
function bubble(text,user=false){const div=element('div','',`message ${user?'user':'bot'}`);div.append(element('b',user?'VOCÊ':'BARIA ✳'),element('p',text));$('#messages').append(div);$('#messages').scrollTop=$('#messages').scrollHeight}
function renderDrink(d){const box=$('#drink');box.replaceChildren(element('h2',d.nome,'drink-title'));box.append(element('span',d.alcool?'Com álcool · 18+':'Sem álcool','badge'),element('span',d.categoria,'badge'));box.append(element('h3','INGREDIENTES'));const ul=element('ul','','recipe');d.ingredientes.forEach(i=>{const li=element('li');li.append(element('span',i.nome),element('span',i.quantidade));ul.append(li)});box.append(ul,element('h3','COMO PREPARAR'),element('p',d.preparo,'detail'),element('h3','UM GOLE DE CONHECIMENTO'),element('p',d.curiosidade,'detail fact'));d.contribuicoes.forEach(f=>box.append(element('p','Contribuição não verificada: '+f.texto,'detail contribution')))}
function renderSources(sources){
  if(!Array.isArray(sources))return;
  const box=element('div','','message bot');
  box.append(element('b','FONTES'));
  for(const source of sources){
    try{const url=new URL(source.url);if(url.protocol!=='https:'||!['pt.wikipedia.org','en.wikipedia.org','www.fda.gov'].includes(url.hostname))continue;
      const p=element('p');const link=element('a',source.title||url.hostname);link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';p.append(link);box.append(p);
    }catch(e){}
  }
  if(box.children.length>1){$('#messages').append(box);$('#messages').scrollTop=$('#messages').scrollHeight;}
}
async function send(message,action='chat'){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);$('#chat-status').textContent='BARIA está preparando sua resposta…';if(message)bubble(message,true);const preferences={};try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,action,preferences})});const data=await r.json();if(!r.ok)throw Error(data.error||'Erro na conexão');if(action==='reset'){$('#messages').replaceChildren();$('#drink').replaceChildren(element('p','Sua próxima sugestão aparecerá aqui.','empty-copy'))}bubble(data.message);renderSources(data.sources);$('#diagnostics').textContent=JSON.stringify(data.diagnostics||{},null,2);if(data.drink)renderDrink(data.drink);if(data.alternative_details?.length){bubble('Outras opções para suas preferências:\n\n'+data.alternative_details.map(d=>d.nome+'\n'+d.ingredientes.map(i=>'• '+i.nome+': '+i.quantidade).join('\n')).join('\n\n'));}else if(data.alternatives?.length){bubble('Outras opções para suas preferências: '+data.alternatives.join(' · '));}$('#chat-status').textContent=data.adding?'Sua próxima mensagem será uma contribuição.':'Recomendações a partir da memória JSON'}catch(e){bubble('Não consegui concluir: '+e.message+'. Tente novamente.');$('#chat-status').textContent='Falha na solicitação';if(action==='chat')$('#message').value=message}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
$('#chat').addEventListener('submit',e=>{e.preventDefault();const text=$('#message').value.trim();if(text&&!busy){$('#message').value='';send(text)}});document.querySelectorAll('[data-query]').forEach(b=>b.addEventListener('click',()=>send(b.dataset.query)));$('#finish').addEventListener('click',()=>send('','finish'));$('#reset').addEventListener('click',()=>send('','reset'));


$('#helpful').addEventListener('click',()=>send('Boa resposta, ajudou muito.','feedback'));
$('#unhelpful').addEventListener('click',()=>send('Não foi isso que eu pedi.','feedback'));
