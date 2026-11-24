import json, sys, datetime as dt, zxingcpp, cv2
from playwright.sync_api import sync_playwright
f=sys.argv[1]; out=sys.argv[2]
today=dt.date.today()
def d(n): return (today+dt.timedelta(days=n)).isoformat()
seed=[
 {"id":"t1","code":"1234567890128","format":"CODE128","shop":"Morrisons","offer":"1000 More Points when you spend £30","expires":d(5),"used":False,"createdAt":1},
 {"id":"t2","code":"5012345678900","format":"EAN13","shop":"Sample Shop","offer":"£2 off when you spend £15","expires":d(12),"used":False,"createdAt":2},
 {"id":"t3","code":"9876543210","format":"CODE128","shop":"Sainsbury's","offer":"£3 off a £20 shop","expires":d(2),"used":False,"createdAt":3},
 {"id":"t4","code":"1111111111","format":"CODE128","shop":"Morrisons","offer":"Old one","expires":d(-3),"used":False,"createdAt":4}]
R={}
with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,accept_downloads=True)
  pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
  pg.goto('file://'+f); pg.evaluate("s=>localStorage.setItem('tillready.v1',s)",json.dumps(seed)); pg.reload(); pg.wait_for_timeout(2500)
  pg.screenshot(path=out+'_wallet.png',full_page=True)
  R['chips']=pg.locator('.slip .chips').all_inner_texts()
  # Morrisons detail
  pg.locator('.slip',has_text='1000 More Points').click(); pg.wait_for_timeout(500)
  R['card_banner']=pg.locator('#dCard').is_visible(); R['first_banner']=pg.locator('#dFirst').is_visible()
  pg.locator('#dTill').screenshot(path=out+'_bc.png'); R['bc']=[x.text for x in zxingcpp.read_barcodes(cv2.imread(out+'_bc.png'))]
  pg.screenshot(path=out+'_till.png',full_page=True)
  with pg.expect_download() as dl: pg.click('#dSaveImg')
  dl.value.save_as(out+'_saved.png'); R['saved_name']=dl.value.suggested_filename
  R['saved_bc']=[x.text for x in zxingcpp.read_barcodes(cv2.imread(out+'_saved.png'))]
  pg.click('#dRemindBtn'); pg.wait_for_timeout(200); R['cal_links']=pg.locator('#dCalLinks a').all_inner_texts()
  R['cal_href']=pg.locator('#dCalLinks a').first.get_attribute('href')
  with pg.expect_download() as dl2: pg.click('#dIcs')
  dl2.value.save_as(out+'_r.ics'); R['ics']=open(out+'_r.ics').read().count('BEGIN:VEVENT')
  pg.click('#dCalDone'); pg.wait_for_timeout(300)
  pg.click('#dRef'); pg.wait_for_timeout(300); R['ref_panel']=pg.locator('#dRefPanel').is_visible()
  pg.click('#dReasons button[data-r="wanted paper"]'); pg.wait_for_timeout(200)
  pg.screenshot(path=out+'_refused.png',full_page=True)
  pg.click('#dRefDone'); pg.wait_for_timeout(300)
  st=json.loads(pg.evaluate("localStorage.getItem('tillready.v1')")); m=[x for x in st if x['id']=='t1'][0]
  R['after_refused']={'used':m['used'],'outcomes':m.get('outcomes'),'reminder':m.get('reminder'),'imageSaved':m.get('imageSaved')}
  # first-till-test voucher: accept -> promote
  pg.locator('.slip',has_text='Sample Shop').click(); pg.wait_for_timeout(400)
  R['first_visible']=pg.locator('#dFirst').is_visible(); R['card_on_first']=pg.locator('#dCard').is_visible()
  pg.click('#dAcc'); pg.wait_for_timeout(300); R['promote']=pg.locator('#dPromote').is_visible()
  pg.click('#dPromoteYes'); pg.wait_for_timeout(300)
  R['shops']=json.loads(pg.evaluate("localStorage.getItem('tillready.shops.v1')"))
  # remind only
  pg.locator('.slip',has_text="Sainsbury").click(); pg.wait_for_timeout(400)
  R['remind']={'banner':pg.locator('#dRemind').is_visible(),'till_hidden':not pg.locator('#dTill').is_visible(),'outcome_hidden':not pg.locator('#dOutcome').is_visible(),'save_hidden':not pg.locator('#dSaveImg').is_visible()}
  pg.click('#dRemindBtn'); R['remind_cal']=pg.locator('#dCalLinks a').all_inner_texts()
  pg.screenshot(path=out+'_remind.png',full_page=True); pg.click('#dClose')
  # new voucher editor: typing shop suggests status
  pg.click('#manualBtn'); pg.wait_for_timeout(200); pg.fill('#fCode','4006381333931'); pg.select_option('#fFormat','EAN13')
  pg.fill('#fShop','Morrisons'); pg.wait_for_timeout(100)
  R['editor_suggest']=pg.evaluate("[document.querySelector('#fStatus input:checked')?.value, document.getElementById('fNeedsCard').checked, document.getElementById('fCardName').value]")
  pg.fill('#fShop','Sample Shop'); R['editor_promoted']=pg.evaluate("document.querySelector('#fStatus input:checked')?.value")
  pg.screenshot(path=out+'_editor.png',full_page=True)
  pg.click('#form button[type=submit] >> nth=-1'); pg.wait_for_timeout(300)
  st=json.loads(pg.evaluate("localStorage.getItem('tillready.v1')")); R['new_saved']=[(x['shop'],x.get('tillStatus'),x.get('needsCard')) for x in st if x['code']=='4006381333931']
  pg.click('#openQr'); pg.wait_for_timeout(200); pg.locator('#qrBox').screenshot(path=out+'_qr.png')
  im=cv2.imread(out+'_qr.png'); R['qr']=cv2.QRCodeDetector().detectAndDecode(im)[0]
  R['errors']=errs
print(json.dumps(R,indent=1,ensure_ascii=False))
