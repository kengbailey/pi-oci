import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {build} from '../build-tools/node_modules/esbuild/lib/main.js';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const r=path.resolve(process.env.PI_BUILD_DIR || '.build/minimal'), variant='compact';
const p=path.resolve('tracks/minimal/node_modules/@earendil-works/pi-coding-agent');
const guarded=JSON.parse(fs.readFileSync(new URL('../tracks/minimal/patch-inputs.json',import.meta.url)));
for(const [f,expected] of Object.entries(guarded.source_files)){
 const actual=crypto.createHash('sha256').update(fs.readFileSync(p+'/'+f)).digest('hex');
 if(actual!==expected) throw Error('Upstream patch input changed: '+f+'; review Minimal before upgrading');
}
const ai=p+'/node_modules/@earendil-works/pi-ai/dist';
const out=r+'/app-'+variant, dest=out+'/node_modules/@earendil-works/pi-coding-agent';
if(!process.env.PI_MINIMAL_PROBE_ONLY){
 if(fs.existsSync(out)) throw Error('refuse overwrite '+out);
 fs.mkdirSync(dest,{recursive:true});
}
const keepApi=['openai-completions','openai-responses','openai-codex-responses'];
const require=createRequire(p+'/package.json');
const patches=[];
const exact=(s,a,b)=>{if(s.split(a).length!==2)throw Error('guard failed: '+a);return s.replace(a,b)};
const plugin={name:'minimal-pinned-patches',setup(b){
 b.onResolve({filter:/^jiti\/static$/},()=>({path:'jiti/static',namespace:'lazy-jiti'}));
 b.onLoad({filter:/.*/,namespace:'lazy-jiti'},()=>({contents:'import {createRequire} from "node:module"; const require=createRequire(import.meta.url);let impl;export function createJiti(...args){impl??=require("jiti").createJiti;return impl(...args)}',loader:'js'}));
 b.onResolve({filter:/^pi-minimal-http-impl$/},()=>({path:p+'/dist/core/http-dispatcher.js',namespace:'http-impl'}));
 b.onLoad({filter:/.*/,namespace:'http-impl'},({path:f})=>({contents:fs.readFileSync(f,'utf8'),loader:'js',resolveDir:path.dirname(f)}));
 b.onLoad({filter:/\.js$/},({path:f})=>{
  let s=fs.readFileSync(f,'utf8'), before=s;
  if(f===ai+'/providers/all.js'){
   s=s.replace(/^import \{.*Provider \} from "\.\/(?!openai(?:-codex)?\.js)[^"]+";\n/gm,'');
   s=exact(s,'export { radiusProvider };','export function radiusProvider(){throw new Error("Radius is not included in OpenAI-only Minimal")}');
   s=s.replace(/(export function builtinProviders\(\) \{\s*return )\[[\s\S]*?\];/,'$1[openaiProvider(),openaiCodexProvider()];');
   s=exact(s,'return [openrouterImagesProvider()];','return [];');
  }
  if(f===ai+'/models.generated.js'){
   s='import {OPENAI_MODELS} from "./providers/openai.models.js";import {OPENAI_CODEX_MODELS} from "./providers/openai-codex.models.js";export const MODELS={openai:OPENAI_MODELS,"openai-codex":OPENAI_CODEX_MODELS};';
  }
  if(f===ai+'/compat.js'){
   s=s.split('\n').filter(l=>{
    const m=l.match(/^(?:import|export).*"\.\/api\/([^\"]+)\.lazy\.js"/);
    if(m&&!keepApi.includes(m[1]))return false;
    if(/^\s*\["/.test(l)&&l.includes('Api()')&&!keepApi.some(x=>l.includes('"'+x+'"')))return false;
    return !l.includes('export * from "./providers/images/register-builtins.js"');
   }).join('\n');
  }
  if(f===ai+'/legacy-api-aliases.js'){
   s=s.split('\n').filter(l=>l.startsWith('//')||!l.trim()||l.includes('openAI')||l.includes('streamOpenAI')||l.includes('streamSimpleOpenAI')).join('\n');
  }
  if(f===ai+'/image-models.generated.js')s='export const IMAGE_MODELS={};';
  if(f===ai+'/providers/images/register-builtins.js')s='export function registerBuiltInImagesApiProviders(){};export async function generateImagesOpenRouter(){throw new Error("OpenRouter images not included in Minimal")}';
  if(f===p+'/dist/config.js')s=exact(s,'export const isBunBinary = import.meta.url.includes("$bunfs") || import.meta.url.includes("~BUN") || import.meta.url.includes("%7EBUN");','export const isBunBinary = false;');
  if(variant!=='providers'&&f===p+'/dist/utils/syntax-highlight.js'){
   const body=s.slice(s.indexOf('const SPAN_CLOSE'));
   s='import {createRequire} from "node:module";import {decodeHtmlEntityAt} from "./html.js";const require=createRequire(import.meta.url);let engine;const hljs=new Proxy({}, {get:(_,k)=>(engine??=require("@pi-minimal/highlight"))[k]});export function loadAllHighlightLanguages(){return Promise.resolve()}\n'+body;
  }
  if(['network','compact'].includes(variant)&&f===p+'/dist/core/http-dispatcher.js'){
   s=s.slice(0,s.indexOf('const ignoreUndiciDispatcherError')).replace('import * as undici from "undici";','');
   s+=`let loaded,pending,lastTimeout=DEFAULT_HTTP_IDLE_TIMEOUT_MS;
export function configureHttpDispatcher(timeoutMs=DEFAULT_HTTP_IDLE_TIMEOUT_MS){
 const normalized=parseHttpIdleTimeoutMs(timeoutMs);if(normalized===undefined)throw new Error('Invalid HTTP idle timeout: '+timeoutMs);lastTimeout=normalized;
 if(loaded){loaded.configureHttpDispatcher(normalized);return;}
 const canInstall=installedGlobalFetch===undefined?globalThis.fetch===originalGlobalFetch:globalThis.fetch===installedGlobalFetch;
 if(canInstall){installedGlobalFetch=async(...args)=>{pending??=import('pi-minimal-http-impl').then(m=>{loaded=m;m.configureHttpDispatcher(lastTimeout)});await pending;return globalThis.fetch(...args)};globalThis.fetch=installedGlobalFetch;}
}\n`;
  }
  if(s!==before){patches.push(path.relative(p,f));return{contents:s,loader:'js',resolveDir:path.dirname(f)}}
 });
}};
const opts={bundle:true,platform:'node',format:'esm',target:'node24',minify:true,keepNames:variant!=='compact',metafile:true,legalComments:'eof',define:{PI_BUNDLED_NODE:'true','process.versions.bun':'undefined'},plugins:[plugin],banner:{js:'import {createRequire as __piCreateRequire} from "node:module";const require=__piCreateRequire(import.meta.url);'},external:['@earendil-works/chord','@silvia-odwyer/photon-node','@pi-minimal/highlight','jiti','bufferutil','utf-8-validate','kerberos','supports-color']};
export {opts,p,r};
if(!process.env.PI_MINIMAL_PROBE_ONLY){
const result=await build({...opts,entryPoints:{cli:p+'/dist/cli.js',index:p+'/dist/index.js','rpc-entry':p+'/dist/rpc-entry.js'},outdir:dest+'/dist/bundle',splitting:true,chunkNames:'chunks/[name]-[hash]'});
await build({...opts,entryPoints:{'openai-codex':ai+'/auth/oauth/openai-codex.js','image-resize-worker':p+'/dist/utils/image-resize-worker.js'},outdir:dest+'/dist/bundle/chunks',splitting:false});
const unexpected=Object.keys(result.metafile.inputs).filter(x=>/node_modules\/(?:@anthropic-ai|@google|@aws-sdk|@smithy|@mistralai|google-auth-library)\//.test(x));
if(unexpected.length)throw Error('unwanted SDK retained '+unexpected.join(','));
for(const f of ['package.json','README.md','CHANGELOG.md','docs','dist/modes/interactive/theme','dist/modes/interactive/assets','dist/core/export-html']) fs.cpSync(p+'/'+f,dest+'/'+f,{recursive:true});
for(const pkg of ['jiti','@silvia-odwyer/photon-node','@earendil-works/chord']) fs.cpSync(p+'/node_modules/'+pkg,out+'/node_modules/'+pkg,{recursive:true});
if(variant!=='providers'){
 const full=require('highlight.js'),names=full.listLanguages(),aliases={};
 for(const n of names)for(const a of full.getLanguage(n).aliases||[])aliases[a]=n;
 // Exact language names take precedence over colliding aliases (notably c/cpp).
 for(const n of names)aliases[n]=n;
 const src=`const core=require('highlight.js/lib/core');const aliases=${JSON.stringify(aliases)};const loaders={${names.map(n=>JSON.stringify(n)+':()=>require('+JSON.stringify('highlight.js/lib/languages/'+n)+')').join(',')}};const loading=new Set();function ensure(name){const k=aliases[String(name).toLowerCase()];if(!k)return;if(core.getLanguage(k)||loading.has(k))return core.getLanguage(k);loading.add(k);core.registerLanguage(k,loaders[k]());const seen=new Set();function visit(x){if(!x||typeof x!=='object'||seen.has(x))return;seen.add(x);if(x.subLanguage)for(const s of [].concat(x.subLanguage))if(s!==k)ensure(s);for(const v of Object.values(x))if(typeof v==='object')visit(v)}visit(core.getLanguage(k));loading.delete(k);return core.getLanguage(k)}module.exports={...core,getLanguage:ensure,listLanguages:()=>Object.keys(loaders),highlight:(code,opts)=>{ensure(opts.language);return core.highlight(code,opts)},highlightAuto:(code,subset)=>{for(const n of subset||Object.keys(loaders))ensure(n);return core.highlightAuto(code,subset)}};`;
 await build({stdin:{contents:src,resolveDir:p},outfile:out+'/node_modules/@pi-minimal/highlight/index.cjs',bundle:true,platform:'node',format:'cjs',target:'node24',minify:true,keepNames:true,legalComments:'eof'});
 fs.writeFileSync(out+'/node_modules/@pi-minimal/highlight/package.json','{"name":"@pi-minimal/highlight","main":"index.cjs"}');
 const neo=createRequire(out+'/package.json')('@pi-minimal/highlight');let count=0;
 for(const name of Object.keys(aliases))for(const code of ['const x=1; // test','<html><style>b{color:red}</style><script>let a=1;</script></html>','def hello():\n    return "Hi"']){if(full.highlight(code,{language:name,ignoreIllegals:true}).value!==neo.highlight(code,{language:name,ignoreIllegals:true}).value)throw Error('highlight mismatch '+name);count++}
 console.log('Highlight comparisons',count);
}
const manifest=JSON.parse(fs.readFileSync(dest+'/package.json'));
manifest.main='./dist/bundle/index.js';manifest.exports['.']={import:'./dist/bundle/index.js'};
fs.writeFileSync(dest+'/package.json',JSON.stringify(manifest,null,2));
function notices(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const f=dir+'/'+e.name;if(e.isDirectory())notices(f);else if(e.isFile()&&/^(licen[cs]e|copying|notice|copyright)/i.test(e.name)){const to=out+'/node_modules/third-party-notices/'+path.relative(p,f);fs.mkdirSync(path.dirname(to),{recursive:true});fs.copyFileSync(f,to)}}}
notices(p);
function prune(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const f=dir+'/'+e.name;if(e.isDirectory()){if(e.name==='images'&&f.includes('/docs/'))fs.rmSync(f,{recursive:true});else prune(f)}else if(/\.map$|\.d\.(?:ts|mts|cts)$/.test(e.name))fs.unlinkSync(f)}}prune(out);
fs.writeFileSync(r+'/'+variant+'-metafile.json',JSON.stringify(result.metafile));
fs.writeFileSync(r+'/'+variant+'-patches.json',JSON.stringify([...new Set(patches)].sort(),null,2));
console.log('Built',variant,'patches',new Set(patches).size,'inputs',Object.keys(result.metafile.inputs).length);
}
