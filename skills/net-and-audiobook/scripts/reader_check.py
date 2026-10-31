#!/usr/bin/env python3
"""Browser regressions for long unit navigation, inline math and existing-site adapters.

All content is an original synthetic UI fixture, never private course or paper data.
"""
import argparse,copy,functools,http.server,json,shutil,tempfile,threading
from pathlib import Path
from common import read_json,write_json
from make_demo import make
from build_site import build

SKILL=Path(__file__).resolve().parents[1]
CASES=['L >> λ_D','N_D >> 1','ω_pe τ > 1','v_th = (k_B T_e / m_e)^{1/2}','T_e/T_i','R^2','B_z','\\omega_{pe} > 1']

def legacy_fixture(path,kind):
    path.mkdir(parents=True,exist_ok=True)
    shutil.copytree(SKILL/'assets/site/reading',path/'reading')
    ids=[f'u-{i:02}' for i in range(1,61)]
    links=''.join(f'<a class="toc-sub" href="#{id}">知识点 {i+1} · λ_D</a>' if kind=='course' else f'<a data-scroll-block="{id}" href="#">知识点 {i+1} · λ_D</a>' for i,id in enumerate(ids))
    blocks=''.join((f'<article class="unit" data-unit="{id}" id="{id}">' if kind=='course' else f'<article class="reading-block" data-block-id="{id}" id="{id}">')+f'<h2>知识点 {i+1} · λ_D</h2><p class="notation">'+ '，'.join(CASES)+'</p><p>这是一段原创界面测试内容，用来验证滚动跟随、可读性和符号排版。</p><code>n_e report_data.json</code><a href="source_file.json">source_file.json</a><div class="fixed-formula"><math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mi>x</mi><mn>2</mn></msup></math></div></article>' for i,id in enumerate(ids))
    if kind=='course':
        shell=f'<div class="layout"><aside class="toc"><nav class="toc-nav"><div class="toc-row"><a class="toc-link" href="#chapter">测试章节</a><div class="toc-subs">{links}</div></div></nav></aside><main class="content"><section class="intro"><h1>原创滚动测试</h1></section><section class="chapter" id="chapter">{blocks}</section></main></div>'
    else:shell=f'<main id="app"><div class="study-shell"><aside class="study-nav"><nav class="block-nav">{links}</nav></aside><section class="study-content">{blocks}</section></div></main>'
    css='*{box-sizing:border-box}body{margin:0}a{display:block}header.topbar{position:sticky;top:0;z-index:5;background:var(--panel);padding:16px;border-bottom:1px solid var(--line)}.layout{max-width:1440px;margin:auto;display:grid;grid-template-columns:290px minmax(0,1fr);align-items:start}.toc{position:sticky;overflow:auto}.unit,.reading-block{min-height:560px;border:1px solid var(--line);padding:24px;margin-bottom:18px;background:var(--panel)}.fixed-formula{margin-top:20px}code{display:block}.toc-link{padding:10px}@media(max-width:760px){.layout{display:block}.toc{position:relative!important;top:0!important;max-height:230px!important;transform:none!important;width:100%!important}.study-nav{max-height:230px!important}.content,.study-content{min-width:0}}'
    s=f'<!doctype html><html lang="zh-CN" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style><link rel="stylesheet" href="reading/reader.css"></head><body><header class="topbar">原创测试 <button id="test-theme" onclick="document.documentElement.dataset.theme=document.documentElement.dataset.theme===\'dark\'?\'light\':\'dark\'">明暗</button></header>{shell}<script defer src="reading/reader.js"></script></body></html>'
    (path/'index.html').write_text(s,encoding='utf-8')

def run(out,executable=None):
    from playwright.sync_api import sync_playwright
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    errors=[];checks=[]
    with tempfile.TemporaryDirectory(prefix='reader-fixture-') as tmp:
        root=Path(tmp);make(root/'input');p=read_json(root/'input/project.json');p['ui']['sequential']=False
        first=copy.deepcopy(p['chapters'][0]['units'][0]);p['chapters'][0]['units']=[]
        for i in range(1,37):
            u=copy.deepcopy(first);u['id']=f'u-{i:02}';u['title_zh']=f'知识点 {i} · λ_D';u['plain_zh']='，'.join(CASES)+'。'+('这是一段原创界面测试内容，用来检查阅读定位、目录跟随与行内公式。'*18);p['chapters'][0]['units'].append(u)
        write_json(root/'input/project.json',p);build(root/'input/project.json',root/'project',root/'input')
        for kind in ['course','paper']:legacy_fixture(root/kind,kind)
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*_):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                options={'headless':True}
                if executable:options['executable_path']=executable
                browser=pw.chromium.launch(**options)
                for kind in ['project','course','paper']:
                    for protocol in ['file','http']:
                        for width in [1280,390]:
                            label=f'{kind}:{protocol}:{width}'
                            ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce');page=ctx.new_page();page.set_default_timeout(8000);js=[];page.on('pageerror',lambda e:js.append(str(e)))
                            try:
                                url=(root/kind/'index.html').as_uri() if protocol=='file' else f'http://127.0.0.1:{server.server_port}/{kind}/index.html';page.goto(url)
                                page.wait_for_function('window.NBAReader && window.NBAReader.version')
                                if kind=='project':
                                    if width==390:page.locator('#menu').click()
                                    page.locator('[data-chapter]').first.click()
                                selector='.chapter:not([hidden]) .unit[data-unit]' if kind=='project' else '.unit[data-unit]' if kind=='course' else '.reading-block[data-block-id]'
                                page.wait_for_function("() => document.querySelectorAll('math.reader-math').length > 20")
                                count=page.locator(selector).count();indices=[0,count//2,count-1,3]
                                for i in indices:
                                    id=page.locator(selector).nth(i).get_attribute('id')
                                    page.evaluate("id=>{const n=document.getElementById(id);window.scrollTo({top:scrollY+n.getBoundingClientRect().top-parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--reader-offset')),behavior:'instant'})}",id)
                                    page.wait_for_function("id=>window.NBAReader.current()===id",arg=id)
                                    if width==1280:
                                        page.wait_for_function("() => {const a=document.querySelector('.reader-current'),n=document.querySelector('.reader-nav');if(!a||!n)return false;const r=a.getBoundingClientRect(),b=n.getBoundingClientRect();return r.top>=b.top && r.bottom<=b.bottom}")
                                    assert page.locator('[aria-current="location"]').count()==1,'Multiple active knowledge points'
                                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),'Page overflow'
                                if kind=='project' and width==390:page.locator('#menu').click()
                                target=page.locator('[data-reader-unit],.toc-sub,[data-scroll-block]').nth(count//3);id=target.get_attribute('data-reader-unit') or target.get_attribute('data-scroll-block') or target.get_attribute('href')[1:];target.click()
                                page.wait_for_function('id=>window.NBAReader.current()===id',arg=id)
                                page.wait_for_function("id=>Math.abs(document.getElementById(id).getBoundingClientRect().top-parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--reader-offset')))<5",arg=id)
                                first_unit=page.locator(selector).first
                                formula_sources=first_unit.locator('math.reader-math').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.mathSource)')
                                for expected in CASES:assert expected in formula_sources,f'Unformatted notation: {expected}'
                                assert first_unit.locator('math.reader-math msub').count()>=5,'Subscripts missing'
                                assert first_unit.locator('math.reader-math msup').count()>=2,'Powers missing'
                                assert first_unit.locator('math.reader-math mfrac').count()>=1,'Fractions missing'
                                if kind!='project':
                                    assert first_unit.locator('code').inner_text()=='n_e report_data.json','Code was typeset'
                                    assert first_unit.locator('a').inner_text()=='source_file.json','Filename was changed'
                                    assert first_unit.locator('.fixed-formula math').count()==1 and not first_unit.locator('.fixed-formula math').get_attribute('class'),'Original math changed'
                                for theme in ['light','dark']:
                                    page.evaluate('theme=>document.documentElement.dataset.theme=theme',theme)
                                    assert page.evaluate("getComputedStyle(document.body).color!==getComputedStyle(document.body).backgroundColor"),'Unreadable palette'
                                    assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()===getComputedStyle(document.documentElement).getPropertyValue('--reader-accent').trim()"),'Legacy theme overrides the reading palette'
                                if kind=='project':
                                    page.locator(f'[data-unit-check="{id}"]').click();page.reload();page.wait_for_function('id=>window.NBAReader.current()===id',arg=id)
                                    assert page.locator(f'[data-unit-check="{id}"]').get_attribute('aria-pressed')=='true','Completion/resume lost'
                                if protocol=='http' and width==1280:
                                    page.screenshot(path=str(out/f'{kind}-dark.png'))
                                assert not js,'JavaScript errors: '+str(js)
                                checks.append({'case':label,'passed':True,'units':count,'themes':['light','dark']})
                            except Exception as e:
                                errors.append({'case':label,'error':str(e)})
                                page.screenshot(path=str(out/f'{kind}-{protocol}-{width}-failure.png'))
                            finally:
                                ctx.close()
                                print(json.dumps({'case':label,'passed':not any(e['case']==label for e in errors)},ensure_ascii=False),flush=True)
                browser.close()
        finally:server.shutdown();server.server_close()
    report={'checks':checks,'errors':errors,'fixture':'Original synthetic content; not a deployment check of private sites.'};write_json(out/'reader-report.json',report);print(json.dumps(report,ensure_ascii=False));return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--browser-executable');a=ap.parse_args();raise SystemExit(bool(run(a.out,a.browser_executable)['errors']))
