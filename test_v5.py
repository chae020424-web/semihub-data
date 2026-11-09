import json,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parent
proc=subprocess.Popen(['python','-m','http.server','8877','--bind','127.0.0.1'],cwd=str(BASE),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1)
import atexit
atexit.register(proc.terminate)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':980})
 errors=[]
 page.on('pageerror',lambda error: errors.append(str(error)))
 page.set_content((BASE/'semihub_offline.html').read_text(encoding='utf-8'),wait_until='load')
 page.get_by_role('button',name='최신 기술·이슈').click()
 print('title',page.locator('h1').inner_text())
 print('articles',page.locator('.tech-news-row').count())
 print('first',page.locator('.tech-news-row').first.inner_text().replace('\n',' | '))
 page.screenshot(path=str(BASE/'preview_tech_news.png'),full_page=False)
 page.locator('.tech-news-title').first.click()
 print('news modal title',page.locator('.tech-modal h2').inner_text())
 print('articles educational notes',page.locator('.tech-learn-block').count())
 page.screenshot(path=str(BASE/'preview_article_explained.png'),full_page=False)
 page.locator('[data-tech-close]').click()
 page.locator('#techSearch').fill('HBM')
 print('HBM results',page.locator('.tech-news-row').count())
 page.locator('[data-tech-mode="topics"]').click()
 print('topics',page.locator('.tech-topic-card').count())
 page.locator('.tech-topic-card').first.click()
 print('topic modal',page.locator('.tech-modal h2').inner_text(),'linked',page.locator('.tech-related').count())
 page.screenshot(path=str(BASE/'preview_tech_map.png'),full_page=False)
 page.locator('.tech-related').first.click()
 print('next linked',page.locator('.tech-modal h2').inner_text())
 page.locator('[data-tech-close]').click()
 page.get_by_role('button',name='반도체 직무').click()
 print('roles',page.locator('.role-card').count())
 page.get_by_role('button',name='2026 채용공고').click()
 print('jobs heading',page.locator('h1').inner_text())
 print('errors',errors)
 assert not errors,errors
 browser.close()
print('TEST PASS')
