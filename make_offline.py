from pathlib import Path
import re
p=Path(__file__).resolve().parent
html=(p/'index.html').read_text(encoding='utf-8')
html=html.replace('<link rel="stylesheet" href="style.css">','<style>'+ (p/'style.css').read_text(encoding='utf-8')+'</style>')
for name in re.findall(r'<script src="([\w-]+\.js)"></script>',html):
    code=(p/name).read_text(encoding='utf-8').replace('</script','<\\/script')
    html=html.replace('<script src="'+name+'"></script>', '<script>\n'+code+'\n</script>')
(p/'semihub_offline.html').write_text(html,encoding='utf-8')
print('created',len(html),'bytes')
