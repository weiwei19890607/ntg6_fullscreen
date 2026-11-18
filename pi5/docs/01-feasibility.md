# 源码与 Pi 5 可行性（2026-11-17）

开发主机实际为 Ubuntu **26.04.1 LTS / x86-64**，不是原任务中的 24.04。所有本地结果仅代表该环境。

## 版本选择与证据

锁定提交见 `upstream-lock.json`。cp2cl HEAD `6e8579f`，版本 0.16.3；ntg6_fullscreen HEAD `d090748`，版本 0.16.2。
实际执行 `git -C upstream/cp2cl merge-base --is-ancestor ntg6/main HEAD` 返回 0，`rev-list --left-right --count ntg6/main...HEAD` 输出 `0 12`。
因此后者当前是前者的祖先，不存在本次必须另行移入的 NTG6 独有补丁。27 个文件差异主要为重连、状态页、配置和构建缓存，完整 diff 保存在 logs/upstream-diff.txt。

GitHub API 记录：cp2cl 最新 Release v0.16.3，提供 aarch64/armv7 ELF 和三种其他板卡固件；ntg6_fullscreen 无 Release、无 Issue；cp2cl 返回 1 个 Issue（“宝藏项目”）。原始响应保存在 logs/*-issues.json、*-releases.json。未发现这两份仓库中正式 Pi 5 板卡支持；这不等于已穷尽所有社区仓库。

## 架构与源码位置

| 路径 | 职责 | Pi 5 处理 |
|---|---|---|
| src/main.rs、hooks.rs、sink.rs | 双向桥接、状态、启动 | 保留桥接架构 |
| crates/carplay-hu | AirPlay/iAP2、无线/有线接入、按键、音频 | 使用板载 BlueZ/Wi-Fi，待硬件测试 |
| crates/carlife-md | CarLife framing、AOA 请求、ConfigFS/FunctionFS、会话 | 复用通用 USB 层 |
| vendor/LIVI/native/crates | iAP2、MFi、无线底层 | 针对锁定版本提供小补丁 |
| src/web、assets/web | axum HTTP 管理页，静态资源编入 ELF | 原样复用，新增只读离线模式 |
| src/config.rs | /etc/cp2cl/config.json，主机名/DT vendor | 无需硬编码 Orange Pi 型号 |
| src/led.rs、button.rs | LED 类及 gpio-keys | best-effort，Pi 缺省不保证指示灯/按钮可用 |
| buildroot/board、configs | 其他板卡 DTS、内核/无线驱动、SysV 启动 | 不直接套用到 Pi OS |

视频 H.264 流纯转发；音频不是全部纯转发：AAC 媒体解码至 PCM，Opus 导航解码/降采样，麦克风反向编码。Siri、触摸、方向盘映射须实车验证。上游已说明 NTG6 部分方向键只上报前/后，不能承诺完整方向区分。

USB 程序创建 `/sys/kernel/config/usb_gadget/cp2cl`，挂载 `/dev/usb-ffs/carlife`，写 FunctionFS v2 descriptors/strings 后绑定首个 UDC。一个 ff/ff/00 接口，bulk IN/OUT，FS 64、HS 512 字节，处理 AOA 请求后重新枚举。Pi 5 USB-C 用 dwc2 peripheral；不能同时运行 g_ether 或官方网络 gadget。
Wi-Fi 不由 cp2cl 自动完整搭建：它读取 `/etc/hostapd/*.conf`、控制 socket `/run/hostapd`，并以 `/run/hostapd.pid` 判断 AP 就绪。必须保留这些路径。蓝牙通过 BlueZ 系统 D-Bus、BLE/RFCOMM 连接，主线已有 paging/retry/持久化配对逻辑，效果尚未测定。

## ELF 与构建

下载官方 `cp2cl-linux-aarch64` v0.16.3，`file`：ELF64 AArch64、静态链接、stripped；`readelf -l -d` 无 PT_INTERP、无动态段。因此不要求匹配 glibc；仍依赖 Linux Gadget/蓝牙等内核接口。已在 Pi 实际运行，并通过 Ubuntu libusb 的 AOA 枚举测试；不代表 NTG6 兼容。SHA256 另存 artifacts/SHA256SUMS。
Cargo.lock 随仓库存在；根 build.rs 嵌入 assets 和 Git 信息，CarLife 密钥通过 `option_env!` 编入。协议 Rust 结构已在树中，不需 protobuf-compiler。实际使用 nusb，不需把 libusb 当 cp2cl 运行必需库；libusb 开发包用于 rpiboot。

发现锁定 LIVI 缺少调用方使用的 CpConfig.now_playing，原始源码无法直接通过本地主机构建。补丁恢复字段，并只在 Bluetooth 协商连接关闭 now-playing 订阅，保留媒体连接订阅。musl 编译另需修复 TUNSETIFF 的 ioctl 请求类型推导。补丁分别保存在 patches/，不改写视频管线。

## 依赖矩阵

| 环境 | 必需/条件 | 备注 |
|---|---|---|
| Ubuntu 26.04 主机 | git、gcc/make、pkg-config、Rust/Cargo、CA、wget、Python、binutils | Rust 1.100.0 已安装用户目录 |
| 主机 rpiboot | libusb-1.0 头文件及运行库 | 最初使用用户目录头文件构建，随后已安装系统开发包 |
| 主机交叉构建 | Rust aarch64-unknown-linux-musl、Zig 0.17.1、rust-lld | Zig 编译依赖中的 C/ASM，rust-lld 最终链接 |
| 主机可选 | QEMU user、Imager、mtools | QEMU 仅验证程序启动/离线接口 |
| Pi 运行 | dbus、bluez、hostapd、dnsmasq-base、iw、kmod、iproute2、rfkill | 静态 ELF 不要求 Pi 安装 Rust |
| Pi 验证 | usbutils、curl、vcgencmd（Pi OS 提供）、可选 pciutils | 脚本不视缺少工具为硬件失败 |
| 认证 | 合法 MFi 证书/私钥或授权芯片 | 尚未提供；CarLife 密钥独立存在 |

初始 sudo 无法非交互认证；用户随后授权 sudo，已安装主机开发包、curl、qemu-user、mtools 和 rpi-imager，实际安装日志见 logs/apt-install.log。此后已获用户明确批准并完成目标 SSD 刷写，未操作主机蓝牙。libssl-dev 曾为构建排障安装，但本次依赖图未编译 OpenSSL，不是静态 cp2cl 的运行依赖。

## 风险与路线

先验证官方静态 Release，再对比自编译补丁版。先 NVMe 启动/UDC/AP/BT，再 CarLife USB 和 iPhone，最后 NTG6；每步证据独立。主要风险：Pi+NVMe 供电、brcmfmac 5GHz AP 能力/地区限制、蓝牙共存与重连、dwc2 FunctionFS 行为、认证材料，以及车辆协议兼容。禁止复用 Orange Pi 的 Unisoc 驱动和 DTS。

参考：[cp2cl](https://github.com/0x5e/cp2cl)、[ntg6_fullscreen](https://github.com/weiwei19890607/ntg6_fullscreen)、[官方 USB Gadget](https://github.com/raspberrypi/rpi-usb-gadget)。
