from dataclasses import dataclass
from typing import Optional
import os
import requests


@dataclass
class ReleaseAsset:
    """Release 资源文件"""
    id: int
    name: str
    download_url: str
    size: int
    digest: Optional[str] = None
    content_type: Optional[str] = None

    @property
    def sha256(self) -> Optional[str]:
        """从 digest 字段提取 SHA256"""
        if self.digest and self.digest.startswith("sha256:"):
            return self.digest.split(":", 1)[1]
        return None


class GitHubApi:
    """GitHub API 封装"""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_latest_release(self, owner: str, repo: str) -> dict:
        """获取仓库最新的 Release 信息"""
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def get_release_assets(self, release: dict) -> list[ReleaseAsset]:
        """解析 release 中的 assets 为 ReleaseAsset 列表"""
        assets = []
        for a in release.get("assets", []):
            assets.append(ReleaseAsset(
                id=a["id"],
                name=a["name"],
                download_url=a["browser_download_url"],
                size=a["size"],
                digest=a.get("digest"),
                content_type=a.get("content_type"),
            ))
        return assets

    def find_asset_by_name(self, assets: list[ReleaseAsset], filename: str) -> Optional[ReleaseAsset]:
        """根据文件名（部分名称）查找 Asset"""
        for asset in assets:
            if filename in asset.name:
                return asset
        return None
