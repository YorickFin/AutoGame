# 打包为exe文件:
# cd update
# uv run pyinstaller update.spec -y
import time
import argparse
import asyncio
import ctypes
from ctypes import wintypes
from src.update_manager import UpdateManager
from src.file_hash import FileHash

update_manager = UpdateManager()


def _is_pid_alive(pid: int) -> bool:
    """检查指定 PID 的进程是否仍在运行（Windows）。"""
    if not pid or pid <= 0:
        return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # 句柄为 0：进程不存在或无权访问
        return False
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _wait_pid_exit(pid: int, poll_interval: float = 0.5):
    """轮询等待指定 PID 的进程退出。"""
    if not pid or pid <= 0:
        return
    print(f'等待父进程 (pid={pid}) 退出...')
    while _is_pid_alive(pid):
        time.sleep(poll_interval)
    print(f'父进程 (pid={pid}) 已退出，开始执行后续操作')


def main():
    parser = argparse.ArgumentParser(description='Update AutoGame')
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    unzip_parser = subparsers.add_parser('unzip', help='Unzip the latest update')
    unzip_parser.add_argument('-f', '--file_path', type=str, required=True, help='Path to the update file')
    unzip_parser.add_argument('-d', '--un_dir', type=str, default=None, help='Path to extract the update')
    unzip_parser.add_argument('-wpid', '--wait_pid', type=int, default=0, help='等待该 PID 进程退出后再执行解压（0 表示不等待）')

    split_parser = subparsers.add_parser('split', help='Split a zip file into chunks')
    split_parser.add_argument('-f', '--file_path', type=str, required=True, help='Path to the zip file')
    split_parser.add_argument('-min', '--min_chunk_size', type=int, default=89, help='Minimum chunk size (MB)')
    split_parser.add_argument('-max', '--max_chunk_size', type=int, default=99, help='Maximum chunk size (MB)')

    merge_parser = subparsers.add_parser('merge', help='Merge split zip files')
    merge_parser.add_argument('-f', '--file_path', type=str, default=None, help='Path to one of the split zip files')
    merge_parser.add_argument('-l', '--file_list', type=str, nargs='+', default=None, help='List of split zip files')

    check_time_parser = subparsers.add_parser('check-time', help='Check if time difference exceeds specified days')
    check_time_parser.add_argument('-t', '--timestamp', type=str, required=True, help='Old timestamp')
    check_time_parser.add_argument('-f', '--date_format', type=str, required=True, help='Date format')
    check_time_parser.add_argument('-d', '--diff_days', type=int, default=1, help='Difference days threshold')

    version_parser = subparsers.add_parser('check-version', help='Check for new version')
    version_parser.add_argument('-s', '--source', type=str, required=True, choices=['github', 'customize'], help='Version source')
    version_parser.add_argument('-u', '--url', type=str, required=True, help='Version URL')

    compare_version_parser = subparsers.add_parser('compare-version', help='Compare two versions')
    compare_version_parser.add_argument('-ov', '--old_version', type=str, required=True, help='Old version')
    compare_version_parser.add_argument('-nv', '--new_version', type=str, required=True, help='New version')

    download_parser = subparsers.add_parser('download', help='Download file')
    download_parser.add_argument('-s', '--source', type=str, required=True, choices=['github', 'customize'], help='Download source')
    download_parser.add_argument('-u', '--url', type=str, required=True, help='Download URL')
    download_parser.add_argument('-n', '--file_name', type=str, required=True, help='Save file name')
    download_parser.add_argument('-d', '--save_dir', type=str, default='downloads', help='Save directory')
    download_parser.add_argument('-sha256', '--sha256', type=str, default='', help='SHA256 hash for file verification')

    args = parser.parse_args()

    def handle_unzip(args):
        _wait_pid_exit(args.wait_pid)
        return update_manager.unzip(args.file_path, args.un_dir)

    def handle_split(args):
        return update_manager.split_zip(args.file_path, args.min_chunk_size, args.max_chunk_size)

    def handle_merge(args):
        return update_manager.merge_zip(args.file_path, args.file_list)

    def handle_check_time(args):
        return update_manager.check_time_diff(args.timestamp, args.date_format, args.diff_days)

    def handle_check_version(args):
        return update_manager.get_new_version(args.source, args.url)

    def handle_compare_version(args):
        return update_manager.compare_versions(args.old_version, args.new_version)


    def handle_download(args):
        result = asyncio.run(update_manager.download_file(args.source, args.url, args.file_name, args.save_dir))
        if not result:
            return False
        success, save_path = result
        if not success:
            return False
        if args.sha256:
            if not FileHash.verify_file(str(save_path), args.sha256):
                save_path.unlink(missing_ok=True)
                return False
        return result

    command_handlers = {
        'unzip': handle_unzip,
        'split': handle_split,
        'merge': handle_merge,
        'check-time': handle_check_time,
        'check-version': handle_check_version,
        'compare-version': handle_compare_version,
        'download': handle_download,
    }

    handler = command_handlers.get(args.command)
    if handler:
        result = handler(args)
        print(result)
        return result
    else:
        print(f'未知命令: {args.command}')
        return None

if __name__ == '__main__':
    main()
