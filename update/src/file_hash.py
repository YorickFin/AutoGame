import hashlib
from pathlib import Path



class FileHash:
    """文件哈希工具类"""

    @classmethod
    def hash_file(cls, file_path: str) -> str:
        """
        计算文件哈希值
        Args:
            file_path: 文件路径
        Returns:
            文件哈希值
        """
        file_path = Path(file_path)
        if not file_path.is_file():
            raise ValueError(f"{file_path} 不是有效的文件")

        with open(file_path, "rb") as f:
            file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()

    @classmethod
    def verify_file(cls, file_path: str, hash256: str) -> bool:
        """
        验证文件哈希值
        Args:
            file_path: 文件路径
            hash256: 文件哈希值
        Returns:
            验证结果
        """
        file_path = Path(file_path)
        if not file_path.is_file():
            raise ValueError(f"{file_path} 不是有效的文件")

        with open(file_path, "rb") as f:
            file_data = f.read()
        return hashlib.sha256(file_data).hexdigest() == hash256

