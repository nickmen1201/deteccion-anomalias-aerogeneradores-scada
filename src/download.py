"""Descarga solo el Parque A del zip CARE to Compare (Zenodo v6) usando peticiones HTTP por rango."""
import io
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

URL = "https://zenodo.org/records/15846963/files/CARE_To_Compare.zip?download=1"
PREFIX = "Wind Farm A/"
CHUNK = 8 * 1024 * 1024


def _get_range(start, end):
    req = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as exc:  # reintento simple ante cortes de red
            err = exc
    raise err


class HttpRangeFile:
    """Archivo de solo lectura respaldado por HTTP Range, para que zipfile lea el índice sin bajar todo."""

    def __init__(self, size):
        self.size, self.pos = size, 0

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        data = _get_range(self.pos, self.pos + n - 1)
        self.pos += len(data)
        return data


def remote_size():
    req = urllib.request.Request(URL, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch_member(info, size, dest_root):
    """Baja los bytes comprimidos de un miembro en bloques paralelos y lo descomprime localmente."""
    out = dest_root / info.filename
    if out.exists() and out.stat().st_size == info.file_size:
        return info.filename, "ya existe"
    # encabezado local: 30 bytes fijos + nombre + extra
    head = _get_range(info.header_offset, info.header_offset + 29)
    name_len = int.from_bytes(head[26:28], "little")
    extra_len = int.from_bytes(head[28:30], "little")
    start = info.header_offset + 30 + name_len + extra_len
    end = start + info.compress_size - 1
    blocks = [(s, min(s + CHUNK - 1, end)) for s in range(start, end + 1, CHUNK)]
    with ThreadPoolExecutor(8) as ex:
        raw = b"".join(ex.map(lambda b: _get_range(*b), blocks))
    data = _decompress(info, raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return info.filename, f"{len(data) / 1e6:.1f} MB"


def _decompress(info, raw):
    import zlib
    if info.compress_type == zipfile.ZIP_STORED:
        data = raw
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompressobj(-15).decompress(raw)
    else:
        raise ValueError(f"compresión no soportada: {info.compress_type}")
    if zlib.crc32(data) != info.CRC:
        raise ValueError(f"CRC inválido en {info.filename}")
    return data


def main(dest="data"):
    dest_root = Path(dest)
    size = remote_size()
    zf = zipfile.ZipFile(HttpRangeFile(size))
    members = [i for i in zf.infolist() if PREFIX in i.filename and not i.is_dir()]
    print(f"{len(members)} archivos del Parque A, {sum(i.compress_size for i in members) / 1e6:.0f} MB comprimidos")
    if "--list" in sys.argv:
        for i in members:
            print(i.filename, i.compress_size)
        return
    for i in members:
        print(*fetch_member(i, size, dest_root), flush=True)


if __name__ == "__main__":
    main()
