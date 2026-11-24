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
 V('mp', shop='Morrisons', kind='points', mine=True, offer='1000 More Points when you spend £30', expires=d(5)),
 V('mm', shop='Morrisons', kind='moneyoff', mine=True, termsChecked=False, offer='£2 off £20', expires=d(6)),
 V('mt', shop='Morrisons', kind='moneyoff', mine=True, termsChecked=True, offer='£3 off £30', expires=d(7)),
 V('ox', shop='Morrisons', kind='points', mine=False, offer='Someone else\'s', expires=d(8)),
 V('sa', shop="Sainsbury's", kind='moneyoff', mine=True, termsChecked=True, offer='£3 off a £20 shop', expires=d(9)),
 V('un', shop='Sample Shop', offer='No type yet', expires=d(10)),
 V('lg', shop='Morrisons', offer='Legacy record', expires=d(11)),
 V('ex', shop='Morrisons', kind='points', mine=True, offer='Expired one', expires=d(-2)),
 V('ss', shop='Sample Shop', kind='moneyoff', mine=True, termsChecked=True, offer='£1 off', expires=d(12)),
 V('sp', shop='Sample Shop', kind='points', mine=True, termsChecked=True, offer='Sample points', expires=d(13)),
]
MOCK = r"""
(()=>{const KEY='__mockdb';const load=()=>JSON.parse(localStorage.getItem(KEY)||'{}');const save=o=>localStorage.setItem(KEY,JSON.stringify(o));
const L={};function emit(c){const o=load()[c]||{};(L[c]||[]).forEach(cb=>cb({docs:Object.entries(o).map(([id,x])=>({id,data:()=>x})),metadata:{fromCache:false}}))}
const db={collection:c=>({doc:id=>({set:async x=>{const o=load();o[c]=o[c]||{};o[c][id]=JSON.parse(JSON.stringify(x));save(o);setTimeout(()=>emit(c),0)},
  delete:async()=>{const o=load();if(o[c])delete o[c][id];save(o);setTimeout(()=>emit(c),0)}}),
  onSnapshot:(cb,err)=>{(L[c]=L[c]||[]).push(cb);setTimeout(()=>emit(c),0);return ()=>{}}})};
window.claude={use:async n=>{if(n==='db')return db;throw {code:'not_granted'}}};})();
"""
def decode(path): return [x.text for x in zxingcpp.read_barcodes(cv2.imread(path))]
def run(mode):
    INIT = "window.__tillTest=1;"
    tag = f'[{mode}] '
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, accept_downloads=True)
        ctx.add_init_script(INIT)
        if mode == 'db': ctx.add_init_script(MOCK)
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://'+F)
        if mode == 'db': pg.evaluate("s=>localStorage.setItem('__mockdb',JSON.stringify({vouchers:Object.fromEntries(JSON.parse(s).map(v=>[v.id,v]))}))", json.dumps(SEED))
        else: pg.evaluate("s=>localStorage.setItem('tillready.v1',s)", json.dumps(SEED))
        pg.reload(); pg.wait_for_timeout(2500)
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
        # --- eligibility matrix ---
        cases = [('1000 More Points', True, 'display', True), ('£2 off £20', False, 'remind', False), ('£3 off £30', True, 'first', True),
                 ("Someone else's", False, 'remind', False), ('£3 off a £20 shop', False, 'remind', False), ('No type yet', False, 'remind', False),
                 ('Legacy record', False, 'remind', False), ('£1 off', True, 'first', False)]
        for offer, bc, stat, card in cases:
            open_by(offer)
            check(tag+f'barcode shown for {offer}', vis('#dTill') == bc, vis('#dTill'))
            check(tag+f'outcome buttons for {offer}', vis('#dOutcome') == bc)
            check(tag+f'save picture button for {offer}', vis('#dSaveImg') == bc)
            check(tag+f'first-test banner for {offer}', vis('#dFirst') == (stat=='first'))
            check(tag+f'remind banner for {offer}', vis('#dRemind') == (stat=='remind'))
            if offer in ('1000 More Points','£3 off £30'): check(tag+f'card banner for {offer}', vis('#dCard') == card)
            pg.click('#dClose')
        # wallet: no mini barcode for remind-only or old
        minis = pg.evaluate("[...document.querySelectorAll('#list .slip')].map(s=>[s.querySelector('.offer').textContent, !s.querySelector('.mini').hidden])")
        for o, shown in minis:
            check(tag+f'wallet mini barcode for {o}', shown == (o in ('1000 More Points when you spend £30','£3 off £30','£1 off','Sample points')), shown)
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
        check(tag+'not recorded before confirm', not pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').imageSaved"))
        pg.click('#dImgYes'); pg.wait_for_timeout(300)
        check(tag+'recorded after confirm', pg.evaluate("__tr.vouchers.find(x=>x.id==='mp').imageSaved===true&&__tr.vouchers.find(x=>x.id==='mp').imageFiles.length===1"))
        pg.click('#dClose')
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
        r = slots('2027-03-31', '2027-03-27T12:00:00'); check(tag+'across clocks change: 9am local kept', r and r[0].startswith('3 days before@2027-03-28'), r)
        pg.evaluate("window.__tillNow=null")
        open_by('1000 More Points'); pg.click('#dRemindBtn'); pg.wait_for_timeout(200)
        hrefs = pg.locator('#dCalLinks a').evaluate_all("a=>a.map(x=>x.href)")
        check(tag+'calendar links hold no voucher number', all('1234567890128' not in h for h in hrefs) and len(hrefs) >= 1, hrefs)
        with pg.expect_download() as dl: pg.click('#dIcs')
        dl.value.save_as(f'{OUT}/{mode}_r.ics'); ics = open(f'{OUT}/{mode}_r.ics').read()
        check(tag+'ics has no voucher id or number', 'mp-' not in ics and '1234567890128' not in ics and ics.count('BEGIN:VEVENT') == len(hrefs), ics[:200])
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
        pg.fill('#fShop', 'Morrisons'); pg.select_option('#fKind', 'points'); check(tag+'editor: Morrisons points -> display', g() == '*display first remind', g())
        check(tag+'editor: card suggested', pg.evaluate("[document.getElementById('fNeedsCard').checked,document.getElementById('fCardName').value]") == [True,'More Card'])
        pg.uncheck('#fMine'); check(tag+'editor: not mine -> remind', g() == '-display -first *remind', g())
        pg.fill('#fShop', "Sainsbury's"); pg.check('#fMine'); check(tag+"editor: Sainsbury's locked", g() == '-display -first *remind', g())
        pg.fill('#fShop', 'Morrisons'); pg.select_option('#fKind', 'points'); pg.check('#fMine'); pg.fill('#fCode', '4006381333931'); pg.select_option('#fFormat','EAN13')
        pg.fill('#fExp', d(4)); pg.locator('#form button[type=submit]').last.click(); pg.wait_for_timeout(500)
        nv = pg.evaluate("__tr.vouchers.find(x=>x.code==='4006381333931')")
        check(tag+'new voucher saved with type/owner/status', nv and nv['kind']=='points' and nv['mine'] is True and nv['tillStatus']=='display', nv)
        check(tag+'new voucher: reminder prompt opens', vis('#dCalPanel')); pg.click('#dClose')
        # --- first test accepted: promotes that shop+type only; double tap -> one outcome ---
        open_by('£1 off'); pg.evaluate("document.getElementById('dAcc').click();document.getElementById('dAcc').click()"); pg.wait_for_timeout(500)
        check(tag+'double tap logs one outcome', pg.evaluate("(__tr.vouchers.find(x=>x.id==='ss').outcomes||[]).length") == 1)
        check(tag+'promotion offered', vis('#dPromote'))
        pg.click('#dPromoteYes'); pg.wait_for_timeout(500)
        check(tag+'Sample Shop money off now display', pg.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'moneyoff',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
        check(tag+'Sample Shop points unchanged', pg.evaluate("__tr.tillStatus(__tr.vouchers.find(x=>x.id==='sp'))") == 'first')
        # --- refused keeps voucher; change to remind applies to shop+type ---
        open_by('£3 off £30'); pg.click('#dRef'); pg.wait_for_timeout(400)
        check(tag+'refused panel', vis('#dRefPanel'))
        mt = pg.evaluate("__tr.vouchers.find(x=>x.id==='mt')"); check(tag+'refused not used', mt['used'] is False and mt['outcomes'][-1]['result']=='refused', mt)
        pg.click('#dToRemind'); pg.wait_for_timeout(500)
        check(tag+'Morrisons money off now remind only', pg.evaluate("__tr.tillStatus({shop:'Morrisons',kind:'moneyoff',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'remind')
        check(tag+'Morrisons points still display', pg.evaluate("__tr.tillStatus({shop:'Morrisons',kind:'points',mine:true,expires:'2099-01-01'})") == 'display')
        pg.click('#dClose')
        # --- cleanup list after use ---
        pg.evaluate("(async()=>{const v=__tr.vouchers.find(x=>x.id==='mp');await __tr.persist(Object.assign({},v,{used:true,usedAt:__tr.todayISO()}))})()"); pg.wait_for_timeout(500)
        check(tag+'cleanup panel lists used voucher picture', vis('#cleanPanel') and 'Morrisons' in pg.inner_text('#cleanList'))
        pg.locator('#cleanList [data-clean]').first.click(); pg.wait_for_timeout(400)
        check(tag+'cleanup tick-off clears it', not vis('#cleanPanel'))
        # --- backup and restore into a fresh "phone" ---
        with pg.expect_download() as dl: pg.click('#bkBtn')
        dl.value.save_as(f'{OUT}/{mode}_backup.json'); bk = json.load(open(f'{OUT}/{mode}_backup.json'))
        check(tag+'backup has vouchers and shop records', len(bk['vouchers']) == len(SEED)+1 and len(bk['shops']) >= 2, (len(bk['vouchers']), len(bk['shops'])))
        check(tag+'last backup shown', 'Last backup: never' not in pg.inner_text('#storeNote'))
        pg.screenshot(path=f'{OUT}/{mode}_wallet.png', full_page=True)
        ctx2 = b.new_context(viewport={'width':390,'height':844}, accept_downloads=True)
        ctx2.add_init_script(INIT)
        if mode == 'db': ctx2.add_init_script(MOCK)
        p2 = ctx2.new_page(); e2 = []; p2.on('pageerror', lambda e: e2.append(str(e)))
        p2.goto('file://'+F); p2.wait_for_timeout(1500)
        p2.set_input_files('#rsFile', f'{OUT}/{mode}_backup.json'); p2.wait_for_timeout(1500)
        check(tag+'restore on fresh phone', p2.evaluate("__tr.vouchers.length") == len(SEED)+1, p2.evaluate("__tr.vouchers.length"))
        check(tag+'restore brings shop records', p2.evaluate("__tr.tillStatus({shop:'Sample Shop',kind:'moneyoff',mine:true,termsChecked:true,expires:'2099-01-01'})") == 'display')
        p2.set_input_files('#rsFile', f'{OUT}/{mode}_backup.json'); p2.wait_for_timeout(1500)
        check(tag+'second restore adds nothing', p2.evaluate("__tr.vouchers.length") == len(SEED)+1)
        # open-elsewhere QR
        pg.click('#openQr'); pg.wait_for_timeout(200); pg.locator('#qrBox').screenshot(path=f'{OUT}/{mode}_qr.png')
        check(tag+'open-elsewhere QR', cv2.QRCodeDetector().detectAndDecode(cv2.imread(f'{OUT}/{mode}_qr.png'))[0] == 'https://claude.ai/artifact/7br1yJwAiLQVTruyZETDue')
        check(tag+'no page errors', not errs and not e2, errs+e2)
        b.close()
for m in ('local', 'db'): run(m)
print(f'{PASSES} passed, {len(FAILS)} failed')
for f in FAILS: print('FAIL', f)
sys.exit(1 if FAILS else 0)
