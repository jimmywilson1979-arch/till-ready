# Tests

`test_till_ready.py` opens `index.html` in Chrome (Playwright) twice: once in phone-only storage mode and once with a stand-in for the Claude-account database. It loads ten made-up vouchers and asserts (exits non-zero on any failure):
- eligibility per retailer and voucher type: Morrisons points (display), Morrisons money off without/with terms checked (remind/first), someone else's voucher, Sainsbury's (locked), no type, legacy record, expired;
- barcode, outcome and save buttons only appear when the voucher may be shown; no mini barcode in the wallet otherwise;
- on-screen barcode and saved picture decode exactly for Code 128 (including leading zeros), EAN-13 with leading zeros, and QR; file names hold no voucher number; a picture is only recorded after "It's saved";
- reminder boundaries: 3 days left before/after 9am, 1 day, same day before/after 8am, expired, across the March clocks change; links and .ics hold no voucher number or record id;
- changing the expiry resets the reminder; saving prompts for reminders;
- editor options gated by shop, type, ownership and terms;
- double tap logs one outcome; promotion covers one retailer and type only; "Change to Remind only" covers that retailer and type;
- used vouchers with a saved picture appear in the clean-up list;
- backup, then restore on a fresh "phone" (no duplicates on a second restore); last-backup date shown;
- open-elsewhere QR decodes to the app link; no page errors.

Run: `python3 tests/test_till_ready.py "$PWD/index.html" /tmp/tr` (needs playwright with Chrome, opencv-python, zxing-cpp). Made-up data only.
Not covered here: the real Claude-account storage and photo reading, Android downloads, Google Photos settings and calendar notifications. Those are checked on James's phone after release.
