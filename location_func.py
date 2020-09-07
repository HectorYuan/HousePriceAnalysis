import requests

key = 'f97ab3c8e1d8daa199ccb207d9c69100' # 输入高德的开发地图平台申请的key

def coord_trans(addr):
    api = f'https://restapi.amap.com/v3/geocode/geo?key={key}&output=json&city=上海&address={addr}'

    r = requests.get(api)

    ro = r.json()
    try:
        coordination =  ro['geocodes'][0]['location']
    except IndexError as nodata:
        coordination = 'None'

    return coordination
