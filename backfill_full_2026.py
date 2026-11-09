"""Optional one-time search for past 2026 articles; resumable on interruption."""
from news_engine import update_news
import time
print('SEMI-HUB: 2026 historical RSS search. Stop with Ctrl+C; next launch resumes.')
for i in range(20):
    result=update_news(backfill_count=60,only_backfill=True,auto_ai=True)
    print('Batch',i+1,result,flush=True)
    if not result['backfillRemaining']:break
    if result['errors'] and result['backfillResults']==0:print('Provider inaccessible; stopped without discarding archive.');break
    time.sleep(2)
print('Done. Existing results were saved in news_archive.json')
