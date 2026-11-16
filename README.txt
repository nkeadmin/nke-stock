NKE STOCK - how to put it online and keep it updated
=====================================================

WHAT THIS IS
  A small website that shows current stock on any phone. It needs no server and no account:
  it reads the ENTRY SHEET that the website copies from your Zoho Sheet every morning at 9 AM IST.

FILES
  index.html          the app
  config.js           company name and where the stock is read from (normally no need to edit)
  xlsx.full.min.js    spreadsheet reader (SheetJS, open source)
  manifest.webmanifest, sw.js, icon-192.png, icon-512.png   make it installable on phones
  update-stock.yml.txt   the automatic Zoho copy job (step 2)
  stock.dat           created by that job; the live stock

STEP 1 - PUT IT ONLINE (free)
  Netlify:  go to https://app.netlify.com/drop  and drag this whole folder onto the page.
            You get a link like https://something.netlify.app  (sign up free to keep it; you can
            rename it or attach your own domain later).
  GitHub Pages works too: upload the files to a repository and turn on Pages in its settings.
  Any web hosting works - upload the files to a folder and open index.html.

STEP 2 - CONNECT ZOHO SHEET (stock updates by itself)
  A. In Zoho Sheet
     1. Upload the Stock Management Excel file to Zoho Sheet (once). Keep the ENTRY SHEET columns A to Z
        in the same order, with the header row containing MOVEMENT.
     2. Right-click the "ENTRY SHEET" tab > Publish (or Share > Publish > Sheet: ENTRY SHEET).
        Choose "External" (anyone with the link), turn on "Allow download", pick CSV as the format.
     3. Copy the download link.
  B. In GitHub (repository nke-stock)
     4. Settings > Secrets and variables > Actions > New repository secret.
        Name: ZOHO_SHEET_URL   Secret: paste the Zoho download link. Add secret.
     5. Add file > Create new file. Name it exactly:  .github/workflows/update-stock.yml
        Paste everything from update-stock.yml.txt (in this folder). Commit changes.
     6. Actions tab > "Update stock from Zoho Sheet" > Run workflow. After a green tick, a file
        stock.dat appears in the repository. From then on it repeats every morning at 9 AM IST on its own
        (GitHub sometimes runs it a few minutes late).
  Your staff then see the new stock the morning's stock after 9 AM (or right away after a manual Run workflow). Nobody uploads anything.
  If a run shows a red cross, open it: the message says what is wrong (link, download not allowed, wrong tab).
  To test a link on one phone: open the app, tap the gear icon, paste it, Save.

STEP 3 - GIVE THE LINK TO YOUR STAFF
  Android (Chrome): open the link, tap the three dots, "Add to Home screen" or "Install app".
  iPhone (Safari): open the link, Share, "Add to Home Screen".

UNTIL ZOHO IS CONNECTED
  The app shows the stock from the 14.10.26 workbook (marked "built-in snapshot").
  Anyone can also tap the gear icon and open the latest Excel file from their phone to see fresh figures
  (on that phone only; nothing is uploaded).

PRIVACY
  Anyone who has the website link can see the stock. Keep the link within the company, or ask your host for
  password protection (Netlify offers it on paid plans; Cloudflare Access is free for small teams).
  The published Zoho link is kept as a GitHub secret, but stock.dat on the website is public like the app.

WHAT IS COUNTED
  Motor movements are rows with a quantity in column O, gearboxes column V, gear motors column Y.
  OUT is subtracted, IN and OPENNING are added. Godown BTB is not counted, as in the workbook.
  Standard motors: HP + Pole + Mounting + Efficiency.  Special motors (Special not STD): plus Frame and Type.
  Gearbox: Model + Ratio + Frame + Mtg.  Gear motor: Model + Ratio + Frame + Make + HP + Pole.
  Spaces and capital letters are ignored when matching, exactly like the KEY columns in the workbook.
