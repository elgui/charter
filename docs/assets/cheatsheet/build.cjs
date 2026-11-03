// Rebuild the PDF and inspect layout. Needs Playwright and a Chromium installation.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');
(async () => {
  const docs = path.resolve(__dirname, '../..');
  const browser = await chromium.launch({headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(path.join(docs, 'cheatsheet.html')).href);
    await page.emulateMedia({media: 'print'});
    const bounds = await page.locator('.sheet').evaluateAll(nodes => nodes.map(n => ({
      height: n.clientHeight, content: n.scrollHeight,
      outside: [...n.querySelectorAll('*')].filter(c => c.getBoundingClientRect().bottom > n.getBoundingClientRect().bottom + 1).length
    })));
    if (bounds.length !== 2 || bounds.some(b => b.content > b.height + 1 || b.outside))
      throw Error('Print overflow: ' + JSON.stringify(bounds));
    // Keep exported PDFs portable: no local worktree paths in link annotations.
    await page.locator('a').evaluateAll(nodes => nodes.forEach(a => {
      a.dataset.originalHref = a.getAttribute('href');
      if (a.dataset.originalHref === 'install.md#upgrade')
        a.href = 'https://github.com/elgui/charter/blob/main/docs/install.md#upgrade';
      else a.removeAttribute('href');
    }));
    await page.pdf({path: path.join(docs, 'cheatsheet.pdf'), preferCSSPageSize: true, printBackground: true});
    await page.locator('a').evaluateAll(nodes => nodes.forEach(a => a.setAttribute('href', a.dataset.originalHref)));
    await page.emulateMedia({media: 'screen'});
    for (const width of [1200, 390]) {
      await page.setViewportSize({width, height: 1000});
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      if (overflow) throw Error(`Horizontal overflow at ${width}px`);
      if (process.env.PREVIEW_DIR) {
        fs.mkdirSync(process.env.PREVIEW_DIR, {recursive:true});
        await page.screenshot({path:path.join(process.env.PREVIEW_DIR, `cheatsheet-${width}.png`),fullPage:true});
      }
    }
    console.log('Built cheatsheet.pdf; two page containers fit; 1200px and 390px layouts fit.');
  } finally { await browser.close(); }
})().catch(e => {console.error(e); process.exitCode = 1;});
