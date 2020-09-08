#%% 导入相关库
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
import json
from geopy.distance import geodesic
import location_func
coord = location_func.coord_trans
#  爬取二手房数据

#设置请求头：包括 UA 和 Coockie

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    #'cookie': 'global_cookie=pzvz4rxn68292nbq0e7htglx91nkdfwbu7i; __utmz=147393320.1568695301.1.1.utmcsr=shbbs.fang.com|utmccn=(referral)|utmcmd=referral|utmcct=/esf~-1/538150834_538150842.htm; __utma=147393320.1476417876.1568695301.1568695301.1568771948.2; __utmc=147393320; Captcha=517779524C44434B39346B48596F65442F75734644684E497361792F6F506668563078316356784D4E785A477279484E3245617138463555314564787379623965542B4A4B7359627942413D; newhouse_user_guid=35B671E8-BF35-888C-AC78-ED09FB6489C8; newhouse_chat_guid=3262F18D-7EFB-AE4D-CC6E-D47888369019; g_sourcepage=esf_xq%5Elb_pc; __utmt_t0=1; __utmt_t1=1; __utmt_t2=1; unique_cookie=U_7eu0ocfmua6k7nyn858kd6mb727k0omb896*20; __utmb=147393320.60.10.1568771948'
}

origin_url = r"https://sh.esf.fang.com/housing/__0_39_0_0_1_0_0_0/"


#第一步：爬取小区信息
def init_dict():
    origin_dict = {'城区': '', '地区': '', '小区名称': '', '均价': '', '建筑年代': '', '建筑类型': '', '房屋总数': '', '小区位置': '', '楼栋总数': '', '物业公司': '', '开发商': '', '对口学校':'' ,'活跃度评级':'','板块评级':'' ,'物业评级':'', '教育评级':''}
    return  origin_dict


def export_block_Info(blockInfo_dict, district):
    '''导出小区信息'''
    with open(f'{district}区各小区信息.txt', 'a', encoding='utf-8') as file:
        file.write('|'.join(blockInfo_dict.values()))
        file.write('\n')


def get_location(data):
    '''获取指定地点的位置坐标信息'''
    data['位置坐标'] = [coord(addr) for addr in data['小区位置']]
    data['经度'] = data['位置坐标'].str.split(',').str[0]
    data['纬度'] = data['位置坐标'].str.split(',').str[1]
    print('已经完成位置的坐标识别处理')
    return data


def distance_cacu(data, target='人民广场'):
    '''获取小区到指定地址的直线距离'''
    target_location = eval(coord(target))
    target_location = (lambda sub:  (sub[1], sub[0]))(target_location)
    data[f'距离{target}-km'] = data.apply(lambda x: round(geodesic(
        (x['纬度'], x['经度']), target_location).km, 2), axis=1)
    print('已经完成位置间的坐标距离计算处理')
    return data


def to_df(blockInfo_dict):
    ''' 将字典转化为 DataFrame 对象'''
    dict_list = [blockInfo_dict]
    df = pd.DataFrame.from_dict(dict_list)
    if df['活跃度评级'][0]:
        df['活跃度等级'] = df['活跃度评级'].str.split(',').str[2].str.replace('属于', '')    
    coord = location_func.coord_trans #调用高德 api
    df = get_location(df)
    df = distance_cacu(df)

    return df

def get_true_url(old_url):
    '''获得正确的url'''
    # print(old_url)
    r = requests.get(url=old_url, headers=headers)
    if r'<title>跳转...</title>' in r.text:
        soup = BeautifulSoup(r.text, 'lxml')
        new_url = soup.find(name='a', attrs={'class': 'btn-redir'}).attrs['href']
        return new_url
    return old_url


def get_district_dict(url):
    '''获得区的链接信息，并存储到字典'''
    true_url = get_true_url(url)
    r =requests.get(url=true_url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    t = soup.find(name='div', attrs={'class': 'qxName'})
    district_dict = {}
    selector = "#houselist_B03_02 > div.qxName > a"

    for i in t.select(selector):
        if i.string!= '不限':
            district_dict[i.string] = r"https://sh.esf.fang.com" + i.attrs['href']
    return district_dict


def get_area_dict(url):
    '''获得目标区不同区域的 url和名称，以字典形式输出'''
    true_url = get_true_url(url)
    r = requests.get(url=true_url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    a = soup.find(name='p', attrs={'id': 'shangQuancontain', 'class': 'contain'})
    area_dict = {}
    for i in a.find_all(name='a'):
        if i.string != '不限' :
            area_dict[i.string] = r"https://sh.esf.fang.com" + i.attrs['href']
    return area_dict


def get_area_url(old_url):
    '''获得这个区域的其它 page_url'''
    # url = r'https://sh.esf.fang.com/housing/25_1646_0_0_0_0_1_0_0_0/'
    true_url = get_true_url(old_url)
    r = requests.get(url=true_url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    page_url = soup.find(name='div', attrs={'class': 'fanye gray6'})
    page_url_list = []
    page_url_list.append(old_url)
    for j in page_url.find_all(name='a'):
        if 'href' in j.attrs:
            temp_url = r'https://sh.esf.fang.com/' + j.attrs['href'][1:]
            page_url_list.append(temp_url)
    page_urls = set(page_url_list)
    return page_urls


def get_block_dict(old_url):
    '''获得某区域某一页的小区信息和url'''
    # old_url = r'https://sh.esf.fang.com/housing/25_5920_0_0_0_0_1_0_0_0/'
    true_url = get_true_url(old_url)
    r = requests.get(url=true_url, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')
    block_url_dict = {}
    for i in soup.find_all(name='a', attrs={'class': 'plotTit', 'target': '_blank'}):
        block_name = i.string
        block_url = 'https:/' + i.attrs['href'][1:]
        block_url_dict[block_name] = block_url
    return block_url_dict

def get_block_info(district, area, block_name, old_url):
    '''获得小区的目标信息'''
    block_dict = init_dict()
    # old_url = r'https://jinqinyuan.fang.com/'

    try:
        true_url = get_true_url(old_url)
        r = requests.get(url=true_url, headers=headers)
        r.encoding = 'gb2312'
        soup = BeautifulSoup(r.text, 'lxml')
        block_price = soup.find(name='span', attrs={'class': 'prib'}).string

        block_dict['城区'] = district
        block_dict['地区'] = area
        block_dict['小区名称'] = block_name
        if block_price == '暂无均价':
            print(f'{block_name}无均价数据')
            return 0
        block_dict['均价'] = block_price
        block_info = soup.find(name='div', attrs={'class': 'Rinfolist'})
        for info in block_info.select('li'):
            info = str(info)
            if re.search(r'<li.*?b>(.*?)<.*?\/b>(?:\s*<a.*>)*?(.*?)<\/.*?', info):
                infos = re.search(r'<li.*?b>(.*?)<.*?\/b>(?:\s*<a.*>)*?(.*?)<\/.*?', info)
                temp_key = infos.group(1)
                temp_value = infos.group(2)
                if temp_key in block_dict.keys():
                    block_dict[temp_key] = temp_value
            
        rank_info = soup.find(name='div', attrs={'class':'s3'})
        for info in rank_info.select('p'):
            info = str(info)
            if re.search(r'<p.*?b>(.*?)</b>.*?>(.*?)<\/.*?', info):
                infos = re.search(r'<p.*?b>(.*?)</b>.*?>(.*?)<\/.*?', info)
                temp_key = infos.group(1)
                temp_value = infos.group(2)
                if temp_key in block_dict.keys():
                    block_dict[temp_key] = temp_value

        print(f'{block_name}的信息已爬取')
        return block_dict
    except:
        return 0

def webCrawler_main(district, area='全区', url=origin_url):
    '''获取所有小区名称和链接'''

    full_data = pd.DataFrame()
    if url == origin_url:
        district_dict = get_district_dict(url)
        if district == '上海全市':
            for key, value in district_dict.items():
                print(f'开始{key}区的爬取')
                df = webCrawler_main(district = key,  area =area, url = value)
                full_data = full_data.append(df)
                print(f'{key}已爬取完毕')
        elif district in district_dict.keys():
            district_url = district_dict[district]
            print(f'开始{district}区的爬取')
            area_dict = get_area_dict(district_url)
            if area == '全区':
                for key, value in area_dict.items():
                    print(f'开始{key}地区的爬取：')
                    df = webCrawler_main(district=district, area=key, url=value)
                    full_data = full_data.append(df)
            else:
                print(f'开始{area}地区的爬取：')
                full_data = webCrawler_main(district=district, area=area, url=area_dict[area])
            print(f'{district}已爬取完毕')
        
        else:
            print(f'{district}不正确或者无数据')
        #result = full_data.reset_index()
    
    else:
        page_urls = get_area_url(url)
        for page_url in page_urls:
            block_url_dict = get_block_dict(page_url)  # 获得每个页面的所有小区名称和url
            for block_name, block_url in block_url_dict.items():
                block_dict = get_block_info(
                    district, area, block_name, block_url)
                if block_dict:
                    #export_block_Info(block_dict, district)
                    df = to_df(block_dict)
                    full_data = full_data.append(df)
        
        #result = full_data.reset_index()
        print(f'{area}已爬取完毕')
        print('--------------------------------------------------------------------')
    result = full_data.reset_index()
    return result

def file_handler(district):
    block_list = init_dict().keys()
    data = pd.read_csv(f'{district}区各小区信息.txt', sep="|")
    data.columns = block_list
    data['活跃度等级'] = data['活跃度评级'].str.split(',').str[2].str.replace('属于', '')
    data = get_location(data)
    data = distance_cacu(data)
    data.to_csv(f'{district}区各小区信息.csv', encoding='utf-8', index=False)

#%%
if __name__ == '__main__':
    district = '黄浦'
    area = '董家渡'
    data =  webCrawler_main(district, area)
    #file_handler(district)
    
