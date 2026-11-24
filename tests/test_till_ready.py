"""Till Ready v1 regression tests. Made-up data only. Exits non-zero on any failure.
Usage: python3 test_v2.py /abs/path/index.html OUTDIR"""
import json, sys, datetime as dt, zxingcpp, cv2
from playwright.sync_api import sync_playwright
F, OUT = sys.argv[1], sys.argv[2]
T = dt.date.today()
def d(n): return (T+dt.timedelta(days=n)).isoformat()
def at(n, h, m=0): return dt.datetime.combine(T+dt.timedelta(days=n), dt.time(h, m)).isoformat()
FAILS, PASSES = [], 0
def check(name, cond, info=''):
    global PASSES
    if cond: PASSES += 1
    else: FAILS.append(f'{name}: {info}')
def V(id, **k):
    v = dict(id=id, code='1234567890128', format='CODE128', used=False, createdAt=1); v.update(k); return v
SEED = [
 V('mp', shop='Morrisons', kind='points', mine=True, termsChecked=True, offer='1000 More Points when you spend £30', expires=d(5)),
 V('mm', shop='Morrisons', kind='moneyoff', mine=True, termsChecked=False, offer='£2 off £20', expires=d(6)),
 V('mt', shop='Morrisons', kind='moneyoff', mine=True, termsChecked=True, offer='£3 off £30', expires=d(7)),
 V('ox', shop='Morrisons', kind='points', mine=False, offer='Someone else\'s', expires=d(8)),
 V('sa', shop="Sainsbury's", kind='moneyoff', mine=True, termsChecked=True, offer='£3 off a £20 shop', expires=d(9)),
 V('un', shop='Sample Shop', offer='No type yet', expires=d(10)),
 V('lg', shop='Morrisons', offer='Legacy record', expires=d(11)),
 V('ex', shop='Morrisons', kind='points', mine=True, termsChecked=True, offer='Expired one', expires=d(-2)),
 V('ss', shop='Sample Shop', kind='moneyoff', mine=True, termsChecked=True, offer='£1 off', expires=d(12)),
 V('sp', shop='Sample Shop', kind='points', mine=True, termsChecked=True, offer='Sample points', expires=d(13)),
 V('nt', shop='Morrisons', kind='points', mine=True, offer='No terms ticked', expires=d(14)),
 V('td', shop='Morrisons', kind='points', mine=True, termsChecked=True, offer='Ends today', expires=d(0)),
 V('fm', shop='Morrisons', kind='points', mine=True, termsChecked=True, format='EAN13', code='4006381333931', offer='Different barcode type', expires=d(15)),
]
MOCK = r"""
(()=>{const KEY='__mockdb';const load=()=>JSON.parse(localStorage.getItem(KEY)||'{}');const save=o=>localStorage.setItem(KEY,JSON.stringify(o));
const L={};function emit(c){const o=load()[c]||{};(L[c]||[]).forEach(cb=>cb({docs:Object.entries(o).map(([id,x])=>({id,data:()=>x})),metadata:{fromCache:false}}))}
const db={collection:c=>({doc:id=>({set:async x=>{const o=load();o[c]=o[c]||{};o[c][id]=JSON.parse(JSON.stringify(x));save(o);setTimeout(()=>emit(c),0)},
  delete:async()=>{const o=load();if(o[c])delete o[c][id];save(o);setTimeout(()=>emit(c),0)}}),
  onSnapshot:(cb,err)=>{if(c==='shops'&&window.__failShops){setTimeout(()=>err({code:'unavailable'}),0);return ()=>{}}(L[c]=L[c]||[]).push(cb);setTimeout(()=>emit(c),0);return ()=>{}}})};
const downloads={save:async({filename,data})=>{window.__saves=(window.__saves||[]).concat([filename]);
  if(window.__declineSaves)throw {code:'declined'};
  const url=typeof data==='string'?'data:application/json;charset=utf-8,'+encodeURIComponent(data):URL.createObjectURL(data);
  const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();return {status:'saved'}}};
window.claude={use:async n=>{if(n==='db')return db;if(n==='downloads')return downloads;throw {code:'not_granted'}}};})();
"""
def confirm_img(pg):
    pg.wait_for_timeout(300)
    if pg.locator('#dImgYes').is_visible(): pg.click('#dImgYes')
def decode(path): return [x.text for x in zxingcpp.read_barcodes(cv2.imread(path))]
def run(mode):
    INIT = "window.__tillTest=1;localStorage.setItem('tillready.dlcheck','1');"
    tag = f'[{mode}] '
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, accept_downloads=True)
        ctx.add_init_script(INIT)
        if mode == 'db': ctx.add_init_script(MOCK)
        # Seed before the app's script runs (once per test browser), so no reload is needed.
        seed_js = json.dumps(SEED)
        if mode == 'db': ctx.add_init_script("if(!localStorage.getItem('__seeded')){localStorage.setItem('__mockdb',JSON.stringify({vouchers:Object.fromEntries(%s.map(v=>[v.id,v]))}));localStorage.setItem('__seeded','1')}" % seed_js)
        else: ctx.add_init_script("if(!localStorage.getItem('__seeded')){localStorage.setItem('tillready.v1',JSON.stringify(%s));localStorage.setItem('__seeded','1')}" % seed_js)
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://'+F); pg.wait_for_selector('.slip', timeout=30000); pg.wait_for_timeout(500)
        st = lambda id: pg.evaluate(f"(()=>{{const v=__tr.vouchers.find(x=>x.id==='{id}');return v?__tr.tillStatus(v):null}})()") if False else None
        def open_(id):
            pg.evaluate(f"document.querySelectorAll('.slip').forEach(b=>b.dataset.x=1)")
            pg.locator('#detail').evaluate("e=>e.hidden=true")
            pg.evaluate(f"window.__open('{id}')")
            pg.wait_for_timeout(250)
        pg.evaluate("window.__open=id=>{const s=[...document.querySelectorAll('.slip')];}")
        # use the app's own list: click the slip whose offer matches
        def open_by(offer, old=False):
            if old: pg.click('#tabOld')
            else: pg.click('#tabLive')
            pg.locator('.slip', has_text=offer).first.click(); pg.wait_for_timeout(300)
        vis = lambda sel: pg.locator(sel).is_visible()
        check(tag+'use-today alert shows', vis('#todayBan') and 'Ends today' in pg.inner_text('#todayText'), pg.inner_text('#todayText') if vis('#todayBan') else '')
        # --- eligibility matrix ---
        cases = [('1000 More Points', True, 'display', True), ('£2 off £20', False, 'remind', False), ('£3 off £30', True, 'first', True),
                 ("Someone else's", False, 'remind', False), ('£3 off a £20 shop', False, 'remind', False), ('No type yet', False, 'remind', False),
                 ('Legacy record', False, 'remind', False), ('£1 off', True, 'first', False),
                 ('No terms ticked', False, 'remind', False), ('Different barcode type', True, 'first', True)]
        for offer, bc, stat, card in cases:
            open_by(offer)
            check(tag+f'barcode shown for {offer}', vis('#dTill') == bc, vis('#dTill'))
            check(tag+f'outcome buttons for {offer}', vis('#dOutcome') == bc)
            check(tag+f'save picture button for {offer}', vis('#dSaveImg') == bc)
            check(tag+f'first-test banner for {offer}', vis('#dFirst') == (stat=='first'))
            check(tag+f'remind banner for {offer}', vis('#dRemind') == (stat=='remind'))
            if offer in ('1000 More Points','£3 off £30'): check(tag+f'card banner for {offer}', vis('#dCard') == card)
            check(tag+f'copy number only when barcode shown, {offer}', vis('#dCopy') == bc)
            pg.click('#dClose')
        # wallet: no mini barcode for remind-only or old
        minis = pg.evaluate("[...document.querySelectorAll('#list .slip')].map(s=>[s.querySelector('.offer').textContent, !s.querySelector('.mini').hidden])")
        for o, shown in minis:
            check(tag+f'wallet mini barcode for {o}', shown == (o in ('1000 More Points when you spend £30','£3 off £30','£1 off','Sample points','Different barcode type','Ends today')), shown)
        # expired: no barcode
        open_by('Expired one', old=True); check(tag+'expired hides barcode', not vis('#dTill')); check(tag+'expired hides outcome', not vis('#dOutcome')); pg.click('#dClose'); pg.click('#tabLive')
        # --- barcode on screen + saved picture, several formats incl. leading zeros ---
        for code, fmt in [('1234567890128','CODE128'),('00123456','CODE128'),('0012345678905','EAN13'),('TEST-QR-123','QR')]:
            pg.evaluate(f"""(async()=>{{const v=Object.assign({{}},__tr.vouchers.find(x=>x.id==='mp'),{{code:'{code}',format:'{fmt}'}});await __tr.persist(v)}})()"""); pg.wait_for_timeout(400)
            open_by('1000 More Points')
            pg.locator('#dTill').screenshot(path=f'{OUT}/{mode}_{fmt}_{code}.png')
            got = decode(f'{OUT}/{mode}_{fmt}_{code}.png')
            check(tag+f'on-screen {fmt} {code}', got == [code], got)
            with pg.expect_download() as dl: pg.click('#dSaveImg')
            dl.value.save_as(f'{OUT}/{mode}_saved_{fmt}_{code}.png'); got = decode(f'{OUT}/{mode}_saved_{fmt}_{code}.png')
            check(tag+f'saved picture {fmt} {code}', got == [code], got)
            check(tag+'saved filename has no voucher number', code not in dl.value.suggested_filename, dl.value.suggested_filename)
            pg.click('#dClose')
        pg.evaluate("""(async()=>{const v=Object.assign({},__tr.vouchers.find(x=>x.id==='mp'),{code:'1234567890128',format:'CODE128'});await __tr.persist(v)})()"""); pg.wait_for_timeout(300)
        # saved picture only recorded after "It's saved"
        open_by('1000 More Points')
        with pg.expect_download(): pg.click('#dSaveImg')
        pg.wait_for_timeout(300)
        if mode == 'db': check(tag+'platform save marks the picture saved', pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').imageSaved===true") and not vis('#dImgAsk'))
        else: check(tag+'not confirmed before tap', not pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').imageSaved"))
        check(tag+'file name tracked from the start', pg.evaluate("(__tr.vouchers.find(x=>x.id==='mp').imageFiles||[]).length") >= 1)
        check(tag+'preview picture present for long-press', pg.evaluate("!!document.getElementById('dImg').getAttribute('src')") and vis('#dImg'))
        if mode == 'local': pg.click('#dImgNo'); check(tag+'it-didn\'t-save shows help', vis('#dImgHelp'))
        confirm_img(pg); pg.wait_for_timeout(300)
        check(tag+'recorded after confirm', pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').imageSaved===true&&__tr.vouchers.find(x=>x.id==='mp').imageFiles.length>=1"))
        pg.click('#dClose'); check(tag+'closing clears the picture', not pg.evaluate("!!document.getElementById('dImg').getAttribute('src')"))
        open_by('1000 More Points'); pg.click('#dDel'); check(tag+'delete asks to delete picture first', 'till-ready-morrisons' in pg.inner_text('#dDelMsg'), pg.inner_text('#dDelMsg')); pg.click('#dDelNo'); pg.click('#dClose')
        if mode == 'db':
            pg.evaluate("window.__declineSaves=1"); open_by('£3 off £30') if False else None
            open_by('1000 More Points'); pg.click('#dSaveImg'); pg.wait_for_timeout(500)
            check(tag+'declined save shows the long-press help', vis('#dImgHelp'))
            check(tag+'declined save used the platform', any(x.endswith('.png') for x in pg.evaluate("window.__saves||[]")))
            pg.evaluate("window.__declineSaves=0"); pg.click('#dClose')
        # --- reminders: boundaries ---
        def slots(exp, now):
            return pg.evaluate(f"(()=>{{window.__tillNow='{now}';return __tr.reminderSlots({{expires:'{exp}'}}).map(s=>s.label.split(' · ')[0]+'@'+s.when.toISOString())}})()")
        r = slots(d(3), at(0,8)); check(tag+'3 days left before 9am: both', [x.split('@')[0] for x in r] == ['3 days before','Last day'], r)
        r = slots(d(3), at(0,10)); check(tag+'3 days left after 9am: last day only', [x.split('@')[0] for x in r] == ['Last day'], r)
        r = slots(d(1), at(0,10)); check(tag+'1 day left: last day only', [x.split('@')[0] for x in r] == ['Last day'], r)
        r = slots(d(0), at(0,7)); check(tag+'same day before 8am: last day', [x.split('@')[0] for x in r] == ['Last day'], r)
        r = slots(d(0), at(0,12)); check(tag+'same day after 8am: today reminder', [x.split('@')[0] for x in r] == ['Today'], r)
        r = slots(d(-1), at(0,12)); check(tag+'expired: none', r == [], r)
        r = slots(d(10), at(0,12)); check(tag+'10 days: both', len(r) == 2, r)
        r = slots('2027-03-31', '2027-03-27T12:00:00'); check(tag+'across clocks change: 9am local kept', r and r[0].startswith('3 days before@2027-03-28T08:00'), r)
        lab = pg.evaluate("(()=>{window.__tillNow='2027-03-27T12:00:00';return __tr.reminderSlots({expires:'2027-03-31'})[0].label})()"); check(tag+'clocks change label says 9:00', lab.endswith(', 9:00'), lab)
        r = slots(d(0), at(0,23,50)); check(tag+'same day near midnight: none', r == [], r)
        pg.evaluate("window.__tillNow=null")
        open_by('1000 More Points'); pg.click('#dRemindBtn'); pg.wait_for_timeout(200)
        hrefs = pg.locator('#dCalLinks a').evaluate_all("a=>a.map(x=>x.href)")
        check(tag+'calendar links hold no voucher number', all('1234567890128' not in h for h in hrefs) and len(hrefs) >= 1, hrefs)
        if mode == 'local':
            with pg.expect_download() as dl: pg.click('#dIcs')
            dl.value.save_as(f'{OUT}/{mode}_r.ics'); ics = open(f'{OUT}/{mode}_r.ics').read()
            check(tag+'ics has no voucher id or number', 'mp-' not in ics and '1234567890128' not in ics and ics.count('BEGIN:VEVENT') == len(hrefs), ics[:200])
        else: check(tag+'calendar file hidden inside Claude (platform doesn\'t allow .ics)', not vis('#dIcs'))
        pg.click('#dCalDone'); pg.wait_for_timeout(300); pg.click('#dClose')
        # editing expiry resets reminder
        pg.evaluate(f"(async()=>{{}})()")
        open_by('1000 More Points'); pg.click('#dEdit'); pg.wait_for_timeout(200)
        pg.fill('#fExp', d(20)); pg.locator('#form button[type=submit]').last.click(); pg.wait_for_timeout(500)
        check(tag+'changed expiry resets reminder', pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').reminder") in (None,), pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').reminder"))
        check(tag+'reminder panel opens after save', vis('#dCalPanel'))
        pg.click('#dClose')
        # --- editor: options gated ---
        pg.click('#manualBtn'); pg.wait_for_timeout(200)
        g = lambda: pg.evaluate("[...document.querySelectorAll('#fStatus input')].map(i=>(i.checked?'*':'')+(i.disabled?'-':'')+i.value).join(' ')")
        pg.fill('#fShop', 'Another Shop'); check(tag+'editor: unknown shop, no type -> remind only', g() == '-display -first *remind', g())
        pg.select_option('#fKind', 'moneyoff'); pg.check('#fMine'); check(tag+'editor: mine but terms unchecked -> remind', g() == '-display -first *remind', g())
        pg.check('#fTerms'); check(tag+'editor: terms checked -> first', g() == '-display *first remind', g())
        pg.fill('#fShop', 'Morrisons'); pg.select_option('#fKind', 'points'); check(tag+'editor: changing shop unticks terms and mine', not pg.is_checked('#fTerms') and not pg.is_checked('#fMine'))
        pg.check('#fMine'); pg.check('#fTerms'); check(tag+'editor: Morrisons points -> display', g() == '*display first remind', g())
        check(tag+'editor: card suggested', pg.evaluate("[document.getElementById('fNeedsCard').checked,document.getElementById('fCardName').value]") == [True,'More Card'])
        pg.uncheck('#fMine'); check(tag+'editor: not mine -> remind', g() == '-display -first *remind', g())
        pg.fill('#fShop', "Sainsbury's"); pg.check('#fMine'); check(tag+"editor: Sainsbury's locked", g() == '-display -first *remind', g())
        pg.uncheck('#fTerms'); pg.fill('#fShop', 'Morrisons'); check(tag+'editor: Morrisons points without terms -> remind', g() == '-display -first *remind', g()); pg.check('#fTerms')
        pg.fill('#fCode', '1234567890128'); check(tag+'new voucher: changing the number after ticking unticks terms', not pg.is_checked('#fTerms')); pg.check('#fTerms')
        pg.fill('#fShop', 'Morrisons Daily'); check(tag+'new voucher: changing the shop unticks mine', not pg.is_checked('#fMine')); pg.fill('#fShop','Morrisons'); pg.check('#fMine'); pg.check('#fTerms')
        pg.fill('#fShop', 'Morrisons'); pg.select_option('#fKind', 'points'); pg.check('#fMine'); pg.fill('#fCode', '9780201379624'); pg.select_option('#fFormat','EAN13')
        pg.check('#fTerms')
        pg.fill('#fExp', d(4)); pg.locator('#form button[type=submit]').last.click(); pg.wait_for_timeout(500)
        nv = pg.evaluate("__tr.vouchers.find(x=>x.code==='9780201379624')")
        check(tag+'new voucher saved with type/owner/status', nv and nv['kind']=='points' and nv['mine'] is True and nv['tillStatus']=='first', nv)
        check(tag+'new voucher: reminder prompt opens', vis('#dCalPanel')); pg.click('#dClose')
        # --- first test accepted: promotes that shop+type only; double tap -> one outcome ---
        open_by('Sample points'); pg.click('#dAcc'); pg.wait_for_timeout(500)
        pg.evaluate("(async()=>{const v=__tr.vouchers.find(x=>x.id==='sp');await __tr.persist(Object.assign({},v,{kind:'item',format:'EAN13',code:'9780201379624'}))})()"); pg.wait_for_timeout(500)
        pg.click('#dPromoteYes'); pg.wait_for_timeout(500)
        check(tag+'promotion approves what was accepted', pg.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'points',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
        check(tag+'promotion ignores later edits', pg.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'item',format:'EAN13',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'first')
        open_by('£1 off'); pg.evaluate("document.getElementById('dAcc').click();document.getElementById('dAcc').click()"); pg.wait_for_timeout(500)
        check(tag+'double tap logs one outcome', pg.evaluate("(__tr.vouchers.find(x=>x.id==='ss').outcomes||[]).length") == 1)
        check(tag+'promotion offered', vis('#dPromote'))
        pg.click('#dPromoteYes'); pg.wait_for_timeout(500)
        check(tag+'Sample Shop money off now display', pg.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'moneyoff',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
        check(tag+'promotion covers its barcode type only', pg.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'moneyoff',format:'EAN13',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'first')
        check(tag+'promoted class still needs terms per voucher', pg.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'moneyoff',format:'CODE128',mine:true,expires:'2099-01-01'})") == 'remind')
        check(tag+'Sample Shop money off promotion separate from points', pg.evaluate("__tr.shopRec('Sample Shop','points').format") == 'CODE128')
        # --- refused keeps voucher; change to remind applies to shop+type ---
        open_by('£3 off £30'); pg.click('#dRef'); pg.wait_for_timeout(400)
        check(tag+'refused panel', vis('#dRefPanel'))
        pg.wait_for_timeout(500); check(tag+'outcome buttons stay hidden after refusal syncs', not vis('#dOutcome'))
        mt = pg.evaluate("__tr.vouchers.find(x=>x.id==='mt')"); check(tag+'refused not used', mt['used'] is False and mt['outcomes'][-1]['result']=='refused', mt)
        pg.click('#dToRemind'); pg.wait_for_timeout(500)
        check(tag+'Morrisons money off now remind only', pg.evaluate("__tr.tillStatus({shop:'Morrisons',kind:'moneyoff',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'remind')
        check(tag+'Morrisons points still display', pg.evaluate("__tr.tillStatus({shop:'Morrisons',kind:'points',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
        pg.click('#dClose')
        # material edit unticks terms
        open_by('Different barcode type'); pg.click('#dEdit'); pg.wait_for_timeout(200)
        pg.fill('#fCode', '4006381333948'); check(tag+'changing the number unticks terms', not pg.is_checked('#fTerms')); pg.click('#eClose')
        # --- edited voucher makes its picture stale ---
        open_by('Different barcode type')
        with pg.expect_download(): pg.click('#dSaveImg')
        confirm_img(pg); pg.wait_for_timeout(300); pg.click('#dEdit'); pg.wait_for_timeout(200)
        pg.fill('#fOffer', 'Different barcode type (edited)'); pg.locator('#form button[type=submit]').last.click(); pg.wait_for_timeout(600)
        if vis('#detail'): pg.click('#dClose')
        check(tag+'edited voucher picture listed for clean-up', pg.evaluate("(__tr.vouchers.find(x=>x.id==='fm').staleFiles||[]).length===1") and 'Morrisons' in pg.inner_text('#cleanList'))
        old_name = pg.evaluate("__tr.vouchers.find(x=>x.id==='fm').staleFiles[0]")
        open_by('Different barcode type (edited)')
        with pg.expect_download(): pg.click('#dSaveImg')
        confirm_img(pg); pg.wait_for_timeout(300); pg.click('#dClose')
        check(tag+'re-saving keeps the old picture in clean-up', old_name in pg.inner_text('#cleanList'), pg.inner_text('#cleanList'))
        # pending picture after the voucher changes elsewhere
        open_by('Different barcode type (edited)')
        with pg.expect_download(): pg.click('#dSaveImg')
        pg.evaluate("(async()=>{const v=__tr.vouchers.find(x=>x.id==='fm');await __tr.persist(Object.assign({},v,{offer:'Changed on another device'}))})()"); pg.wait_for_timeout(700)
        check(tag+'changed voucher hides the pending picture', not vis('#dImgPanel'))
        check(tag+'its file goes to clean-up', pg.evaluate("(__tr.vouchers.find(x=>x.id==='fm').staleFiles||[]).length") >= 2)
        pg.click('#dClose')
        pg.evaluate("document.querySelectorAll('#cleanList [data-clean]').forEach(b=>b.click())"); pg.wait_for_timeout(600)
        # --- cleanup list after use ---
        open_by('1000 More Points')
        with pg.expect_download(): pg.click('#dSaveImg')
        confirm_img(pg); pg.wait_for_timeout(300); pg.click('#dClose')
        pg.evaluate("(async()=>{const v=__tr.vouchers.find(x=>x.id==='mp');await __tr.persist(Object.assign({},v,{used:true,usedAt:__tr.todayISO()}))})()"); pg.wait_for_timeout(500)
        check(tag+'cleanup panel lists used voucher picture', vis('#cleanPanel') and 'Morrisons' in pg.inner_text('#cleanList'))
        pg.locator('#cleanList [data-clean]').first.click(); pg.wait_for_timeout(400)
        check(tag+'cleanup tick-off clears it', not vis('#cleanPanel'))
        # --- backup and restore into a fresh "phone" ---
        with pg.expect_download() as dl: pg.click('#bkBtn')
        dl.value.save_as(f'{OUT}/{mode}_backup.json'); bk = json.load(open(f'{OUT}/{mode}_backup.json'))
        if mode == 'local':
            check(tag+'backup date not recorded until confirmed', 'Last backup: never' in pg.inner_text('#storeNote'))
            pg.click('#bkYes')
        pg.wait_for_timeout(400)
        check(tag+'backup has vouchers and shop records', len(bk['vouchers']) == len(SEED)+1 and len(bk['shops']) >= 2, (len(bk['vouchers']), len(bk['shops'])))
        check(tag+'last backup shown', 'Last backup: never' not in pg.inner_text('#storeNote'))
        pg.screenshot(path=f'{OUT}/{mode}_wallet.png', full_page=True)
        ctx2 = b.new_context(viewport={'width':390,'height':844}, accept_downloads=True)
        ctx2.add_init_script(INIT)
        if mode == 'db': ctx2.add_init_script(MOCK)
        p2 = ctx2.new_page(); e2 = []; p2.on('pageerror', lambda e: e2.append(str(e)))
        p2.goto('file://'+F); p2.wait_for_function("typeof JsBarcode!=='undefined'", timeout=30000); p2.wait_for_timeout(800)
        p2.set_input_files('#rsFile', f'{OUT}/{mode}_backup.json'); p2.wait_for_timeout(1500)
        check(tag+'restore on fresh phone', p2.evaluate("__tr.vouchers.length") == len(SEED)+1, p2.evaluate("__tr.vouchers.length"))
        check(tag+'restore brings shop records', p2.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'moneyoff',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
        p2.set_input_files('#rsFile', f'{OUT}/{mode}_backup.json'); p2.wait_for_timeout(1500)
        check(tag+'second restore adds nothing', p2.evaluate("__tr.vouchers.length") == len(SEED)+1)
        bad = {'app':'Till Ready','version':1,'vouchers':[{'id':'z1','code':'','format':'CODE128'},{'id':'z2','code':'12','format':'EAN13'},{'id':'z3','code':'1234567890128','format':'NOPE'},
               {'id':'z4','code':'1234567890128','format':'CODE128','mine':'yes'},{'id':'z5','code':'1234567890128','format':'CODE128','expires':'31/12/26'},
               {'id':'z6','code':'1234567890128','format':'CODE128','shop':'Test','kind':'points'},{'id':'z6','code':'1234567890128','format':'CODE128'},{'id':'bad id!','code':'1','format':'CODE128'},
               {'id':'z7','code':'1234567890128','format':'CODE128','expires':'2026-02-30'},{'id':'z8','code':'1234567890128','format':'CODE128','outcomes':[{'result':'maybe','at':'x'}]}],
               'shops':{"sainsbury's|moneyoff":{'name':"Sainsbury's",'kind':'moneyoff','status':'display'},'x|points':{'name':'Y','kind':'points','status':'display'},'ok shop|points':{'name':'OK Shop','kind':'points','status':'superstar'},'nf shop|points':{'name':'NF Shop','kind':'points','status':'display','basis':'x'}}}
        json.dump(bad, open(f'{OUT}/{mode}_bad.json','w')); n0 = p2.evaluate("__tr.vouchers.length")
        p2.set_input_files('#rsFile', f'{OUT}/{mode}_bad.json'); p2.wait_for_timeout(1500)
        msg = p2.inner_text('#rsMsg')
        check(tag+'malformed restore: only the valid voucher added', p2.evaluate("__tr.vouchers.length") == n0+1, (n0, p2.evaluate("__tr.vouchers.length"), msg))
        check(tag+'malformed restore reports skips', 'skipped' in msg and 'duplicate in file' in msg and 'shop only accepts originals' in msg, msg)
        check(tag+'restore rejects approval without barcode type', 'approval without barcode type' in msg and p2.evaluate("__tr.tillStatus({shop:'NF Shop',kind:'points',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'first', msg)
        check(tag+'restore rejects impossible dates and bad outcomes', 'bad date' in msg and 'bad outcomes' in msg, msg)
        check(tag+"restore can't unlock Sainsbury's", p2.evaluate("__tr.tillStatus({shop:\"Sainsbury's\",kind:'moneyoff',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'remind')
        json.dump({'app':'Till Ready','version':2,'vouchers':[]}, open(f'{OUT}/{mode}_v2.json','w'))
        p2.set_input_files('#rsFile', f'{OUT}/{mode}_v2.json'); p2.wait_for_timeout(600)
        check(tag+'newer backup version refused', p2.evaluate("__tr.vouchers.length") == n0+1)
        # open-elsewhere QR
        pg.click('#openQr'); pg.wait_for_timeout(200); pg.locator('#qrBox').screenshot(path=f'{OUT}/{mode}_qr.png')
        check(tag+'open-elsewhere QR', cv2.QRCodeDetector().detectAndDecode(cv2.imread(f'{OUT}/{mode}_qr.png'))[0] == 'https://claude.ai/artifact/7br1yJwAiLQVTruyZETDue')
        # one-time download privacy check
        ctx3 = b.new_context(viewport={'width':390,'height':844}, accept_downloads=True); ctx3.add_init_script("window.__tillTest=1;")
        if mode == 'db': ctx3.add_init_script(MOCK)
        p3 = ctx3.new_page(); e3 = []; p3.on('pageerror', lambda e: e3.append(str(e)))
        p3.goto('file://'+F); p3.wait_for_timeout(1200); p3.click('#bkBtn'); p3.wait_for_timeout(200)
        check(tag+'download asks for the privacy check first', p3.locator('#dlOv').is_visible())
        p3.click('#dlNo'); check(tag+'not now saves nothing', not p3.locator('#bkPanel').is_visible())
        p3.click('#bkBtn'); p3.wait_for_timeout(200)
        with p3.expect_download(): p3.click('#dlOk')
        p3.wait_for_timeout(400)
        if mode == 'local': check(tag+'after the check, backup goes ahead', p3.locator('#bkPanel').is_visible())
        else: check(tag+'after the check, backup goes ahead', 'Last backup: never' not in p3.inner_text('#storeNote'))
        if mode == 'db':
            ctx4 = b.new_context(viewport={'width':390,'height':844}); ctx4.add_init_script("window.__tillTest=1;window.__failShops=1;localStorage.setItem('__mockdb',JSON.stringify({shops:{'x':{name:'Sample Shop',kind:'points',key:'sample shop|points',status:'display',format:'CODE128'}}}));"); ctx4.add_init_script(MOCK)
            p4 = ctx4.new_page(); e4 = []; p4.on('pageerror', lambda e: e4.append(str(e)))
            p4.goto('file://'+F); p4.wait_for_function("typeof JsBarcode!=='undefined'", timeout=30000); p4.wait_for_timeout(800)
            check(tag+'shop records unavailable: falls back to safe list', p4.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'points',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'first')
            check(tag+'shop records unavailable: Morrisons points still from built-in list', p4.evaluate("__tr.tillStatus({shop:'Morrisons',kind:'points',format:'CODE128',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
            e3 += e4
        check(tag+'no page errors', not errs and not e2 and not e3, errs+e2+e3)
        b.close()
for m in ('local', 'db'): run(m)
print(f'{PASSES} passed, {len(FAILS)} failed')
for f in FAILS: print('FAIL', f)
sys.exit(1 if FAILS else 0)
