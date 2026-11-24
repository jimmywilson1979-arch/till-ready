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
- terms must be ticked on every voucher, even for an approved shop and type; a different barcode type gets a first till test; changing the shop, type, number or barcode type unticks the terms;
- Sainsbury's can't be unlocked by a restored record; shop records that fail to load fall back to the built-in safe list;
- restore rejects malformed vouchers and shop records, duplicates in the file and newer backup versions, and reports what it skipped;
- the long-press picture is present after saving; "It didn't save" shows help and can still be confirmed; closing clears it; file names are tracked from the start; deleting a voucher asks for its picture to be deleted first; editing a voucher makes its picture stale and lists it for clean-up;
- the one-time Downloads privacy check comes before any download; the backup date is only recorded after confirming the file saved;
- approvals need a barcode type (restore rejects one without); promotion approves exactly what was accepted, even if the voucher is edited after; new drafts untick terms (and "mine" on a shop change) when a key detail changes after ticking;
- restore rejects impossible dates and malformed outcomes; re-saving a picture keeps older pictures in clean-up; a picture pending confirmation is dropped to clean-up if the voucher changes; outcome buttons stay hidden after a refusal syncs; use-today alert in the wallet;
- open-elsewhere QR decodes to the app link; no page errors.

Result on 24 Nov 2026: 322 passed, 0 failed, on three consecutive runs.

Run: `python3 tests/test_till_ready.py "$PWD/index.html" /tmp/tr` (needs playwright with Chrome, opencv-python, zxing-cpp). Made-up data only.
Not covered here: the real Claude-account storage and photo reading, Android downloads, Google Photos settings and calendar notifications. Those are checked on James's phone after release.
