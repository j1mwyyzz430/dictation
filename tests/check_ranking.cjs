// Executes the actual embedded Apps Script against in-memory storage; no Google calls.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const backend=html.match(/<script id="backendSource"[^>]*>([\s\S]*?)<\/script>/)[1];
const app=html.match(/<script id="appScript"[^>]*>([\s\S]*?)<\/script>/)[1];
const rank=s=>s.match(/function rankSummaries\([\s\S]*?\n\}/)[0];
assert.equal(rank(backend),rank(app),'browser/backend ranking rules must match');
const ctx=vm.createContext({console,assert});
vm.runInContext(backend,ctx);
vm.runInContext(`
const objects=new Map(),tables=new Map(),cacheMap=new Map(),properties=new Map();let serial=0;
const roster=[{studentId:'fictional-a',name:'測試甲',classId:'6B',grade:'6',active:true},{studentId:'fictional-b',name:'測試乙',classId:'6A',grade:'6',active:true}];
const cp=x=>JSON.parse(JSON.stringify(x));
get5_=key=>objects.has(key)?cp(objects.get(key)):null;
put5_=(key,value)=>objects.set(key,cp(value));
students5_=()=>cp(roster);
sheet5_=(name,head)=>{if(!tables.has(name))tables.set(name,[head]);const rows=tables.get(name);return {
 getDataRange:()=>({getValues:()=>cp(rows)}),appendRow:row=>rows.push(cp(row)),
 getRange:(r,c,n,w)=>({setValues:values=>{for(let i=0;i<n;i++)for(let j=0;j<w;j++)rows[r-1+i][c-1+j]=values[i][j]}})
}};
rows5_=(name,head)=>sheet5_(name,head).getDataRange().getValues().slice(1);
PropertiesService={getScriptProperties:()=>({getProperty:k=>properties.get(k)||null,setProperty:(k,v)=>properties.set(k,v)})};
Utilities={getUuid:()=>String(++serial)};
CacheService={getScriptCache:()=>({get:k=>cacheMap.get(k)||null,put:(k,v)=>cacheMap.set(k,v)})};
const now=Date.now(),session={role:'student',studentId:'fictional-a',grade:'6'},teacher={role:'teacher'};
const fixture=(id='test-paper-0001')=>({id,studentId:'fictional-a',grade:'6',classId:'6B',name:'測試甲',mode:'dictation',scope:'words',settings:{scoreRule:6,punctuationCounts:false},groups:[{key:'w0',kind:'詞語',text:'甲乙丙丁'}],cells:[{auto:'match',manual:null},{auto:'match',manual:null},{auto:'review',manual:null},{auto:'blank',manual:null}],created:new Date(now).toISOString(),version:1,approved:false,elapsed:40,timeValid:true});
const source=fixture(),pre={snap:source,groups:source.groups,cells:source.cells};
// A cached v2.1 result must never suppress new provisional scores.
cacheMap.set('rank5:6:total:'+weekStart(now)+':0',JSON.stringify({rows:[]}));
let a=submit_({id:source.id,elapsed:40},session,pre).attempt;
let board=board5_(session,{period:'total'});
assert.equal(board.rankingVersion,'2.2');assert.equal(board.rows[0].points,15);assert.equal(board.rows[0].provisionalCount,1);assert.equal(board.rows[0].count,1);
assert.equal(a.metrics.pointsMax,22.5); // Uncertain character is not silently awarded.
submit_({id:source.id,elapsed:40},session,pre);
assert.equal(summaries5_().length,1);assert.equal(board5_(session,{}).rows[0].points,15);
assert.throws(()=>review_({id:a.id,version:0,manual:[true,true,true,false],approve:true}),/已更新/);
a=review_({id:a.id,version:1,manual:[true,false,null,false],approve:false}).attempt;
board=board5_(session,{});assert.equal(board.rows[0].points,7.5);assert.equal(board.rows[0].count,1);
assert.throws(()=>review_({id:a.id,version:2,manual:[true,false,null,false],approve:true}),/待核/);
a=review_({id:a.id,version:2,manual:[true,true,true,false],approve:true}).attempt;
board=board5_(session,{});assert.equal(board.rows[0].points,22.5);assert.equal(board.rows[0].provisionalCount,0);assert.equal(board.rows[0].count,1);
a=review_({id:a.id,version:3,manual:[true,true,true,false],approve:false}).attempt;
assert.equal(board5_(session,{}).rows[0].points,22.5);assert.equal(board5_(session,{}).rows[0].provisionalCount,1);
a=review_({id:a.id,version:4,manual:[true,true,true,false],approve:true,excluded:true}).attempt;
assert.equal(board5_(session,{}).rows.length,0);
console.log('PASS submit → provisional board → teacher changes → approval/revocation/exclusion, retry idempotence and cache invalidation');
const make=(overrides={})=>{const a=Object.assign(fixture(),overrides);a.metrics=marks(a);return a};
const valid=make(),studentB=make({studentId:'fictional-b'});
const excluded=['excluded','incomplete','testAccount','practiceOnly'].map(k=>make({[k]:true}));
const zero=make({cells:Array.from({length:4},()=>({auto:'blank'}))});
const practice=make({mode:'review'});
const rows=rankSummaries([valid,studentB,...excluded,zero,practice],roster,'6','total',now);
assert.equal(rows.length,2);assert.equal(rows[0].rank,1);assert.equal(rows[1].rank,1);
assert.equal(rankSummaries([valid],roster,'4','total',now).length,0);
assert.equal(rankSummaries([make({created:new Date(weekStart(now)-1).toISOString()})],roster,'6','week',now).length,0);
assert.equal(rankSummaries([make({created:new Date(weekStart(now)).toISOString()})],roster,'6','week',now).length,1);
assert.equal(rankSummaries([make({created:new Date(weekStart(now)+7*86400000).toISOString()})],roster,'6','week',now).length,0);
const random=make({mode:'random'});assert.equal(random.metrics.points,6);
const legacy=make({settings:{scoreRule:5,penalty:3},legacyScore:88});assert.equal(legacy.metrics.score,88);assert.equal(legacy.metrics.points,50);
// Interrupted summary write is repaired by an idempotent submit retry.
const saved=get5_('attempt:'+a.id);saved.excluded=false;saved.version++;put5_('attempt:'+a.id,saved);
submit_({id:a.id},session,null);assert.equal(board5_(session,{}).rows[0].points,22.5);
sheet5_('DeletedAttempts',['id','studentId','deletedAt']).appendRow([a.id,a.studentId,new Date().toISOString()]);
properties.set('RANK_REV',Utilities.getUuid());assert.equal(board5_(session,{}).rows.length,0);
console.log('PASS zero/practice exclusions, ties, grade scope, HK weekly boundaries, old scores, random scoring, summary recovery and deleted papers');
const config=normalizeConfig5_({stamp:'fixture',classes:{'6B':[]},lessons:{'6B':[{id:'test-lesson',title:'四課詞語',grade:'6',status:'published',words:['甲','乙','丙','丁'],sentences:[],paragraph:'',wordSections:[{title:'第一課',start:1,end:1},{title:'第二課',start:2,end:4}]}]},settings:{}});
put5_('config',config);
const result=saveConfig5_(config).config;
assert.equal(result.lessons['6B'][0].wordSections[1].end,4);
assert.equal(result.backendVersion,'2.2');assert.equal(get5_('config').backendVersion,undefined);
assert.equal(publicConfig5_().lessons['6B'][0].wordSections[0].title,'第一課');
for(const invalid of [{title:'重疊',start:1,end:2},{title:'越界',start:5,end:6},{title:'',start:1,end:1}]){
 const bad=cp(result);bad.lessons['6B'][0].wordSections.push(invalid);
 assert.throws(()=>saveConfig5_(bad));assert.equal(get5_('config').stamp,result.stamp);
}
console.log('PASS real saveConfig/publicConfig functions preserve sections and reject invalid ranges before writes');
// Review rewards are server-stamped on new starts, never retroactive local points.
const rewardStart=start5_({id:'review-reward-paper',lessonId:'test-lesson',mode:'review',scope:'words',reviewRewardMax:999},session).start;
assert.equal(rewardStart.reviewRewardMax,3);
assert.equal(publicConfig5_().reviewRewardMax,3);
auth_=()=>session;
recognizeAll_=()=>[['甲'],['乙'],['丙'],['丁']];
const reviewPayload={id:rewardStart.id,mode:'review',studentId:session.studentId,keys:rewardStart.groups.map(g=>g.key),cells:[[[[.2,.5],[.8,.5]]],[[[.2,.5],[.8,.5]]],[],[]],elapsed:40,newRule:true,reviewRewardMax:999};
let rewarded=submit_(reviewPayload,session,prepareSubmit_({payload:reviewPayload})).attempt;
assert.equal(rewarded.metrics.points,1.5);assert.equal(rewarded.metrics.maxScore,3);
assert.equal(board5_(session,{}).rows[0].points,1.5);
submit_(reviewPayload,session,prepareSubmit_({payload:reviewPayload}));
assert.equal(board5_(session,{}).rows[0].count,1);
rewarded=review_({id:rewarded.id,version:1,manual:[true,true,true,true],approve:true}).attempt;
assert.equal(board5_(session,{}).rows[0].points,3);assert.equal(board5_(session,{}).rows[0].count,1);
rewarded=review_({id:rewarded.id,version:2,manual:[false,false,false,false],approve:true}).attempt;
assert.equal(board5_(session,{}).rows.length,0);
const pendingReview={...fixture(),mode:'review',reviewRewardMax:3};
assert.equal(marks(pendingReview).points,1.5);assert.equal(marks(pendingReview).pointsMax,2.25);
for(const modifier of [{reviewRewardMax:undefined},{testAccount:true},{practiceOnly:true}])assert.equal(marks({...pendingReview,...modifier}).points,0);
assert.throws(()=>prepareSubmit_({payload:{...reviewPayload,id:'old-local-review',newRule:false}}),/沒有獎勵開卷/);
assert.equal(marks(fixture()).points,15);
console.log('PASS new review reward: server-controlled cap, 1.5/3 scores, shared ranking, retry idempotence, manual changes, uncertain/blank exclusion and no retroactive/test rewards');

`,ctx);
