import assert from 'node:assert/strict';
import http from 'node:http';
import net from 'node:net';
import zlib from 'node:zlib';
const {configureHttpDispatcher,builtinProviders,builtinImagesProviders,getApiProviders}=await import(process.env.PI_HTTP_PROBE);
assert.deepEqual(builtinProviders().map(p=>p.id),['openai','openai-codex']);
assert.equal(builtinImagesProviders().length,0);
assert.deepEqual(getApiProviders().map(p=>p.api).sort(),['openai-codex-responses','openai-completions','openai-responses']);
console.log('OPENAI_ONLY_REGISTRIES_OK');
const sockets=new Set();let tunnels=0;
const server=http.createServer((req,res)=>{
 if(req.url==='/slow'){res.writeHead(200);res.write('start');setTimeout(()=>res.end('end'),2200).unref();return;}
 res.writeHead(200,{'content-type':'application/json','content-encoding':'gzip'});res.end(zlib.gzipSync(JSON.stringify({ok:true,path:req.url})));
});
const proxy=http.createServer();
proxy.on('connect',(req,downstream,head)=>{
 tunnels++;const [host,port]=req.url.split(':');const upstream=net.connect(Number(port),host,()=>{downstream.write('HTTP/1.1 200 Connection Established\r\n\r\n');if(head.length)upstream.write(head);upstream.pipe(downstream);downstream.pipe(upstream)});
 sockets.add(upstream);upstream.on('error',()=>downstream.destroy());downstream.on('error',()=>upstream.destroy());
});
for(const s of [server,proxy])s.on('connection',socket=>{sockets.add(socket);socket.on('close',()=>sockets.delete(socket));});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port;
try{
 process.env.HTTP_PROXY='http://127.0.0.1:'+proxy.address().port;process.env.NO_PROXY='';delete process.env.no_proxy;
 configureHttpDispatcher(1000);
 assert.deepEqual(await (await fetch(url+'/gzip')).json(),{ok:true,path:'/gzip'});
 assert.ok(tunnels>0);console.log('DEFERRED_FETCH_GZIP_PROXY_OK');
 const response=await fetch(url+'/slow',{signal:AbortSignal.timeout(35)});
 await assert.rejects(response.text());console.log('STREAM_ABORT_OK');
 configureHttpDispatcher(40);await assert.rejects(async()=>{await (await fetch(url+'/slow')).text()});console.log('IDLE_TIMEOUT_OK');
 process.env.HTTP_PROXY='http://127.0.0.1:'+proxy.address().port;process.env.NO_PROXY='';delete process.env.no_proxy;
 configureHttpDispatcher(1000);
 assert.deepEqual(await (await fetch(url+'/proxy')).json(),{ok:true,path:'/proxy'});assert.ok(tunnels>0);console.log('PROXY_CONNECT_OK');
 const custom=()=>Promise.resolve(new Response('custom'));globalThis.fetch=custom;configureHttpDispatcher(1000);assert.equal(globalThis.fetch,custom);console.log('CUSTOM_FETCH_PRESERVED_OK');
}finally{for(const s of sockets)s.destroy();server.close();proxy.close();}
