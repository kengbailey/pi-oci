// A deterministic model exercises Pi's real streaming adapter and tool loop.
// No API key, internet service, or home-LAN connection is used.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
const cli='/opt/pi/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js';
const flavor=process.env.PI_TEST_FLAVOR;
assert.ok(['standard','minimal'].includes(flavor));
const req=createRequire('/opt/pi/package.json');
const nested=createRequire('/opt/pi/node_modules/@earendil-works/pi-coding-agent/package.json');
const photon=nested('@silvia-odwyer/photon-node');
const pixel=new photon.PhotonImage(new Uint8Array([255,0,0,255]),1,1);
assert.equal(pixel.get_width(),1);pixel.free();
assert.notEqual(process.getuid(),0);
assert.throws(()=>fs.writeFileSync('/usr/pi-test','bad'));
assert.equal(fs.existsSync('/var/run/docker.sock'),false);
const status=fs.readFileSync('/proc/self/status','utf8');
assert.match(status,/CapEff:\s+0+\n/);assert.match(status,/Seccomp:\s+2/);
const run=(args,timeout=180000)=>new Promise((resolve,reject)=>{
  console.log('RUN', args.join(' '));
  const child=spawn(process.execPath,[cli,...args],{cwd:'/workspace',env:process.env});
  child.stdin.end();
  let output='',error='';
  const timer=setTimeout(()=>{child.kill('SIGKILL');reject(Error('Pi timeout: '+output.slice(-3000)+error))},timeout);
  child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>error+=b);
  child.on('error',reject);child.on('exit',code=>{clearTimeout(timer);resolve({code,output,error})});
});
const version=await run(['--version']);assert.equal(version.code,0);assert.match(version.output,/0\.\d+\.\d+/);
fs.mkdirSync('/home/pi/.pi/agent',{recursive:true});
fs.writeFileSync('/workspace/sum.js','export function sum(a,b){return a-b}\n');
fs.writeFileSync('/workspace/package.json','{"type":"module"}');
fs.writeFileSync('/workspace/check.mjs',"import assert from 'node:assert/strict';import {sum} from './sum.js';assert.equal(sum(2,3),5);console.log('TEST_OK');\n");
const plan=[
 ['ls',{path:'.'}],['find',{pattern:'*.js',path:'.'}],['grep',{pattern:'return',path:'sum.js'}],
 ['read',{path:'sum.js'}],['edit',{path:'sum.js',oldText:'return a-b',newText:'return a+b'}],
 ['bash',{command:'node check.mjs'}],['write',{path:'result.txt',content:'ALL_TOOLS_OK\n'}]
];
let stage=0,mode='tools',calls=0;
const server=http.createServer(async(request,response)=>{
 try {
  assert.equal(request.url,'/v1/chat/completions');
  let body='';for await(const b of request)body+=b;
  const data=JSON.parse(body);assert.equal(data.stream,true);calls++;
  if(mode==='tools'&&stage>0){
   const results=data.messages.filter(m=>m.role==='tool');assert.ok(results.length>=stage);
  }
  response.writeHead(200,{'content-type':'text/event-stream'});
  const send=(delta,finish_reason=null)=>response.write('data: '+JSON.stringify({id:'fixture-'+calls,object:'chat.completion.chunk',created:1,model:'fixture',choices:[{index:0,delta,finish_reason}]})+'\n\n');
  send({role:'assistant'});
  if(mode==='tools'&&stage<plan.length){
   const [name,args]=plan[stage++];
   assert.ok(data.tools.some(t=>t.function.name===name),'tool not registered: '+name);
   send({tool_calls:[{index:0,id:'call-'+stage,type:'function',function:{name,arguments:JSON.stringify(args)}}]});send({},'tool_calls');
  }else if(mode==='extension'){
   const name='fixture_hello';assert.ok(data.tools.some(t=>t.function.name===name));
   mode='extension-result';send({tool_calls:[{index:0,id:'hello',type:'function',function:{name,arguments:'{}'}}]});send({},'tool_calls');
  }else{send({content:'FIXTURE_DONE'});send({},'stop')}
  response.end('data: [DONE]\n\n');
 }catch(e){console.error(e);response.destroy(e);process.exitCode=1}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const models={providers:{fixture:{baseUrl:`http://127.0.0.1:${server.address().port}/v1`,api:'openai-completions',apiKey:'fixture-not-a-secret',models:[{id:'fixture',name:'Fixture',reasoning:false,input:['text'],contextWindow:32000,maxTokens:1024,cost:{input:0,output:0,cacheRead:0,cacheWrite:0}}]}}};
fs.writeFileSync('/home/pi/.pi/agent/models.json',JSON.stringify(models));
const base=['--mode','json','--provider','fixture','--model','fixture','--thinking','off','--no-skills','--no-prompt-templates','--no-themes'];
const check=result=>{
 assert.equal(result.code,0,result.error);
 const events=result.output.split('\n').filter(l=>l.startsWith('{')).map(l=>JSON.parse(l));
 assert.ok(events.length>0);
 assert.ok(!events.some(e=>e.message?.stopReason==='error'||e.error||e.message?.errorMessage),result.output);
 assert.match(result.output,/FIXTURE_DONE/);
 return events;
};
try{
 const events=check(await run([...base,'--no-extensions','--tools','read,bash,edit,write,grep,find,ls','-p','Repair and test the fixture.']));
 const ends=events.filter(e=>e.type==='tool_execution_end');
 assert.equal(ends.length,7);assert.ok(ends.every(e=>!e.isError),JSON.stringify(ends));
 assert.equal(stage,7);assert.match(fs.readFileSync('/workspace/sum.js','utf8'),/return a\+b/);
 assert.equal(fs.readFileSync('/workspace/result.txt','utf8'),'ALL_TOOLS_OK\n');
 console.log('ALL_SEVEN_TOOLS_OK');
 mode='resume';check(await run([...base,'--no-extensions','--continue','-p','Resume the fixture session.']));
 console.log('SESSION_RESUME_OK');
 // Real .ts syntax, plus import through the public extension API.
 fs.writeFileSync('/workspace/hello.ts',`import {Type} from '@sinclair/typebox';\nexport default function(pi:any){pi.registerTool({name:'fixture_hello',label:'Fixture',description:'test',parameters:Type.Object({}),async execute(){return {content:[{type:'text',text:'HELLO_OK'}],details:{}}}})}`.replace("import {Type} from '@sinclair/typebox';","import {Type} from 'typebox';"));
 mode='extension';const ext=check(await run([...base,'-e','/workspace/hello.ts','-p','Use fixture_hello.']));
 assert.ok(ext.some(e=>e.type==='tool_execution_end'&&!e.isError));console.log('TYPESCRIPT_EXTENSION_OK');
 // Import provider registries from the real distributed entry points.
 if(flavor==='standard'){
  const p='/opt/pi/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/';
  const all=await import(p+'providers/all.js');assert.ok(all.builtinProviders().length>=40);
  for(const api of ['anthropic-messages','openai-completions','openai-responses','openai-codex-responses','google-generative-ai','google-vertex','bedrock-converse-stream','mistral-conversations','azure-openai-responses','openrouter-images','pi-messages']){
   await import(p+'api/'+api+'.js');
  }
  console.log('ALL_PROVIDER_IMPORTS_OK');
 }
}finally{await new Promise(r=>server.close(r))}
// Pi has historically exited 0 on provider errors; require an error event.
const failure=await run([...base,'--no-extensions','--no-session','-p','Unavailable endpoint.']);
assert.match(failure.output,/Connection error|ECONNREFUSED|fetch failed/);
console.log('STRUCTURED_FAILURE_OK');
console.log('RUNTIME_SUITE_OK');
