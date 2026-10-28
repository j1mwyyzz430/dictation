// Real Apps Script selection/start/submit logic with in-memory storage and no network.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const backend=html.match(/<script id="backendSource"[^>]*>([\s\S]*?)<\/script>/)[1];
const app=html.match(/<script id="appScript"[^>]*>([\s\S]*?)<\/script>/)[1];
for(const name of ['wordSections22','selectWordSectionGroups22']){
 const pattern=new RegExp('function '+name+'\\([\\s\\S]*?\\n\\}');
 assert.equal(backend.match(pattern)[0],app.match(pattern)[0],name+' must agree in browser/backend');
}
const ctx=vm.createContext({assert,console});
vm.runInContext(backend,ctx);
vm.runInContext(`
const cp=x=>JSON.parse(JSON.stringify(x)),objects=new Map();let config,serial=0;
const session={studentId:'fictional-section-test',name:'本機測試',classId:'6B',grade:'6'};
const lesson={id:'section-test',title:'四課詞語',grade:'6',status:'published',
 words:Array.from({length:40},(_,i)=>'詞語'+(i+1)),sentences:['測試句子'],paragraphs:['測試段落'],memoryParagraphs:['背默內容'],readings:{'w7:0':'慈'},
 wordSections:[{title:'第一課',start:1,end:7},{title:'第二課',start:8,end:20},{title:'第三課',start:21,end:31},{title:'第四課',start:32,end:40}]};
config={stamp:'fixture-stamp',settings:{scoreRule:6,punctuationCounts:false,integrity:false},lessons:{'6B':[lesson]}};
config5_=()=>cp(config);get5_=k=>objects.has(k)?cp(objects.get(k)):null;put5_=(k,v)=>objects.set(k,cp(v));deleted6_=()=>false;
auth_=()=>session;storeAttempt5_=a=>{a.metrics=marks(a);put5_('attempt:'+a.id,a)};ensureSummary5_=()=>{};
const payload=(keys,more={})=>({id:'section-paper-'+(++serial),lessonId:lesson.id,mode:'dictation',scope:'words',wordSectionKeys:keys,configStamp:config.stamp,...more});
`,ctx);
// Stateful browser fixture; actual start/pre-submit/submit handlers, deterministic recognition.
if(process.argv.includes('--review-rpc')){
 ctx.rpc=JSON.parse(fs.readFileSync(0,'utf8'));
 const output=vm.runInContext(`
   for(const [k,v] of Object.entries(rpc.objects||{}))objects.set(k,v);
   let response;
   if(rpc.action==='start')response=start5_(rpc.payload,session);
   else if(rpc.action==='submit'){
     const snap=get5_('start:'+rpc.payload.id),expected=rpc.payload.keys.flatMap(k=>Array.from(snap.groups.find(g=>g.key===k).text));
     recognizeAll_=()=>expected.map(ch=>[ch]);
     response=submit_(rpc.payload,session,prepareSubmit_({payload:rpc.payload}));
   }else if(rpc.action==='attempt')response={attempt:get5_('attempt:'+rpc.payload.id)};
   else if(rpc.action==='myAttempts')response={attempts:[...objects].filter(([k])=>k.startsWith('attempt:')).map(([,a])=>({...a,metrics:marks(a)}))};
   else if(rpc.action==='leaderboard')response={rankingVersion:'2.2',updated:new Date().toISOString(),rows:rankSummaries([...objects].filter(([k])=>k.startsWith('attempt:')).map(([,a])=>({...a,metrics:marks(a)})),[session],'6','total',Date.now())};
   else throw Error('Unexpected mock API '+rpc.action);
   JSON.stringify({result:response,objects:Object.fromEntries(objects)});
 `,ctx);
 process.stdout.write(output);process.exit(0);
}
// Browser tests obtain snapshots from this same real start handler via stdin/stdout.
if(process.argv.includes('--snapshot')){
 ctx.input=JSON.parse(fs.readFileSync(0,'utf8'));
 process.stdout.write(JSON.stringify(vm.runInContext('start5_(input,session)',ctx)));process.exit(0);
}
vm.runInContext(`
let p=payload(['section1']),start=start5_(p,session).start;
assert.deepEqual(start.groups.map(g=>g.key),Array.from({length:13},(_,i)=>'w'+(i+7)));
assert.equal(start.readings['w7:0'],'慈');assert.equal(start.groups[0].title,'第二課');
assert.deepEqual(start.wordSectionKeys,['section1']);
const all=start5_(payload(null),session).start;assert.equal(all.groups.length,40);
const multiple=start5_(payload(['section3','section0']),session).start;
assert.deepEqual(multiple.groups.map(g=>g.key),[...Array.from({length:7},(_,i)=>'w'+i),...Array.from({length:9},(_,i)=>'w'+(31+i))]);
const mixed=start5_(payload(['section1'],{scope:'all',paragraphKeys:['p0']}),session).start;
assert.deepEqual(mixed.groups.slice(-2).map(g=>g.key),['s0','p0']);
for(const keys of [[],['section0','section0'],['w0'],['section99'],[0],'section0']){
 const bad=payload(keys);assert.throws(()=>start5_(bad,session));assert.equal(get5_('start:'+bad.id),null);
}
assert.throws(()=>start5_(payload(['section0'],{configStamp:'old'}),session),/教材已更新/);
for(const mode of ['memory','random'])assert.throws(()=>start5_(payload(['section0'],{mode}),session),/不支援/);
assert.throws(()=>start5_(payload(['section0'],{scope:'sentences'}),session),/不支援/);
const memory=start5_(payload(null,{mode:'memory',scope:'paragraph'}),session).start;
assert.equal(memory.groups[0].text,'背默內容');
assert.equal(start5_(payload(null,{mode:'random',count:5}),session).start.groups.length,5);
// Frozen start remains unchanged when the teacher edits the current lesson.
config.stamp='new-stamp';lesson.words[7]='已更改';
assert.deepEqual(start5_(p,session).start,start);
assert.throws(()=>start5_(p,{...session,studentId:'another'}),/不是你的/);
const chars=start.groups.flatMap(g=>Array.from(g.text));
recognizeAll_=()=>chars.map(ch=>[ch]);
const ink=chars.map(()=>[[[.2,.5],[.8,.5]]]);
const submission={id:p.id,studentId:session.studentId,mode:'dictation',keys:start.groups.map(g=>g.key),cells:ink,elapsed:90,newRule:true};
const pre=prepareSubmit_({payload:submission,token:'fixture'});
const result=submit_(submission,session,pre).attempt;
assert.equal(result.cells.length,chars.length);assert.ok(Math.abs(marks(result).score-30)<1e-9);assert.ok(Math.abs(marks(result).points-30)<1e-9);
assert.equal(result.readings['w7:0'],'慈');assert.deepEqual(result.wordSectionKeys,['section1']);
// Validate forged/omitted groups before any attempt exists.
const fresh=start5_(payload(['section0']),session).start;
const good={...submission,id:fresh.id,keys:fresh.groups.map(g=>g.key),cells:fresh.groups.flatMap(g=>Array.from(g.text)).map(()=>[])};
assert.throws(()=>prepareSubmit_({payload:{...good,keys:[...good.keys,'w20']}}),/題目不完整/);
assert.throws(()=>prepareSubmit_({payload:{...good,keys:good.keys.slice(1)}}),/題目不完整/);
assert.throws(()=>prepareSubmit_({payload:{...good,cells:[]}}),/格數不符/);
const noSections=cp(lesson);delete noSections.wordSections;config.lessons['6B']=[noSections];
assert.equal(start5_(payload(null),session).start.groups.length,40);
config.lessons['6B']=[{...lesson,wordSections:[lesson.wordSections[0]]}];
assert.equal(start5_(payload(['other']),session).start.groups.length,33);
console.log('PASS real start/submit: single/multiple/all sections, readings, 30-point scoring, mixed scope, invalid/stale/forged requests, immutable retries and legacy lessons');
`,ctx);
