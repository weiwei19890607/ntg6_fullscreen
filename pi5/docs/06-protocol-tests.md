# 协议测试与实车清单

## Linux 模拟器调查

cp2cl README 指向 [CarLifePort](https://github.com/0x5e/CarLifePort)。已实际读取其当前 README（logs/CarLifePort-README.md）：原生 link 产物为 CarLifeLink.app，依赖 dylib、macOS 签名/定位权限，Go 服务加 WebCodecs 前端。**它不是已核实可直接在 Ubuntu 运行的模拟器**。浏览器前端可跨平台不等于 macOS USB 后端可跨平台。
可行替代是复用 CarLifePort 的分层或百度开源 [CarLifeVehicleLib](https://github.com/ApolloAuto/CarLife) 在 Linux 另做 libusb/AOA backend；需要单独移植/协议验证，当前未完成，不冒称已有可用 Linux 版本。Windows 工具/USB passthrough 也必须另行测试，不能直接执行 macOS 程序。
本阶段可用 carlife-md 的 framing/descriptor/协议单测和真实 Pi Gadget 对 Ubuntu USB 枚举独立验证；这两项不能证明音视频端到端成功。

## Ubuntu↔Pi 已完成的基础测试

新增 tests/aoa-smoke.c：libusb 仅选择测试 Pi 的 VID/PID/序列号，AOA v2 重枚举后发送版本、HU_INFO 和 VIDEO_INIT/START。实际收到 MATCH_STATUS、MD_INFO、1280×720@30 ACK，以及20,823字节 H264向导帧。ffprobe/ffmpeg 确认 High/yuv420p/1280×720 并解码为 PNG；这是内置连接向导，**不是 iPhone 视频**。测试未发送认证 challenge，未测试音频/触摸/Siri；该工具不是完整 Linux CarLifePort 移植。

编译：`gcc -Wall -Wextra -Werror tests/aoa-smoke.c -o .tools/aoa-smoke $(pkg-config --cflags --libs libusb-1.0)`。需要 USB 访问权限并保持以太网 SSH。协议模式通过 `CP2CL_TEST_PROTOCOL=1` 开启，证据见 logs/aoa-patched-protocol-smoke.log。

## 实车逐项验收

| 功能 | 操作/证据 | 当前 |
|---|---|---|
| USB 枚举 | Ubuntu AOA 前后 VID/PID/端点已验证，实车仍待验证 | 基础 PASS / NTG6 NOT_TESTED |
| CarLife 初始化/握手 | NTG6 插线，记录状态转移/协议版本、初始化顺序 | NOT_TESTED |
| 分辨率/帧率 | 记录车机协商值→CarPlay /info、首帧编码参数；默认无 screen override | NOT_TESTED |
| 视频 | 首帧、连续播放、全屏比例/黑边、至少 30min | NOT_TESTED |
| 媒体/导航音频 | 音乐、提示混音、音量、音画同步 | NOT_TESTED |
| Siri/电话 | 麦克风双向、唤醒、通话切换和结束后恢复 | NOT_TESTED |
| 触摸/方向盘 | 坐标、边缘、点击/长按、选择/返回/音量，标注上游键码限制 | NOT_TESTED |
| iPhone 重连 | 亮屏/锁屏、蓝牙范围变化、离车再进入 | NOT_TESTED |
| 车机重连 | USB 拔插/车机重启/点火周期；保存故障日志 | NOT_TESTED |
| 稳定性 | 连续 2h，之后 8h，记录内存/温度/欠压/丢帧/USB reset | NOT_TESTED |

Ubuntu 抓 USB：确认总线后 `sudo modprobe usbmon`，用已安装的 Wireshark/tshark 或内核 usbmon 记录指定总线；Pi 侧抓 btmon 和 journalctl。不能使用 usbmon 数据证明空缺的 MFi 认证成功。抓包可能包含设备标识/音频/认证交换，应本地保存、按需脱敏，不默认上传。

真实车辆仅在安全驻车状态由用户配合操作；需要 iPhone、合法 MFi 材料以及 2020 中国进口 A35 NTG6，尚无完成实车的证据。

## 无车机时的手机侧测试

cp2cl 在 CarLife HU_INFO 建立车机会话之前，明确保持 AirPlay held、Bluetooth waiting_for_car；仅连接热点不能验证 CarPlay。tests/aoa-smoke.c 的 `CP2CL_TEST_PROTOCOL=1 CP2CL_HOLD_SECONDS=900` 可模拟车机握手并持续读取 USB 流15分钟，保持原程序的门控设计。需要主机 USB 权限，使用 `sudo env ... .tools/aoa-smoke`，且先让 Pi cp2cl 回到18d1:4ee1初始状态；中断测试/超时后可在 Pi 重启 cp2cl 恢复等待车机。

保持网线 SSH，iPhone 开启蓝牙/Wi-Fi/Siri，在蓝牙设置选择 cp2cl-pi5 并接受配对/使用 CarPlay。以实际认证、无线连接、流建立日志判定，而非仅根据配对或管理页。此窗口禁用视频保存，只持续丢弃接收的数据，输出帧计数（含向导帧），不作真实视频已成功的判据。最长允许1800秒；不应当作生产服务启用。

2026-11-17 已实际观察 car_up→airplay.listening→bt.service_up，BlueZ Pairable=yes。清除旧配对并部署认证能力修正后，已实际通过 MFiSAP、Wi-Fi iAP2，并观察 linked/H264首帧；当前接收工具无显示界面，尚未进行手机视频解码显示。

## 次日 NTG6 测试准备

当前持久屏幕设置为1920×720@60；模板与目标均已更新，--check、管理接口和启动日志核对通过。该配置不等于已实测60fps。热点 raspberry_NTG6_5G，实测5GHz信道149/5745MHz/20MHz，WPA2；密码只在目标和本地忽略的凭据文件保存。蓝牙名称现为raspberry_NTG6_BT（2026-11-18修改），此前测试日志中的cp2cl-pi5为旧名称。

Ubuntu 模拟器已停止，cp2cl重启并恢复 waiting_for_host/waiting_for_car，服务开机自启。安全驻车时，将Pi USB-C数据口经数据线接入NTG6支持CarLife的USB口，在车机进入相应CarLife入口；车机会话建立后cp2cl才发布手机连接服务。iPhone保持Wi-Fi/蓝牙开启，选择cp2cl-pi5并允许CarPlay，正常由蓝牙下发新热点信息并自动切换；若需手动入网，使用新的SSID和本地凭据。无需连接Ubuntu或以太网。

供电仍是未解决项：此前USB供电有欠压证据，不能保证车口单独供电足够。应采用已验证能保留device数据路径、足额供电且防倒灌的供电方案，禁止任意并联5V。自编译缺CarLife认证私钥，具体NTG6是否要求它尚未验证；手机侧已通过不代表车机侧必然通过。先测显示/比例，再逐项音频、Siri、触摸和重连。

1920×720@60 模拟主机测试使用额外参数 CP2CL_TEST_WIDE_60=1；实际 ACK 为08800f10d005183c，已收到对应向导帧。重新开放窗口后，手机自动完成AirPlay认证并再次产生video.first_frame，证据logs/pi5-wide-phone-reconnect.log。该观察不等于实测60fps或NTG6显示。没有真实/模拟车机会话时，Wi-Fi及蓝牙连接本身不会打开CarPlay门控。
