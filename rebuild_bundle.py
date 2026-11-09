"""After editing companies.json, rebuild the data bundle used by the website."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
obj=json.loads((p/'companies.json').read_text(encoding='utf-8'))
(p/'bundle.js').write_text('window.SEMI_DB='+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
print('Rebuilt bundle.js',len(obj['companies']),'companies')
