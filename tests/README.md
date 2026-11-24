# Tests

`test_v1.py` opens `index.html` in Chrome (Playwright) in phone-only storage mode, loads four made-up vouchers, and checks:
- status chips in the wallet; card-first banner; first-till-test and remind-only screens;
- the on-screen barcode and the saved picture both decode to the exact made-up number;
- reminder links (3 days before 9am, last day 8am) and the .ics file;
- Refused keeps the voucher and logs the reason; Accepted on a first till test offers to promote the shop;
- the editor suggests the status from the shop record; the open-elsewhere QR decodes to the app link.

Run: `python3 tests/test_v1.py "$PWD/index.html" /tmp/tr` (needs playwright, opencv-python, zxing-cpp). Made-up data only.
