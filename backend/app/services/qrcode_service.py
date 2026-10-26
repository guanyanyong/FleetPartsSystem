"""二维码生成服务（qrcode + Pillow）。

约定：
- 二维码内容直接使用库存件编码 `item_code`，扫码即可定位 inventory_item；
- 图片保存到 `settings.QRCODE_DIR`（默认 `uploads/qrcode/{item_code}.png`），
  该配置为相对路径时以 `backend/` 目录为基准；
- `generate_qrcode` 返回**相对 backend/ 的 Posix 路径**（如
  `uploads/qrcode/IT20261022000001.png`），直接存入 `inventory_item.qrcode_image`，
  换机器/换部署目录不受影响。
"""

from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from app.core.config import BASE_DIR, settings

__all__ = [
    "generate_item_qrcode",
    "generate_qrcode",
    "qrcode_dir",
    "qrcode_file_path",
    "to_relative_path",
]

# 二维码默认参数（见 docs/backend-requirements.md 第八节）
DEFAULT_BOX_SIZE = 10
DEFAULT_BORDER = 2

# 文件名允许的字符，防止 item_code 中出现路径分隔符导致写到目录外
_SAFE_FILENAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


def qrcode_dir(directory: str | Path | None = None) -> Path:
    """二维码目录（绝对路径）；相对路径以 backend/ 为基准。"""
    raw = Path(directory) if directory is not None else Path(settings.QRCODE_DIR)
    return raw.resolve() if raw.is_absolute() else (BASE_DIR / raw).resolve()


def _safe_filename(content: str) -> str:
    """把二维码内容转成安全文件名。"""
    filename = "".join(char for char in content if char in _SAFE_FILENAME_CHARS)
    if not filename:
        raise ValueError("二维码内容无法作为文件名")
    return filename


def qrcode_file_path(
    content: str,
    directory: str | Path | None = None,
) -> Path:
    """二维码图片绝对路径：`{QRCODE_DIR}/{content}.png`（不生成图片）。"""
    return qrcode_dir(directory) / f"{_safe_filename(content)}.png"


def to_relative_path(path: Path) -> str:
    """转成相对 backend/ 的 Posix 路径；不在 backend/ 下则返回绝对路径。"""
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def generate_qrcode(
    content: str,
    save_path: Path | str | None = None,
    *,
    box_size: int = DEFAULT_BOX_SIZE,
    border: int = DEFAULT_BORDER,
    error_correction: int = ERROR_CORRECT_M,
) -> str:
    """生成二维码图片，返回相对 backend/ 的存储路径。

    :param content: 二维码内容（库存件场景即 item_code）
    :param save_path: 保存路径；不传时按 `{QRCODE_DIR}/{content}.png` 生成
    """
    text = content.strip()
    if not text:
        raise ValueError("二维码内容不能为空")

    target = Path(save_path) if save_path is not None else qrcode_file_path(text)
    if not target.is_absolute():
        target = BASE_DIR / target
    target = target.resolve()

    qr = qrcode.QRCode(
        version=1,
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return to_relative_path(target)


def generate_item_qrcode(item_code: str) -> str:
    """按库存件编码生成二维码（内容 = item_code），返回可入库的图片路径。"""
    return generate_qrcode(item_code, qrcode_file_path(item_code))
