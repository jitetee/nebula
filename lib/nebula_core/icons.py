"""Icons for terminal GUIs: Nebula Mono glyphs when that font is active, Nerd Font glyphs otherwise, plain ASCII as the safe fallback.
Force one with NEBULA_ICONS=nebula|nerd|plain (same switch as Neovim)."""
import os

_N = {  # name: nerd-font codepoint (Font Awesome range)
    "folder": 0xF07B, "folder_open": 0xF07C, "file": 0xF15B, "image": 0xF1C5, "audio": 0xF1C7, "video": 0xF1C8, "archive": 0xF1C6,
    "code": 0xF1C9, "text": 0xF0F6, "pdf": 0xF1C1, "apk": 0xF17B, "up": 0xF062, "refresh": 0xF021, "new": 0xF067, "copy": 0xF0C5,
    "cut": 0xF0C4, "paste": 0xF0EA, "rename": 0xF040, "delete": 0xF1F8, "info": 0xF05A, "search": 0xF002, "home": 0xF015,
    "download": 0xF019, "music": 0xF001, "camera": 0xF030, "disk": 0xF0A0, "play": 0xF04B, "pause": 0xF04C, "next": 0xF051,
    "prev": 0xF048, "stop": 0xF04D, "volume": 0xF028, "shuffle": 0xF074, "repeat": 0xF01E, "cpu": 0xF2DB, "ram": 0xF1C0,
    "battery": 0xF240, "net": 0xF1EB, "clock": 0xF017, "branch": 0xE0A0, "cloud": 0xF0C2, "ok": 0xF00C, "bad": 0xF00D,
    "warn": 0xF071, "user": 0xF007, "key": 0xF084, "rocket": 0xF135, "star": 0xF005, "lock": 0xF023, "gear": 0xF013,
    "grid": 0xF00A, "terminal": 0xF120, "github": 0xF09B, "bolt": 0xF0E7, "sort": 0xF0DC, "eye": 0xF06E, "link": 0xF0C1,
}
_PLAIN = {
    "folder": "▸", "folder_open": "▾", "file": "-", "image": "i", "audio": "♪", "video": "v", "archive": "z", "code": "<", "text": "t",
    "pdf": "p", "apk": "a", "up": "^", "refresh": "~", "new": "+", "copy": "c", "cut": "x", "paste": "v", "rename": "r", "delete": "x",
    "info": "i", "search": "/", "home": "~", "download": "d", "music": "♪", "camera": "o", "disk": "=", "play": "▶", "pause": "=",
    "next": ">", "prev": "<", "stop": "■", "volume": "v", "shuffle": "s", "repeat": "r", "cpu": "c", "ram": "m", "battery": "b",
    "net": "n", "clock": "t", "branch": "@", "cloud": "c", "ok": "✔", "bad": "✖", "warn": "!", "user": "u", "key": "k", "rocket": "^",
    "star": "★", "lock": "l", "gear": "*", "grid": "#", "terminal": ">", "github": "g", "bolt": "!", "sort": "s", "eye": "e", "link": "l",
}
_NEBULA = {"logo": 0xE400, "bolt": 0xE401, "sparkle": 0xE402, "prompt": 0xE403, "face": 0xE404, "planet": 0xE405}


def mode():
    v = os.environ.get("NEBULA_ICONS", "auto").lower()
    if v in ("0", "off"):
        v = "plain"
    if v == "auto":
        try:
            real = os.path.realpath(os.path.expanduser("~/.termux/font.ttf"))
            v = "nebula" if real.endswith("fonts/nebula.ttf") else "nerd"
        except OSError:
            v = "nerd"
    return v if v in ("nebula", "nerd", "plain") else "nerd"


def get(name):
    m = mode()
    if m == "plain":
        return _PLAIN.get(name, "·")
    if m == "nebula" and name in _NEBULA:
        return chr(_NEBULA[name])
    if name == "logo":
        return chr(0xF135)
    if name == "sparkle":
        return chr(0xF4B8)
    return chr(_N[name]) if name in _N else _PLAIN.get(name, "·")


def for_path(path, is_dir=False, ext=None):
    """Icon name for a file/folder."""
    if is_dir:
        return "folder"
    e = (ext if ext is not None else os.path.splitext(path)[1]).lower().lstrip(".")
    if e in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "heic"):
        return "image"
    if e in ("mp3", "m4a", "flac", "wav", "ogg", "opus", "aac", "wma"):
        return "audio"
    if e in ("mp4", "mkv", "webm", "avi", "mov", "3gp"):
        return "video"
    if e in ("zip", "tar", "gz", "xz", "7z", "rar", "bz2", "tgz"):
        return "archive"
    if e in ("py", "sh", "js", "ts", "lua", "c", "h", "cpp", "java", "go", "rs", "json", "html", "css", "yml", "yaml", "toml", "kt"):
        return "code"
    if e in ("txt", "md", "log", "csv", "ini", "conf", "cfg"):
        return "text"
    if e == "pdf":
        return "pdf"
    if e == "apk":
        return "apk"
    return "file"
