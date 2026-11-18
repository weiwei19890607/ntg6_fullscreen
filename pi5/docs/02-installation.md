# Pi OS / NVMe 安装

## 当前证据

用户已明确批准覆盖指定 WD SN740。官方 Imager 已写入并完成 **100% 回读验证**。实际从 NVMe 启动 Raspberry Pi OS Lite ARM64 Trixie（2026-10-06），内核 6.18.50+rpt-rpi-2712，根分区 /dev/nvme0n1p2，已扩容约 476.4GiB。

目标：WD PC SN740 SDDPTQD-512G-1102，SSD 序列号 23222S404027，512110190592 字节。Pi USB 序列号 ab045208eb860d1e，导出时稳定路径 /dev/disk/by-id/usb-nvme0n1_Raspberry_Pi_multi-function_USB_device_ab045208eb860d1e-0:0。主机 WD 1TB 和 XPG 2TB 均未刷写。

Imager 验证后弹出 LUN，首次 provisioning 报 No medium found；经 ACM 控制台重新向同一 mass-storage LUN 绑定 /dev/nvme0n1 后成功，脚本已包含处理。写入 cloud-init、公钥及预生成主机密钥，逐文件比较后卸载同步。SSH 使用固定主机公钥校验，不关闭 StrictHostKeyChecking。

当前用户 cp2cl，专用私钥 `.tools/ssh/pi5_ed25519`，以太网 DHCP 当前 192.168.50.65。最初 Wi-Fi STA 已用于接入，后按用户要求改用网线，wlan0 专供 AP。首次 cloud-init 报 cc_netplan_nm_patch 缺失警告、状态 degraded done，无 errors；网络及 SSH 实际成功，不运行 cloud-init clean 重做初始化。

## 无需拆 SSD 的首选路线

官方 usbboot `Readme.md` 明确支持 Pi 5，mass-storage-gadget 的 initramfs 扫描 NVMe/SD/USB 后暴露为 USB 存储。

1. 完全断电，按住 Pi 电源按钮，将主机数据线插入 Pi 的 USB-C。
2. `lsusb -d 0a5c:2712` 确认 ROM 模式。
3. 主机项目目录执行 `sudo upstream/usbboot/rpiboot -d upstream/usbboot/mass-storage-gadget`。仅启动内存环境，不使用 recovery/recovery5，不改 OTP/EEPROM。
4. 执行 `scripts/inspect-storage.sh`。对照插入前后记录，检查 `lsblk -b`、`udevadm info --query=property --name=<明确设备>`、`/dev/disk/by-id/usb-*`。确认型号、序列号、容量、USB transport、所有分区挂载、无 Ubuntu/其他主机磁盘。
5. **显示上述信息并等待用户明确批准覆盖这一块 SSD，才可进入 Imager 或写盘工具。** 禁止仅凭 /dev/sda 名称选择。
6. Raspberry Pi Imager 选择 Pi 5 → Raspberry Pi OS Lite (64-bit)，用户/主机名 cp2cl-pi5、SSH 公钥（或用户现场输入密码），首次建议以太网 DHCP。禁止把明文密码写入仓库。
7. 写入、校验后安全弹出，完全断电后正常启动 Pi，确认实际根分区属于 NVMe。

官方 Imager JSON 当前给出：2026-10-06 Trixie ARM64 Lite，压缩 550466056 字节，展开 3078619136 字节；SHA256 见 configs/pi5/os-image.json。镜像 init_format 为 **cloudinit-rpi**，不能盲目照搬旧版 userconf.txt 配置；优先使用匹配版本 Imager。下载及流式展开哈希已验证，scripts/prepare-image.py 可重复执行，不写块设备。已只读检查镜像中的 user-data/meta-data/network-config。已创建用户 cp2cl、主机名 cp2cl-pi5，专用 SSH 公钥登录、禁密码登录，以太网 DHCP；本地私钥位于 .tools/ssh/pi5_ed25519（Git 忽略）。本次已由 flash-approved.sh 完成目标写入，首次启动文件保存在 Git 忽略的 .tools/ 下。再次刷写仍必须重新确认目标及用户授权。

如无法进入 mass-storage 或 HAT/NVMe 未被 initramfs 支持：使用临时 microSD 官方 Lite 启动，在 Pi 上检查 PCIe/NVMe，确认目标身份后用 Imager 写 NVMe。先保留 SD 作为救援，不把 SSD 导出为 mass storage 的同时挂载写入。BOOT_ORDER/NVMe 启动配置需现场读取后处理，暂不无条件更新 EEPROM。

## 供电

Pi 5 官方电源建议 5V/5A（USB PD）；USB-C 数据与供电共用，主机端口或 NTG6 能否供足 Pi+NVMe 必须实际验证。不能把描述符中的 250mA 当真实功耗，也不能通过设置 MaxPower 强迫主机供电。避免直接并联两路 5V。
如果不足，需用户选择经验证可同时为 Pi 提供足额 5V 且保留 USB2 device 数据路径、具防倒灌/隔离设计的供电硬件，或有明确电源隔离设计的 HAT。未拿到具体方案前不提供随意剪线/接 5V 的接线建议；不得直接把普通 PD Hub 视为兼容 device 模式的方案。

参考：[usbboot 官方步骤](https://github.com/raspberrypi/usbboot/blob/master/Readme.md)、[Pi 5 电源说明](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)、[官方 OS 列表](https://downloads.raspberrypi.com/os_list_imagingutility_v4.json)。
