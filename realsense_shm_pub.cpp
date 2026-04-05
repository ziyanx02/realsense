#include <librealsense2/rs.hpp>
#include <iostream>
#include <vector>
#include <string>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <atomic>
#include <cstring>
#include <csignal>

constexpr int WIDTH = 424;
constexpr int HEIGHT = 240;
constexpr int CHANNELS = 3;
constexpr size_t IMG_SIZE = WIDTH * HEIGHT * CHANNELS;

static std::atomic<bool> g_running{true};

void signal_handler(int) {
    g_running = false;
}

struct SharedFrame {
    std::atomic<uint64_t> seq;
    char serial[32];
    uint8_t data[IMG_SIZE];
};

class ShmBuffer {
public:
    ShmBuffer(const std::string& name, const std::string& serial) {
        shm_name_ = "/" + name;

        fd_ = shm_open(shm_name_.c_str(), O_CREAT | O_RDWR, 0666);
        ftruncate(fd_, sizeof(SharedFrame));

        ptr_ = (SharedFrame*)mmap(
            0, sizeof(SharedFrame),
            PROT_READ | PROT_WRITE,
            MAP_SHARED, fd_, 0
        );

        ptr_->seq.store(0);
        memset(ptr_->serial, 0, sizeof(ptr_->serial));
        strncpy(ptr_->serial, serial.c_str(), sizeof(ptr_->serial) - 1);
    }

    ~ShmBuffer() {
        munmap(ptr_, sizeof(SharedFrame));
        close(fd_);
        shm_unlink(shm_name_.c_str());
    }

    void write(const uint8_t* src) {
        uint64_t next = ptr_->seq.load() + 1;
        memcpy(ptr_->data, src, IMG_SIZE);
        ptr_->seq.store(next, std::memory_order_release);
    }

private:
    std::string shm_name_;
    int fd_;
    SharedFrame* ptr_;
};

int main() {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    rs2::context ctx;
    auto devices = ctx.query_devices();

    int num_cams = devices.size();
    if (num_cams == 0) {
        std::cerr << "No RealSense devices found. Exiting." << std::endl;
        return 1;
    }

    std::cout << "Found " << num_cams << " camera(s)" << std::endl;

    std::vector<rs2::pipeline> pipelines;
    std::vector<ShmBuffer> buffers;
    pipelines.reserve(num_cams);
    buffers.reserve(num_cams);

    for (int i = 0; i < num_cams; i++) {
        rs2::pipeline pipe;
        rs2::config cfg;

        std::string serial = devices[i].get_info(RS2_CAMERA_INFO_SERIAL_NUMBER);
        cfg.enable_device(serial);
        cfg.enable_stream(RS2_STREAM_COLOR, WIDTH, HEIGHT, RS2_FORMAT_RGB8, 60);
        pipe.start(cfg);

        pipelines.push_back(pipe);
        buffers.emplace_back("cam_" + std::to_string(i), serial);

        std::cout << "Started camera " << i << " serial: " << serial << std::endl;
    }

    while (g_running) {
        for (int i = 0; i < num_cams; i++) {
            rs2::frameset frames;
            if (!pipelines[i].try_wait_for_frames(&frames, 100))
                continue;
            auto color = frames.get_color_frame();
            if (color)
                buffers[i].write((const uint8_t*)color.get_data());
        }
    }

    std::cout << "Shutting down..." << std::endl;
    for (auto& pipe : pipelines)
        pipe.stop();

    return 0;
}
