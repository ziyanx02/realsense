import glob
import mmap
import os
import struct
import numpy as np

WIDTH = 640
HEIGHT = 480
CHANNELS = 3
IMG_SIZE = WIDTH * HEIGHT * CHANNELS
SEQ_SIZE = 8
SERIAL_SIZE = 32
DATA_OFFSET = SEQ_SIZE + SERIAL_SIZE  # 40
TOTAL_SIZE = DATA_OFFSET + IMG_SIZE


class CamReader:
    def __init__(self):
        self._cams = {}  # serial -> {fd, mm, last_seq}
        for path in glob.glob("/dev/shm/cam_*"):
            fd = os.open(path, os.O_RDONLY)
            mm = mmap.mmap(fd, TOTAL_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
            mm.seek(SEQ_SIZE)
            serial = mm.read(SERIAL_SIZE).rstrip(b'\x00').decode()
            self._cams[serial] = {'fd': fd, 'mm': mm, 'last_seq': -1}

    @property
    def serials(self):
        return list(self._cams.keys())

    def get_latest(self, serials=None):
        if serials is None:
            serials = self.serials
        elif isinstance(serials, str):
            serials = [serials]
        if not serials:
            return []
        imgs = []
        for serial in serials:
            cam = self._cams.get(serial)
            if cam is None:
                imgs.append(None)
                continue
            mm = cam['mm']
            mm.seek(0)
            seq = struct.unpack('Q', mm.read(SEQ_SIZE))[0]
            if seq == cam['last_seq']:
                imgs.append(None)
                continue
            mm.seek(DATA_OFFSET)
            data = mm.read(IMG_SIZE)
            img = np.frombuffer(data, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))
            cam['last_seq'] = seq
            imgs.append(img)
        return imgs
