NKE STOCK - how to put it online and keep it updated
=====================================================

WHAT THIS IS
  A small website that shows current stock on any phone. It needs no server and no account:
  it reads the ENTRY SHEET straight from your Google Sheet.

FILES
  index.html          the app
  config.js           the only file you edit: company name and the Google Sheet link
  xlsx.full.min.js    spreadsheet reader (SheetJS, open source)
  manifest.webmanifest, sw.js, icon-192.png, icon-512.png   make it installable on phones

STEP 1 - PUT IT ONLINE (free)
  Netlify:  go to https://app.netlify.com/drop  and drag this whole folder onto the page.
            You get a link like https://something.netlify.app  (sign up free to keep it; you can
            rename it or attach your own domain later).
  GitHub Pages works too: upload the files to a repository and turn on Pages in its settings.
  Any web hosting works - upload the files to a folder and open index.html.

STEP 2 - CONNECT YOUR GOOGLE SHEET (when the stock moves to Google Sheets)
  1. Open the Google Sheet. File > Share > Publish to web.
  2. In the first box choose the tab "ENTRY SHEET" (not Entire document).
     In the second box choose "Comma-separated values (.csv)". Click Publish.
  3. Copy the link it gives you (it ends with output=csv).
  4. Open config.js in Notepad, paste the link between the quotes of SHEET_CSV_URL, save.
  5. Upload config.js to the website again (on Netlify: drag the folder again, or use Deploys > drag and drop).
  The sheet must keep the same column layout as the Excel ENTRY SHEET (columns A to Z in the same order,
  with the header row containing MOVEMENT). Google refreshes a published CSV within a few minutes of an edit.
  To test a link on one phone before changing config.js: open the app, tap the gear icon, paste it, Save.

STEP 3 - GIVE THE LINK TO YOUR STAFF
  Android (Chrome): open the link, tap the three dots, "Add to Home screen" or "Install app".
  iPhone (Safari): open the link, Share, "Add to Home Screen".

UNTIL THE GOOGLE SHEET EXISTS
  The app shows the stock from the 14.10.26 workbook (marked "built-in snapshot").
  Anyone can also tap the gear icon and open the latest Excel file from their phone to see fresh figures
  (on that phone only; nothing is uploaded).

PRIVACY
  Anyone who has the website link can see the stock. Keep the link within the company, or ask your host for
  password protection (Netlify offers it on paid plans; Cloudflare Access is free for small teams).
  The published CSV link is public in the same way; it exposes only the Entry Sheet tab you publish.

WHAT IS COUNTED
  Motor movements are rows with a quantity in column O, gearboxes column V, gear motors column Y.
  OUT is subtracted, IN and OPENNING are added. Godown BTB is not counted, as in the workbook.
  Standard motors: HP + Pole + Mounting + Efficiency.  Special motors (Special not STD): plus Frame and Type.
  Gearbox: Model + Ratio + Frame + Mtg.  Gear motor: Model + Ratio + Frame + Make + HP + Pole.
  Spaces and capital letters are ignored when matching, exactly like the KEY columns in the workbook.
