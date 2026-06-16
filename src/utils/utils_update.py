import os
import re
import json
import logging
import shutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta

from ..services import services
from .utils_path import utils_path

logger = logging.getLogger(__name__)


class UtilsUpdate:
    """软件更新管理类，负责提取内嵌更新文件、检查版本、下载更新、退出时解压覆盖"""

    def __init__(self):
        self._version = self._get_current_version()
        self._update_exe_path = None    # update.exe 在用户目录的路径
        self._download_dir = None       # 下载目录
        self._downloaded_zip = None     # 下载完成的完整 zip 路径（已合并或完整下载）

    # ------------------------------------------------------------------ #
    # 版本信息
    # ------------------------------------------------------------------ #

    def _get_current_version(self) -> str:
        """从 pyproject.toml 读取当前版本号"""
        try:
            import tomli
            with open(utils_path.pyproject_path, 'rb') as f:
                data = tomli.load(f)
            return data['project']['version']
        except Exception as e:
            logger.warning(f'读取版本号失败: {e}')
            return '0.0.0'

    # ------------------------------------------------------------------ #
    # 提取内嵌文件
    # ------------------------------------------------------------------ #

    def extract_bundled_files(self):
        """从打包资源中提取 update.exe 和 update.json 到用户目录"""
        self._download_dir = utils_path.base_user_path / 'downloads'
        self._download_dir.mkdir(parents=True, exist_ok=True)

        # 清理上次更新残留的 zip 包（update.exe unzip 已用完）
        self._cleanup_old_zips()

        if not utils_path.is_frozen():
            # 开发环境：直接使用项目根目录的文件
            self._update_exe_path = utils_path.base_user_path / 'update.exe'
            logger.info('开发环境，使用项目根目录的 update.exe')
            return

        try:
            # 提取 update.exe
            res_exe = utils_path.base_res_path / 'update.exe'
            if res_exe.exists():
                user_exe = utils_path.base_user_path / 'update.exe'
                shutil.copy2(res_exe, user_exe)
                self._update_exe_path = user_exe
                logger.info(f'已提取 update.exe 到 {user_exe}')
            else:
                logger.warning('打包资源中未找到 update.exe')

            # 提取 data/config/update.json
            res_json = utils_path.base_res_path / 'data' / 'config' / 'update.json'
            if res_json.exists():
                user_json_dir = utils_path.base_user_path / 'data' / 'config'
                user_json_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(res_json, user_json_dir / 'update.json')
                logger.info(f'已提取 update.json 到 {user_json_dir / "update.json"}')
            else:
                logger.warning('打包资源中未找到 update.json')

        except Exception as e:
            logger.error(f'提取更新文件失败: {e}')

    def _cleanup_old_zips(self):
        """清理下载目录中残留的旧 zip 包（上次更新后未清理的）"""
        if not self._download_dir or not self._download_dir.exists():
            return
        for f in self._download_dir.glob('*.zip'):
            try:
                f.unlink()
                logger.info(f'已清理旧更新包: {f.name}')
            except Exception as e:
                logger.warning(f'清理旧更新包失败 {f.name}: {e}')

    # ------------------------------------------------------------------ #
    # 间隔检查控制
    # ------------------------------------------------------------------ #

    def start_update_check(self):
        """启动后台线程检查更新（距上次检查至少间隔一天）"""
        if not utils_path.is_frozen():
            logger.info('开发环境，跳过版本更新检查')
            return

        if not self._should_check():
            logger.info('未到检查更新时间间隔（1天），跳过')
            return

        thread = threading.Thread(target=self._check_and_download, daemon=True)
        thread.start()

    def _should_check(self) -> bool:
        """判断是否需要进行版本检查（至少间隔一天）"""
        marker = utils_path.base_user_path / 'data' / 'config' / '.last_update_check'
        if not marker.exists():
            return True
        try:
            last_text = marker.read_text(encoding='utf-8').strip()
            last_dt = datetime.strptime(last_text, '%Y-%m-%d')
            return (datetime.now() - last_dt) > timedelta(days=1)
        except Exception:
            return True

    def _update_last_check_time(self):
        """记录本次检查时间"""
        marker = utils_path.base_user_path / 'data' / 'config' / '.last_update_check'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(datetime.now().strftime('%Y-%m-%d'), encoding='utf-8')

    # ------------------------------------------------------------------ #
    # 检查版本 & 下载（后台线程）
    # ------------------------------------------------------------------ #

    def _check_and_download(self):
        """在后台线程中检查版本并下载更新"""
        try:
            # 读取更新配置
            update_json = utils_path.base_user_path / 'data' / 'config' / 'update.json'
            if not update_json.exists():
                logger.warning('update.json 不存在，跳过更新检查')
                return

            with open(update_json, 'r', encoding='utf-8') as f:
                sources = json.load(f)

            for src_cfg in sources:
                source = src_cfg['source']
                url = src_cfg['url']

                logger.info(f'检查更新源 [{source}] ...')
                version_info = self._check_version(source, url)
                if version_info is None:
                    logger.info(f'更新源 [{source}] 无需更新或检查失败')
                    continue

                logger.info(f'发现新版本: {version_info["version"]} (来自 {source})')
                ok = self._download_update(source, version_info)
                if ok:
                    logger.info(f'更新下载完成（来源: {source}）')
                    break
                else:
                    logger.warning(f'从 {source} 下载失败')

        except Exception as e:
            logger.error(f'检查更新异常: {e}')
        finally:
            self._update_last_check_time()

    def _check_version(self, source: str, url: str):
        """调用 update.exe check-version 检查是否有新版本"""
        if not self._update_exe_path or not self._update_exe_path.exists():
            logger.warning('update.exe 不可用，无法检查版本')
            return None

        try:
            result = subprocess.run(
                [str(self._update_exe_path), 'check-version', '-s', source, '-u', url],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            output = result.stdout.strip()
            if not output or output == 'None':
                logger.info(f'检查版本返回空（{source}）')
                return None

            # 解析版本号  version='x.y.z'
            version_m = re.search(r"version='([\d.]+)'", output)
            if not version_m:
                logger.warning(f'无法从输出中解析版本号: {output[:200]}')
                return None

            new_ver = version_m.group(1)

            # 版本比较
            if not self._compare_versions(new_ver):
                logger.info(f'当前版本 {self._version} 已是最新')
                return None

            # 解析文件信息
            files = self._parse_files_output(output)

            return {
                'source': source,
                'version': new_ver,
                'files': files,
            }

        except subprocess.TimeoutExpired:
            logger.error('检查版本超时（30s）')
            return None
        except Exception as e:
            logger.error(f'检查版本失败: {e}')
            return None

    def _compare_versions(self, new_version: str) -> bool:
        """比较版本号，True 表示有新版本"""
        old = self._version.replace('v', '')
        new = new_version.replace('v', '')
        return new > old

    def _parse_files_output(self, output: str) -> dict:
        """
        从 VersionInfo 的文本表示中解析 files 字典
        匹配形如 'filename.zip': {'sha256': '...', 'url': '...'}
        """
        files = {}
        # 匹配文件名及其后面的 sha256 和 url
        pat = re.compile(r"'([^']+\.zip)':\s*\{[^}]*?'sha256':\s*'([^']*)'[^}]*?'url':\s*'([^']*)'")
        for m in pat.finditer(output):
            files[m.group(1)] = {'sha256': m.group(2), 'url': m.group(3)}
        return files

    def _download_update(self, source: str, version_info: dict) -> bool:
        """根据 source 类型执行下载"""
        if not self._update_exe_path or not self._update_exe_path.exists():
            return False

        self._download_dir.mkdir(parents=True, exist_ok=True)

        if source == 'github':
            return self._download_github(version_info['files'])
        elif source == 'customize':
            return self._download_customize(version_info['files'])
        else:
            logger.warning(f'未知更新源类型: {source}')
            return False

    def _download_github(self, files: dict) -> bool:
        """下载 GitHub 完整 zip 包"""
        target = None
        for name, info in files.items():
            if 'AutoGame-win-x64' in name:
                target = (name, info)
                break

        if not target:
            logger.warning('GitHub 源中未找到含 AutoGame-win-x64 的更新包')
            return False

        filename, info = target
        logger.info(f'开始下载: {filename}')
        return self._run_download('github', info['url'], filename, sha256=info.get('sha256', ''))

    def _download_customize(self, files: dict) -> bool:
        """下载 customize 源的分块文件并合并"""
        sp_files = []
        for filename, info in files.items():
            if '-sp' not in filename:
                continue
            logger.info(f'下载分块: {filename}')
            ok = self._run_download('customize', info['url'], filename, sha256=info.get('sha256', ''))
            if not ok:
                logger.error(f'分块 {filename} 下载失败')
                return False
            sp_files.append(self._download_dir / filename)

        if not sp_files:
            logger.warning('customize 源中未找到分块文件')
            return False

        # 合并分块
        logger.info('开始合并分块文件...')
        try:
            merge_result = subprocess.run(
                [str(self._update_exe_path), 'merge', '-f', str(sp_files[0])],
                capture_output=True, text=True, timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            merged_path_str = [l.strip() for l in merge_result.stdout.splitlines() if l.strip()][-1]
            if merged_path_str:
                merged = Path(merged_path_str)
                if merged.exists():
                    self._downloaded_zip = merged
                    # 清理分块文件
                    for sp in sp_files:
                        try:
                            sp.unlink()
                        except Exception:
                            pass
                    logger.info(f'合并完成: {merged}')
                    return True

            logger.error(f'合并失败: stdout={merge_result.stdout!r} stderr={merge_result.stderr!r}')
            return False

        except Exception as e:
            logger.error(f'合并分块异常: {e}')
            return False

    def _run_download(self, source: str, url: str, filename: str, sha256: str = '') -> bool:
        """调用 update.exe download 下载单个文件，支持 sha256 验证"""
        try:
            cmd = [str(self._update_exe_path), 'download',
                   '-s', source, '-u', url,
                   '-n', filename, '-d', str(self._download_dir)]
            if sha256:
                cmd += ['-sha256', sha256]
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            output = result.stdout.strip()
            # 成功时输出格式: (True, WindowsPath('...'))
            # 失败时输出: False
            if output.startswith('(True'):
                path_m = re.search(r"'([^']+)'", output)
                if path_m:
                    dl_path = Path(path_m.group(1))
                    if dl_path.exists():
                        # 只有非分块文件才直接标记为最终 zip
                        if '-sp' not in filename:
                            self._downloaded_zip = dl_path
                        return True

            logger.error(f'下载失败 [{filename}]: {output} {result.stderr}')
            return False

        except subprocess.TimeoutExpired:
            logger.error(f'下载超时 [{filename}]（300s）')
            return False
        except Exception as e:
            logger.error(f'下载异常 [{filename}]: {e}')
            return False

    # ------------------------------------------------------------------ #
    # 退出时解压覆盖
    # ------------------------------------------------------------------ #

    def apply_on_exit(self):
        """应用退出时启动 update.exe unzip -wpid，等待本进程退出后解压覆盖"""
        if not self._downloaded_zip or not self._downloaded_zip.exists():
            return

        update_exe = utils_path.base_user_path / 'update.exe'
        if not update_exe.exists():
            logger.warning('update.exe 不存在，无法执行更新解压')
            return

        pid = os.getpid()
        logger.info(
            f'启动更新解压: 压缩包={self._downloaded_zip} '
            f'目标目录={utils_path.base_user_path} '
            f'等待PID={pid}'
        )

        try:
            subprocess.Popen(
                [str(update_exe), 'unzip',
                 '-f', str(self._downloaded_zip),
                 '-d', str(utils_path.base_user_path),
                 '-wpid', str(pid)],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            logger.error(f'启动更新解压失败: {e}')
            return


