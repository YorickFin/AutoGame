import asyncio
import re
import json
import random
import zipfile
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from .github_api import GitHubApi
from .lanzou_parser import LanzouParser
from .file_hash import FileHash

@dataclass
class VersionInfo:
    source: str
    version: Optional[str] = None
    files: dict = field(default_factory=dict)


class UpdateManager:

    CUSTOM_VERSION_PATTERN = re.compile(r'"version":"(\d+\.\d+\.\d+)"')
    FILE_INFO_PATTERN = re.compile(r'"(AutoGame.*?\.zip)"')
    SHA256_PATTERN = re.compile(r'stroke="none">"([^"]+)",')
    URL_PATTERN = re.compile(r'"url":"(.*?)"')
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    def unzip(self, zip_file_path, un_dir_path=None):
        """
            解压压缩文件
        Args:
            zip_file_path: 压缩文件路径(包含文件名)
            un_dir_path: 解压目录路径(不包含文件名, 默认为压缩文件所在目录)
        """
        try:
            zip_file_path = Path(zip_file_path)
            if not zip_file_path.exists():
                raise FileNotFoundError(f'文件 {zip_file_path} 不存在')
            if '.zip' not in zip_file_path.suffix:
                raise ValueError(f'文件 {zip_file_path} 不是zip压缩文件')

            if un_dir_path is not None:
                un_dir_path = Path(un_dir_path)
            else:
                un_dir_path = zip_file_path.parent / zip_file_path.stem
            un_dir_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(un_dir_path)
            return True
        except Exception:
            return False

    def split_zip(self, zip_file_path, min_chunk_size=89, max_chunk_size=99):
        """
            分割压缩文件
        Args:
            zip_file_path: 压缩文件路径(包含文件名)
            min_chunk_size: 最小分块大小(MB)
            max_chunk_size: 最大分块大小(MB)
        Returns:
            dict[str, str]: key 为文件名, value 为文件sha256值
        """
        file_path = Path(zip_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f'文件 {file_path} 不存在')
        if '.zip' not in file_path.suffix:
            raise ValueError(f'文件 {file_path} 不是zip压缩文件')

        result = {
            "version": '0.0.1'
        }

        # 创建目录
        dir_path = file_path.parent / file_path.stem
        dir_path.mkdir(parents=True, exist_ok=True)

        # 分块大小
        min_chunk_size = 1024 * 1024 * min_chunk_size  # 80MB
        max_chunk_size = 1024 * 1024 * max_chunk_size  # 95MB

        with open(zip_file_path, 'rb') as f:
            serialNumber = 1
            while True:
                # 随机生成 80MB-95MB 大小的数据块
                data = f.read(random.randint(min_chunk_size, max_chunk_size))
                if not data:
                    break
                # 保存数据块到文件
                with open(f'{dir_path}\\{file_path.stem}-sp{serialNumber}.zip', 'ab') as f2:
                    f2.write(data)
                result[f'{file_path.stem}-sp{serialNumber}.zip'] = None
                serialNumber += 1

        # 计算sha256值
        for file_name in result:
            if file_name == 'version':
                continue
            result[file_name] = {
                'sha256': FileHash.hash_file(f'{dir_path}\\{file_name}'),
                'url': ''
            }

        with open(f'{dir_path}\\version.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        return result

    def merge_zip(self, zip_file_path=None, zip_file_list=None):
        """
            合并压缩文件
        Args:
            zip_file_path: 压缩文件路径(包含文件名)
            zip_file_list: 压缩文件列表
        """
        def get_zip_file_list(file_path):
            """
                获取压缩文件列表
            Args:
                file_path: 文件路径
            Returns:
                list[str]: 文件列表
            """
            zip_file_list = []
            prefix = file_path.stem.split('-sp')[0]
            file_list = file_path.parent.iterdir()
            for item in file_list:
                if item.suffix == '.zip' and '-sp' in item.stem and \
                    item.stem.startswith(prefix):
                    zip_file_list.append(item)

            return zip_file_list

        if zip_file_path is None and zip_file_list is None:
            raise ValueError('zip_file_path 和 zip_file_list 必须提供一个')

        if zip_file_path:
            zip_file_path = Path(zip_file_path)
            if not zip_file_path.exists():
                raise FileNotFoundError(f'文件 {zip_file_path} 不存在')
            else:
                if '.zip' not in zip_file_path.suffix or '-sp' not in zip_file_path.stem:
                    raise ValueError(f'文件 {zip_file_path} 必须是zip压缩文件且包含分块信息')
                zip_file_list = get_zip_file_list(zip_file_path)

        try:
            zip_file_list.sort(key=lambda x: int(x.stem.split('-sp')[1].replace('.zip', '')))
            if str(zip_file_list[0]).split('-sp')[1].replace('.zip', '') != '1':
                raise ValueError('分块文件不完整，缺失第一个分块文件')
            if str(zip_file_list[-1]).split('-sp')[1].replace('.zip', '') != str(len(zip_file_list)):
                raise ValueError('分块文件不完整或不是连续的')

            file_data = bytearray()
            for file in zip_file_list:
                with open(file, 'rb') as f:
                    file_data.extend(f.read())

            result = str(zip_file_list[0]).split('-sp')[0]
            with open(result, 'wb') as f:
                f.write(file_data)

            # 删除分块文件
            for file in zip_file_list:
                file.unlink()

            return result

        except Exception as e:
            raise ValueError(f'合并压缩文件时出错: {e}')

    def check_time_diff(self, old_timestamp: str, date_format: str, diff_days: int = 1) -> bool:
        """
        检查时间差是否超过1天
        Args:
            old_timestamp: 旧时间戳
            date_format: 时间格式 '%Y_%m_%d__%H_%M_%S'
            diff_days: 时间差天数
        Returns:
            bool: 是否超过指定天数
        """
        old_datetime = datetime.strptime(old_timestamp, date_format)
        new_timestamp = datetime.now().strftime(date_format)
        new_datetime = datetime.strptime(new_timestamp, date_format)

        delta = new_datetime - old_datetime
        return delta > timedelta(days=diff_days)

    def get_new_version(self, source: str, url: str) -> Optional[VersionInfo]:
        """
        检查是否有新的版本
        Args:
            source: 版本来源
            url: 版本URL
        Returns:
            VersionInfo: 版本信息，解析失败返回 None
        """
        try:
            if source == 'github':
                return self._parse_github_response(url)
            elif source == 'customize':
                return self._parse_customize_response(url)
        except requests.RequestException:
            return None

    def compare_versions(self, old_version: str, new_version: str) -> bool:
        """
        对比版本号
        Args:
            old_version: 旧版本号 格式: v1.0.0 或 1.0.0
            new_version: 新版本号 格式: v1.0.0 或 1.0.0
        Returns:
            bool: 是否有新版本
        """
        old_version = old_version.replace('v', '')
        new_version = new_version.replace('v', '')
        return new_version > old_version



    def _parse_github_response(self, url: str) -> Optional[VersionInfo]:
        """解析 GitHub 页面响应"""
        items = url.split('/')
        indx = items.index('github.com')
        if len(items) >= indx + 3:
            owner, repo = items[indx + 1], items[indx + 2]
        else:
            raise ValueError('无效的 URL, 示例: https://github.com/owner/repo')

        github_api = GitHubApi()
        release = github_api.get_latest_release(owner, repo)
        assets = github_api.get_release_assets(release)

        files = {}
        for asset in assets:
            files[asset.name] = {'sha256': asset.sha256, 'url': asset.download_url}

        return VersionInfo(
            source='github',
            version=release['tag_name'].replace('v', ''),
            files=files
        )

    def _parse_customize_response(self, url: str) -> Optional[VersionInfo]:
        """解析自定义 JSON 响应"""
        response = requests.get(url, timeout=10, headers=self.HEADERS)
        response.raise_for_status()
        text = response.text

        version_match = self.CUSTOM_VERSION_PATTERN.search(text)
        if not version_match:
            return None

        files = {}
        file_names = self.FILE_INFO_PATTERN.findall(text)
        sha256_values = self.SHA256_PATTERN.findall(text)
        url_values = self.URL_PATTERN.findall(text)

        for i, filename in enumerate(file_names):
            if i < len(sha256_values) and i < len(url_values):
                files[filename] = {'sha256': sha256_values[i], 'url': url_values[i]}

        return VersionInfo(
            source='customize',
            version=version_match.group(1),
            files=files
        )

    async def download_file(self, source: str, url: str, file_name: str, save_dir: str='downloads') -> bool:
        """
        下载文件（异步）
        Args:
            source: 下载来源
            url: 下载URL
            file_name: 保存文件名
            save_dir: 保存目录路径
        Returns:
            tuple: (bool, Path) 是否下载成功，保存路径
        """
        try:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)

            if source == 'github':
                save_path = save_dir / file_name
                file_size = save_path.stat().st_size if save_path.exists() else 0
                headers = {'User-Agent': self.HEADERS['User-Agent']}
                mode = 'wb'
                if file_size > 0:
                    headers['Range'] = f'bytes={file_size}-'
                    mode = 'ab'
                return await asyncio.to_thread(
                    self._sub_download_file, url, headers, save_path, mode
                ), save_path

            elif source == 'customize':
                parser = LanzouParser(url=url, password='')
                for _ in range(3):
                    success, _, direct_url = parser.parse()
                    if success:
                        break
                else:
                    raise Exception("解析失败3次")

                save_path = save_dir / file_name
                file_size = save_path.stat().st_size if save_path.exists() else 0
                headers = {'User-Agent': self.HEADERS['User-Agent']}
                mode = 'wb'
                if file_size > 0:
                    headers['Range'] = f'bytes={file_size}-'
                    mode = 'ab'
                return await asyncio.to_thread(
                    self._sub_download_file, direct_url, headers, save_path, mode
                ), save_path
        except Exception:
            return False

    def _sub_download_file(self, url: str, headers: dict, save_path: Path, mode: str) -> bool:
        """
        下载文件（同步，内部使用）
        Args:
            url: 文件URL
            headers: 请求头
            save_path: 保存路径
            mode: 写入模式
        Returns:
            bool: 是否下载成功
        """
        try:
            with requests.get(url, timeout=(5, 30), stream=True, headers=headers) as resp:
                resp.raise_for_status()
                with open(save_path, mode) as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
            return True
        except Exception:
            return False
