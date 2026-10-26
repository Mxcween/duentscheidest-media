"""Pull Instagram stats for @duentscheidest.mp4 into studio/data (runs every 5 min in GitHub Actions).
Token comes from the IG_TOKEN secret — never stored in the repo."""
import json, os, re, time, urllib.parse, urllib.request

API = 'https://graph.instagram.com/v23.0'
TOKEN = os.environ['IG_TOKEN']
D = os.path.join(os.path.dirname(__file__), '..', 'studio', 'data')

def get(path, **p):
    p['access_token'] = TOKEN
    with urllib.request.urlopen(f'{API}/{path}?{urllib.parse.urlencode(p)}', timeout=30) as r:
        return json.load(r)

def votes(mid):
    a = b = 0; seen = set(); url = None
    try:
        res = get(f'{mid}/comments', fields='text,username', limit=100)
        for c in res.get('data', []):
            m = re.match(r'\s*([AaBb])\b', c.get('text', ''))
            if m and c.get('username') not in seen:
                seen.add(c.get('username'))
                if m.group(1).upper() == 'A': a += 1
                else: b += 1
        return dict(a=a, b=b, lesbar=bool(res.get('data')))
    except Exception:
        return dict(a=0, b=0, lesbar=False)

def main():
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    eps = json.load(open(os.path.join(D, 'episodes.json')))
    me = get('me', fields='username,followers_count,media_count')
    media = get('me/media', fields='id,caption,timestamp,permalink,thumbnail_url,like_count,comments_count,media_type', limit=50)['data']
    reels = []
    for m in media:
        ins = {}
        try:
            ins = {x['name']: x['values'][0]['value'] for x in get(f"{m['id']}/insights", metric='views,reach,shares,saved,ig_reels_avg_watch_time')['data']}
        except Exception:
            pass
        e = eps.get(m['id'], {})
        dauer = e.get('dauer')
        watch = round(ins.get('ig_reels_avg_watch_time', 0) / 1000, 1)
        reels.append(dict(id=m['id'], serie=e.get('serie', '?'), folge=e.get('folge', ''), zeit=m['timestamp'], link=m['permalink'],
                          bild=m.get('thumbnail_url'), titel=m.get('caption', '').split('\n')[0][:90],
                          aufrufe=ins.get('views', 0), reichweite=ins.get('reach', 0), likes=m.get('like_count', 0),
                          kommentare=m.get('comments_count', 0), geteilt=ins.get('shares', 0), gespeichert=ins.get('saved', 0),
                          watch_s=watch, dauer_s=dauer, durchsicht=round(100 * watch / dauer) if dauer else None,
                          stimmen=votes(m['id'])))
    stats = dict(stand=now, konto=me['username'], follower=me['followers_count'], posts=me['media_count'], reels=reels)
    json.dump(stats, open(os.path.join(D, 'stats.json'), 'w'), ensure_ascii=False, indent=1)
    hp = os.path.join(D, 'history.json')
    hist = json.load(open(hp)) if os.path.exists(hp) else []
    hist.append(dict(t=now, f=me['followers_count'], v={r['id']: r['aufrufe'] for r in reels}))
    json.dump(hist[-2016:], open(hp, 'w'), separators=(',', ':'))   # one week at 5-min steps

if __name__ == '__main__':
    main()
