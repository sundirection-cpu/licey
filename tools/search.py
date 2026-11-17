import sys, json, time, urllib.request, urllib.parse, urllib.error
UA={'User-Agent':'LiceyBuilder/1.0 (educational app)'}
def api(params, host='commons.wikimedia.org'):
    params={**params,'format':'json'}
    u=f'https://{host}/w/api.php?'+urllib.parse.urlencode(params)
    for i in range(6):
        try:
            time.sleep(1.2)
            return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30))
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(5*(i+1)); continue
            raise
if __name__=='__main__':
    kind=sys.argv[1]
    for q in sys.argv[2:]:
        extra=' filetype:audio' if kind=='a' else ' filetype:bitmap'
        r=api({'action':'query','list':'search','srsearch':q+extra,'srnamespace':6,'srlimit':6})
        print('##',q)
        for h in r['query']['search']: print('  ',h['title'])
