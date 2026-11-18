// Unit-test the shipped recovery logic with a simulated network, not a browser.
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');
const html=readFileSync(require('node:path').join(__dirname,'../upstream/cp2cl/assets/web/index.html'),'utf8');
const script=html.split('<script>')[1].split('</script>')[0];
new vm.Script(script); // Check the complete shipped script as well.
const snippet=script.slice(script.indexOf('let systemMode = "unavailable";'),script.indexOf('document.getElementById("set-maintenance").addEventListener'));
function rig() {
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',hidden:id==='system-controls',disabled:false});return nodes.get(id);};
  const r={boot:'first',down:false,pending:false,reloads:0,posts:[]};
  const context=vm.createContext({AbortController,setTimeout:()=>1,clearTimeout:()=>{},
    document:{getElementById:node,querySelectorAll:()=>['set-maintenance','set-normal','set-poweroff','set-save'].map(node)},
    location:{reload:()=>r.reloads++},showToast:()=>{},
    fetch:async(url,options)=>{
      if(r.down)throw new Error('network unavailable');
      if(options.method==='POST'){r.posts.push([url,JSON.parse(options.body)]);r.pending=true;return {ok:true,json:async()=>({ok:true})};}
      if(url==='/api/system')return {ok:true,json:async()=>({supported:true,current:'protected',next_boot:'protected',boot_id:r.boot,pending:r.pending})};
      return {ok:true,json:async()=>({carlife:{session_up:false},carplay:{}})};
    }});
  vm.runInContext(snippet,context);
  return {...r,node,state:r,load:()=>vm.runInContext('loadSystemMode()',context),act:a=>vm.runInContext(`systemAction(${JSON.stringify(a)})`,context)};
}
test('initial network failure recovers without refreshing the page',async()=>{
 const r=rig();r.state.down=true;await r.load();
 assert.match(r.node('system-mode').textContent,/自动重试/);
 r.state.down=false;await r.load();
 assert.match(r.node('system-mode').textContent,/普通模式/);
 assert.equal(r.node('system-controls').hidden,false);
 assert.equal(r.node('set-maintenance').disabled,false);
 assert.equal(r.node('set-normal').disabled,true);
 assert.match(r.node('bluetooth-gate').textContent,/等待车机/);
});
test('reboot transition tolerates loss of network and reloads on a new boot',async()=>{
 const r=rig();await r.load();await r.act('maintenance');
 assert.deepEqual(r.state.posts,[['/api/system/maintenance',{confirm:true}]]);
 await r.load();assert.match(r.node('system-mode').textContent,/正在重启/);
 r.state.down=true;await r.load();assert.match(r.node('system-mode').textContent,/自动重试/);
 r.state.down=false;r.state.boot='second';r.state.pending=false;await r.load();
 assert.equal(r.state.reloads,1);
});
test('poweroff disconnect remains a shutdown message, not a failed mode read',async()=>{
 const r=rig();await r.load();await r.act('poweroff');r.state.down=true;await r.load();
 assert.match(r.node('system-mode').textContent,/关机请求已提交/);
 assert.equal(r.node('set-poweroff').disabled,true);
});
