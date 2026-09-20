import {build} from '../build-tools/node_modules/esbuild/lib/main.js';
process.env.PI_MINIMAL_PROBE_ONLY='1';
const {opts,p,r}=await import('./build-minimal.mjs');
await build({...opts,stdin:{contents:`export * from '${p}/dist/core/http-dispatcher.js';export {builtinProviders,builtinImagesProviders} from '${p}/node_modules/@earendil-works/pi-ai/dist/providers/all.js';export {getApiProviders} from '${p}/node_modules/@earendil-works/pi-ai/dist/compat.js';`,resolveDir:p},outfile:r+'/probe-module.mjs',splitting:false});
