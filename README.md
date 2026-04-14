# RealSense Shared Memory Publisher

Streams color frames from all connected RealSense cameras into POSIX shared memory (`/dev/shm/cam_0`, `cam_1`, …) for low-latency inter-process access.

---

## 1. Install librealsense2

### Option A — Intel apt repository (Ubuntu 20.04 / 22.04)

```bash
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCD
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main"
sudo apt update
sudo apt install librealsense2-dev
```

Also install udev rules so non-root users can access USB devices:

```bash
sudo apt install librealsense2-udev-rules
```

### Option B — Build from source

```bash
git clone https://github.com/IntelRealSense/librealsense.git
cd librealsense
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
make install
```

Install udev rules manually:

```bash
sudo cp librealsense/config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## 2. Compile

### With apt-installed librealsense2

```bash
g++ -std=c++14 -O2 realsense_shm_pub.cpp -o realsense_shm_pub -lrealsense2 -lrt
```

### With source-built librealsense2

Replace `/path/to/librealsense` with the directory where you cloned the repo.

```bash
g++ -std=c++14 -O2 \
  -I /path/to/librealsense/include \
  -L /path/to/librealsense/build/Release \
  -Wl,-rpath,/path/to/librealsense/build/Release \
  realsense_shm_pub.cpp -o realsense_shm_pub \
  -lrealsense2 -lrt
```

---

## 3. Run manually

```bash
./realsense_shm_pub
```

Exits immediately if no cameras are detected. Press `Ctrl+C` to stop cleanly (shared memory segments are unlinked on exit).

---

## 4. Install as a systemd service

### Create the service file

```bash
sudo nano /etc/systemd/system/realsense-shm.service
```

Paste:

```ini
[Unit]
Description=RealSense Shared Memory Publisher
After=local-fs.target
StartLimitIntervalSec=60
StartLimitBurst=10

[Service]
Type=simple
User=<your-user>
ExecStart=/path/to/realsense_shm_pub
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> `Restart=on-failure` with `RestartSec=3` handles the case where the service starts before USB cameras are enumerated — it will keep retrying until cameras are found.

### Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable realsense-shm   # auto-start on boot
sudo systemctl start realsense-shm    # start now
```

### Check status and logs

```bash
sudo systemctl status realsense-shm
journalctl -u realsense-shm -f
```

### Stop / disable

```bash
sudo systemctl stop realsense-shm
sudo systemctl disable realsense-shm
```

---

## Python reader

```python
from realsense_shm_sub import CamReader

reader = CamReader()
print(reader.serials)          # ['323622273002', '323622272294']

imgs = reader.get_latest()                        # all cameras
imgs = reader.get_latest('323622273002')          # one camera by serial
imgs = reader.get_latest(['323622273002', ...])   # specific cameras

# Each entry is a (480, 640, 3) uint8 numpy array (RGB), or None if no new frame.
```
