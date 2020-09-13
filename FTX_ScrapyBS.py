#%% 导入相关库
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import location_func
coord = location_func.coord_trans #调用高德 api
import timeit
import time
from os.path import exists
from os import mkdir,remove
from pandas.errors import EmptyDataError

# 设置请求头：包括 UA 和 Coockie

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    'cookie':'{"city":"sh","csrfToken":"xFVPP0WewcU1quPpJwUtmBuv","g_sourcepage":"esf_xq^lb_pc","global_cookie":"071ua2jfroy9ui0m0emxpu16j60kf151o3n","unique_cookie":"U_071ua2jfroy9ui0m0emxpu16j60kf151o3n*4"}'
}

origin_url = r"https://sh.esf.fang.com/housing/__1_39_0_0_1_0_0_0/"


# 第一步：爬取小区信息
def init_dict():
    origin_dict = {'城区': '', '地区': '', '小区名称': '', '均价': '', '建筑年代': '', '建筑类型': '', '房屋总数': '', '小区位置': '', '楼栋总数': '', '物业公司': '', '开发商': '', '对口学校':'' ,'活跃度评级':'','板块评级':'' ,'物业评级':'', '教育评级':''}
    return  origin_dict


def export_block_Info(blockInfo_dict):
    '''导出小区信息'''
    with open(f'二手房小区信息.txt', 'a', encoding='utf-8') as file:
        file.write('|'.join(blockInfo_dict.values()))
        file.write('\n')

def file_check(path):
    if exists(path):
        print(f'{path} already exists')
    else:
        mkdir(path)
        print(f'{path} has created successfully')

def get_location(data):
    '''获取指定地点的位置坐标信息'''
    data['位置坐标'] = [coord(addr) for addr in data['小区位置']]
    data['经度'] = data['位置坐标'].str.split(',').str[0]
    data['纬度'] = data['位置坐标'].str.split(',').str[1]
    #print('已经完成位置的坐标识别处理')
    return data


def distance_cacu(data, target='人民广场'):
    '''获取小区到指定地址的直线距离'''
    target_location = eval(coord(target))
    target_location = (lambda sub:  (sub[1], sub[0]))(target_location)
    try:
        data[f'距离{target}-km'] = data.apply(lambda x: round(geodesic(
            (x['纬度'], x['经度']), target_location).km, 2), axis=1)
    except ValueError:
        data[f'距离{target}-km'] = None
    #print('已经完成位置间的坐标距离计算处理')
    return data


def data_clean(data):
    ''' 对于原始数据进行基础处理'''
    if data['活跃度评级'][0]:
        data['活跃度等级'] = data['活跃度评级'].str.extract(r'.*属于(.*)?$')
        data['活跃度分数'] = data['活跃度评级'].str.extract(r'.*为(\d{1,2}).*')
        data['活跃度趋势'] = data['活跃度评级'].str.extract(r'.*较上月活跃度(.*),.*')
    data = data.drop(columns = ['活跃度评级'])    
    data = get_location(data)
    data = distance_cacu(data)

    return data


def time_wait(seconds):
    print('倒计时开始：')
    while seconds > 0:
        print(f'倒计时: 还有{seconds}s!!')
        time.sleep(1)
        seconds -= 1
    else:
        print('结束倒计时!!')

def get_true_url(old_url):
    '''获得正确的url'''
    # print(old_url)
    r = requests.get(url=old_url, headers=headers)
    if r'<title>跳转...</title>' in r.text:
        soup = BeautifulSoup(r.text, 'lxml')
        new_url = soup.find(name='a', attrs={'class': 'btn-redir'}).attrs['href']
        if get_true_url(new_url) == new_url:
            return new_url
        else:
            print(get_true_url(new_url))
            return None
    return old_url

def get_district_dict(url):
    '''获得区的链接信息，并存储到字典'''
    if exists(r"files\district_dict.csv"):
        district_df = pd.read_csv(r"files\district_dict.csv")
        district_df = district_df[district_df['上级'] == "0"]
        district_dict = dict(zip(district_df['地区'], district_df['链接']))
    else:
        true_url = get_true_url(url)
        df = pd.DataFrame()
        r =requests.get(url=true_url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')
        t = soup.find(name='div', attrs={'class': 'qxName'})
        selector = "#houselist_B03_02 > div.qxName > a"
        links = t.select(selector)
        district_dict = {link.string:f"https://sh.esf.fang.com{link.attrs['href']}" for link in links if link.string not in ['不限','上海周边']}
        df['地区'] = list(district_dict.keys())
        df['链接'] = list(district_dict.values())
        df['上级'] = 0
        df.to_csv(r"files\district_dict.csv",encoding="utf-8",index=False)
    return district_dict


def get_area_dict(url):
    '''获得目标区不同区域的 url和名称，以字典形式输出'''
    # url = 'https://sh.esf.fang.com/housing/25__0_39_0_0_1_0_0_0/'
    
    if exists(r"files\district_dict.csv"):
        pass
    else:
        get_district_dict(origin_url)

    area_df = pd.read_csv(r"files\district_dict.csv")
    parent = area_df[area_df['链接']==url]['地区'].to_string(header=False, index=False).strip()
    if parent in list(area_df['上级']):
        area_df = area_df[area_df['上级'] == parent]
        area_dict = dict(zip(area_df['地区'],area_df['链接']))
    else:
        df = pd.DataFrame()
        true_url = get_true_url(url)
        r = requests.get(url=true_url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')
        a = soup.find(name='p', attrs={'id': 'shangQuancontain', 'class': 'contain'})
        links = a.find_all(name='a')
        area_dict = {link.string:f"https://sh.esf.fang.com{link.attrs['href']}" for link in links if link.string not in ['不限','上海周边']}
        print(area_df['地区'])
        for key in area_dict.keys():
            
            if key not in list(area_df['地区']):
                df['地区'] = list(area_dict.keys())
                df['链接'] = list(area_dict.values())
                df['上级'] = parent
        
        area_df = area_df.append(df)
        area_df.to_csv(r"files\district_dict.csv",encoding="utf-8",index=False)
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

        return block_dict
    except:
        print(f"!!! {block_name}的信息存在问题")
        return 0


def webCrawler_main(district, area='全区', url=origin_url):
    '''获取所有小区名称和链接'''
    
    region = district 
    full_data = pd.DataFrame()
    if url == origin_url:
        district_dict = get_district_dict(url)
        if district == '上海全市':
            district_sum = len(district_dict)
            for key in district_dict.keys():
                district_done = list(district_dict).index(key)
                print(f'#   准备{key}区的爬取:1> {district_done}/{district_sum}')
                df = webCrawler_main(district = key,  area =area, url = origin_url)
                full_data = full_data.append(df)
                print(f'-   {key}区已爬取完毕')

        elif district in district_dict.keys():
            district_url = district_dict[district]
            print(f'>   开始{district}区的爬取')
            area_dict = get_area_dict(district_url)
            try:
                with open(f'files\{district}区各小区信息.csv','r',encoding='utf-8') as f:
                    result = re.search(r'[\n\s]+',f.read())
                if result:
                    saved_df = pd.read_csv(f'files\{district}区各小区信息.csv', encoding='utf-8')
                    saved_set = set(saved_df['地区'])
                else:
                    print("文件数据为空")
                    remove(f'files\{district}区各小区信息.csv')
                    saved_set = set()
            except FileNotFoundError as 文件错误:
                saved_set = set()

            if area == '全区':
                area_sum = len(area_dict)
                if area_sum == len(saved_set):
                    full_data = saved_df
                    print(f'*   {district}区已有数据')
                else:                    
                    for key, value in area_dict.items():
                        area_done = list(area_dict).index(key)
                        print(f'>>  开始{key}地区的爬取:1> {area_done}/{area_sum}')
                        if key in saved_set:
                            print(f'**  {key}地区数据已存在')
                            df = saved_df[saved_df['地区']==key]
                        else:
                            df = webCrawler_main(district=district, area=key, url=value)
                        full_data = full_data.append(df)
            else:
                print(f'>>  开始{area}地区的爬取:1/1')
                if area in saved_set:
                    print(f'**  {area}地区数据已存在')
                    df = saved_df[saved_df['地区'] == area]
                    df.to_csv(f'files\{district}区{area}小区信息.csv', encoding='utf-8', index=False)
                    full_data = saved_df
                else:
                    full_data = webCrawler_main(district=district, area=area, url=area_dict[area])
            print(f'-   {district}区已爬取完毕')
            full_data.to_csv(f'files\{district}区各小区信息.csv', encoding='utf-8', index=False)
        else:
            print(f'{district}不正确或者无数据')
    
    else:
        page_urls = get_area_url(url)
        page_sum = len(page_urls)
        for page_url in page_urls:
            page_done = list(page_urls).index(page_url)+1
            print(f'>>> 进入{district}{area}地区的页面:{page_done}/{page_sum}')
            block_url_dict = get_block_dict(page_url)  # 获得每个页面的所有小区名称和url
            block_sum = len(block_url_dict)
            for block_name, block_url in block_url_dict.items():
                block_done = list(block_url_dict).index(block_name)+1
                block_dict = get_block_info(
                    district, area, block_name, block_url)
                if block_dict:
                    #export_block_Info(block_dict)
                    df = pd.DataFrame.from_dict([block_dict])
                    df = data_clean(df)
                    full_data = full_data.append(df)
                    print(f'--- {area}地区：{block_name}的信息已爬取:{block_done}/{block_sum} ')
        
        print(f'--  {area}已爬取完毕')
        time_wait(1)
    result = full_data.reset_index(drop=True)
    #result.to_csv(f'files\{district}区各小区信息.csv', encoding='utf-8', index=False)
    return result


def data_manu(district, data=None):
    if data is None:
        data = pd.read_csv(f'二手房小区信息.txt', sep="|",names=init_dict().keys())

    data = data_clean(data)
    data.to_csv(f'files\{district}区各小区信息.csv', encoding='utf-8', index=False)

#%%
if __name__ == '__main__':
    district = '宝山'
    area = '共康'
    s = timeit.timeit(stmt= "webCrawler_main(district,area).to_csv(f'files\{district}区各小区信息.csv', encoding='utf-8', index=False)",setup="from __main__ import webCrawler_main, district, area", number=1)
    #data_manu(district)
    print(s)