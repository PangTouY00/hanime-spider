import requests
import re
import os
import json
import xml.etree.ElementTree as ET
from tqdm import tqdm

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/118.0.0.0 Safari/537.36'
}



def getSearchData(name: str):
    main_url = 'https://hanime1.me/playlists'
    search_url = 'https://hanime1.me/search'

    params = {
        "query": name,
        "type": "",
        "genre": "",
        "sort": "",
        "year": "",
        "month": "",
    }
    search_resp = requests.get(url=search_url, headers=headers, params=params)
    if search_resp.status_code == 200:
        search_regex = re.compile(
            f'overlay.*?href="(?P<href>.*?)"',
            re.S)
        hrefs = []
        for href in search_regex.finditer(search_resp.text):
            hrefs.append(href.group('href'))
        search_resp.close()
        return list(set(hrefs))  # 数组查重


def getFirstPageData(hrefs):
    print(hrefs)
    download_page_hrefs = []
    for href in hrefs:
        page_resp = requests.get(url=href, headers=headers)
        if page_resp.status_code == 200:
            download_regex = re.compile(f'儲存.*?<a href="(?P<href>.*?)".*?download</i>下載', re.S)
            page_result = download_regex.search(page_resp.text)
            page_href = page_result.group('href')
            download_page_hrefs.append(page_href)
            page_resp.close()

    return download_page_hrefs


def handleDownloadAudio(hrefs):
    print(hrefs)
    download_urls = []
    infos = []
    for href in hrefs:
        download_resp = requests.get(url=href, headers=headers)
        if download_resp.status_code == 200:
            download_regex = re.compile(f'play_circle_filled.*?href="(?P<href>.*?)"', re.S)
            info_title_regex = re.compile(f'download="(?P<title>.*?)"')
            download_result = download_regex.search(download_resp.text)
            download_href = download_result.group('href')
            info_title_result = info_title_regex.search(download_resp.text)
            info_title = info_title_result.group('title')
            download_urls.append(download_href.replace('&amp;', '&'))
            infos.append({'title': info_title, 'url': download_href.replace('&amp;', '&')})
            download_resp.close()

    return infos, download_urls



def downloadAudio(name: str, path_name: str, url: str):
    try:
        # 确保目标文件夹存在，如果不存在则创建它
        target_folder = f'./assets/{name}'
        os.makedirs(target_folder, exist_ok=True)

        response = requests.get(url, stream=True, timeout=60)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1KB
        progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)

        with open(f"./assets/{name}/{path_name}.mp4", 'wb') as file:
            for data in response.iter_content(chunk_size=block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
    except Exception as e:
        print(f'下载失败:{e}')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/118.0.0.0 Safari/537.36'
}


# 获取第一集的信息
def getTvInfo(path, videoArr):
    info = {
        "title": '',  # 原标题
        "artistName": '',  # 艺术家
        "captionText": '',  # 简介
        "updateTime": '',  # 更新日期
        "tags": []
    }
    r = requests.get(url=videoArr[-1], headers=headers)
    if r.status_code == 200:
        title = re.compile(r'shareBtn-title.*?>(?P<title>.*?)</h3>').search(r.text).group('title')
        info['title'] = title
        artistName = re.compile(r'<a id="video-artist-name".*?>(?P<artistName>.*?)</a>', re.S).search(r.text).group(
            'artistName')
        info["artistName"] = artistName.lstrip().rstrip()
        captionText = re.compile(r'<div class="video-caption-text.*?>(?P<captionText>.*?)</div>', re.S).search(
            r.text).group('captionText')
        info["captionText"] = captionText
        updateTime = re.compile(r'觀看次數.*?&nbsp;&nbsp;(?P<updateTime>.*?)</div>').search(r.text).group('updateTime')
        info["updateTime"] = updateTime
        tags_regex = re.compile(
            r'<div class="single-video-tag" style="margin-bottom: 18px; font-weight: normal">.*?>(?P<tag>.*?)</a></div>',
            re.S)
        for tag in tags_regex.finditer(r.text):
            info["tags"].append(tag.group('tag'))

        r.close()
        print(info)
        with open(path, 'w', encoding='utf-8') as json_file:
            json.dump(info, json_file, ensure_ascii=False)

        # 创建 XML 元素
        root = ET.Element("tvshow")
        outline = ET.SubElement(root, "outline").text = info['title']
        # 创建 ElementTree 对象
        tree = ET.ElementTree(root)
        # 保存到 NFO 文件
        nfo_file_path = "movie.nfo"
        tree.write(nfo_file_path, encoding='utf-8', xml_declaration=True)

        return info


if __name__ == '__main__':
    while True:
        name = input('输入你要查询的番剧名（输入"退出"结束程序）: ')
        if name.lower() == '退出':
            print("程序已退出。")
            break

        search_hrefs = getSearchData(name)  # 根据番剧名抓取所有剧集 href
        if not search_hrefs:
            print("没有找到相关结果。")
            continue

        download_page_href = getFirstPageData(search_hrefs)  # 抓取剧集内下载按钮的下载链接
        if not download_page_href:
            print("没有找到下载链接。")
            continue

        infos, download_url = handleDownloadAudio(download_page_href)
        if not infos:
            print("没有找到音频信息。")
            continue

        print("找到以下音频信息：")
        for idx, info in enumerate(infos, 1):
            print(f"{idx}. 标题：{info['title']}，链接：{info['url']}")

        while True:
            choice = input("输入你想下载的音频编号（输入'全部'下载所有，输入'退出'取消下载）: ")
            if choice.lower() == '退出':
                print("取消下载。")
                break
            elif choice.lower() == '全部':
                for info in infos:
                    downloadAudio(name, info['title'], info['url'])
                print("所有音频下载完成。")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(infos):
                selected_info = infos[int(choice) - 1]
                downloadAudio(name, selected_info['title'], selected_info['url'])
                print(f"音频 {selected_info['title']} 下载完成。")
                break
            else:
                print("无效的输入，请重新输入。")
