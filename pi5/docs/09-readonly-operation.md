# 车载只读运行与维护

## 当前实现

2026-11-17 已在 Pi 5 / Raspberry Pi OS Lite Trixie 实际部署并重启验证，使用发行版 overlayroot（raspi-config 也使用该包）。

- `/media/root-ro`：原 NVMe ext4 根分区，**ro**。
- `/media/root-rw`：tmpfs，接收运行时修改；合并后的 `/` 显示 overlay/rw，这不代表 SSD 可写。
- `/boot/firmware`：NVMe FAT 启动分区，**ro**。
- `/var/log`：64MiB tmpfs，包括 cp2cl 文件日志；journald 仍在内存，32MiB 上限。`/tmp` 和 `/run` 也在内存。
- rpi-swap 显式 `Mechanism=zram`；`/sys/block/zram0/backing_dev` 实测 `none`，移除了默认 zram+file 定时写回路径。
- 自动更新、包数据库备份、logrotate、e2scrub、fstrim 和 zram 写回计时器已屏蔽；维护时由操作者手动更新，不依赖后台自动更新。
- cp2cl 启动前检查保护状态；如果启动参数要求保护但底层分区可写、日志不在 RAM 或 zram 有磁盘后备，则拒绝启动 cp2cl 并记录错误。

配置和认证文件仍保留原路径 `/etc/cp2cl`，BlueZ 配对在 `/var/lib/bluetooth`，它们的**磁盘基线在日常模式冻结**，没有额外创建可写数据分区。程序仍可在内存中更新配置/配对，但重启后恢复基线。适合固定手机和固定车机；新增配对或永久保存设置应进入维护模式。不会自动把整个覆盖层回写，避免将缓存、日志或未知更改混入基线。

当前基线：1920×720@60、SSID raspberry_NTG6_5G、现有 MFi 文件与手机配对；密码仅在目标文件及本地忽略的连接信息文件。与改造前私密备份逐文件 SHA 比较，config/pairings/MFi/hostapd 均一致。60fps是目标配置，不是实测输出帧率。

## 网页操作（2026-11-18）

连接热点后打开 http://192.168.4.1/ ，进入“设置”，可看到当前运行模式及三个按钮：

- “开启维护模式”：确认后保存下次启动模式，并在3秒后通过systemd正常重启；重启后修改可永久保存，当前内存修改不会自动保存。
- “开启普通模式”：确认后重启进入只读保护，保留维护期间已经写入的配置。
- “关机”：确认后通过systemd正常关机；热点会断开，等系统关机完成再断电。

当前模式对应按钮自动禁用，接受操作后禁用重复点击。普通模式保存屏幕设置会明确提示“临时保存，重启后恢复”，避免误认为已持久保存。请求仅提供固定动作，要求JSON确认并拒绝跨来源请求；原有AP内管理页仍无账号认证，应只供受信设备使用。

普通↔维护的网页/API切换及重启已在目标机实际验证，关机弹窗的打开/取消与未确认请求400拒绝已验证；未真正执行关机，以保留当前可测试状态。自动关机调用固定的systemctl poweroff，不使用直接断电或立即重启系统调用。

蓝牙/CarPlay显示名称现为raspberry_NTG6_BT，通过/etc/cp2cl/bluetooth-name设置，与Linux主机名及Wi-Fi SSID分开。BlueZ别名同步设置，控制器地址、原配对文件保持；手机若显示旧名称，可重新打开蓝牙设置刷新设备列表。cp2cl仍需真实车机会话才开放CarPlay，新增按钮不会绕过该门控。

## 查询与修改

通过现有以太网 SSH（或后续配置好的 SSH 连接）登录 Pi 后：

```bash
sudo cp2cl-mode status
```

`current=protected`、`changes_persist=false` 表示日常保护已生效。`next_boot` 单独显示下次启动模式，选择模式后仍需重启。

需要新增配对、保存管理页设置、更新程序或系统时，先执行：

```bash
sudo cp2cl-mode maintenance
sudo reboot
```

重连后确认 `current=maintenance`、`changes_persist=true`。此时根分区可写，专用启动服务也会将 boot 分区改为可写。**先进入维护模式，再做永久修改**；在保护模式下已经改过的内容不会自动带入。若需保留本次内存日志，先复制到另一台电脑。

完成配对、设置或更新后执行：

```bash
sudo cp2cl-mode protect
sudo reboot
```

重连确认 `current=protected`。`protect` 在已经运行于 overlay 时会拒绝操作，避免用户误以为它会保存内存修改。bootstrap/install-release/rollback 在保护模式中也会明确拒绝持久部署，而不是看似更新成功、重启又丢失。

维护模式期间应正常关机，不能当成日常抗断电模式。日常模式也保留 `sudo poweroff` 的正常关机方式。

## 已执行验证

1. 重启进入保护模式：底层 ext4/FAT 都 ro，覆盖层和日志为 tmpfs，zram backing_dev=none；SSH、AP、DHCP、USB准备及 cp2cl 均正常。
2. 在 `/etc/cp2cl/.volatile-storage-test` 写入测试标记，确认下层没有该文件。
3. 从保护模式切到维护模式并重启：根分区恢复 ext4/rw，测试标记已消失，证明 RAM 修改没有落盘。
4. 安装维护启动服务、返回保护模式并重启，持久工具保留，保护检查再次通过。
5. 原有配置/热点/MFi/手机配对基线 SHA 与备份一致。
6. 保护模式下20秒空闲采样，整盘新增读/写均0字节；仅代表该窗口，不代表启动阶段或硬件绝对零写。
7. 初始 overlayroot 与新内核的重挂载参数冲突已通过 init-bottom hook 修正：只清理 RAM 中生成的根挂载参数，保留已挂载覆盖层与底层只读设置。三项主机回归测试覆盖 overlay 修正、维护模式不修改及启动顺序。

证据：`logs/pi5-readonly-first-boot.log`、`pi5-readonly-maintenance-switch.log`、`pi5-readonly-maintenance-boot.log`、`pi5-readonly-seal.log`、`pi5-readonly-final.log`、`pi5-readonly-resources.json`。没有执行强制断电测试，也没有重新开启模拟车机；当前停在等待真实车机状态。

## 安装和故障恢复

改造前的启动分区及重要配置备份在主机 `.tools/readonly-backup/before-readonly.tar.gz`，目录0700、文件0600，包含私钥，禁止公开或提交 Git；这不是整盘镜像。

可重复安装：先处于维护模式、保留私密备份，安装 overlayroot，上传最新 scripts/configs 后以 root 执行 `scripts/enable-pi5-readonly.sh`，再重启检查。包安装会生成包含 overlayroot hook 的 initramfs；脚本核对当前内核 initramfs 后才设置保护启动参数。

如果保护模式启动后网络不可用，可以按原来的官方 RPIBOOT mass-storage 路线在 Ubuntu 上挂载已核对身份的 SSD 启动分区，将 cmdline.txt 中唯一的 `overlayroot=tmpfs:swap=0,recurse=1` 改成 `overlayroot=disabled`（整行仍保持一行），同步并卸载后正常启动；不必重刷 SSD。进入维护后排查。切勿凭 /dev/sda 名称操作主机磁盘。

## 可靠性的范围

这项改造大幅减少正常运行中的 SSD 写入和断电时的软件数据风险，**不是 SSD 硬件掉电保护**。不能承诺任意供电波动、写入中的维护模式、SSD固件行为或反复异常断电绝不损坏。此前欠压问题仍未解决，稳定供电和实车断电/重启测试仍需完成。Buildroot 迁移应继续保留同样的只读/持久配置边界。

依据：[Raspberry Pi raspi-config](https://github.com/raspberrypi/raspi-config)、目标 overlayroot.conf 和 rpi-swap 的 swap.conf(5) 实际包文档。

## 重启后的网页恢复修正（2026-11-18）

用户发现切到维护模式后页面停在“运行模式读取失败”。实际SSH、/api/system均正常，模式已成功切换；原页面仅首次/首次进入设置时读取一次，碰上重启断网后隐藏按钮且没有重试。现已增加2秒轮询、网络/前后台恢复时重试、请求超时、并发读取保护，检测boot_id变化后自动刷新，恢复所有操作按钮。HTML也标记no-store，减少加载旧代码。断线期间显示等待恢复，关机断线保留关机提示。

设置页同时读取真实CarLife会话状态，明确显示“等待车机”“车机会话就绪可配对”或“手机视频流已建立”。未改变车机先建立会话、手机才开放CarPlay的门控；没有重新开启模拟车机。普通/维护模式均遵循此规则，改名与模式切换不负责让无车机的蓝牙连接常驻。

新增tests/test_web_reconnect.cjs，用Node内置test/vm执行页面实际恢复代码，覆盖初始断网恢复、重启跨boot_id自动刷新、关机断线提示三种情况；不是对真实浏览器进行模拟操控。可用node --test tests/test_web_reconnect.cjs运行，或给scripts/test.sh设置CP2CL_NODE_BINARY。

真实浏览器也已通过网页切换普通模式，跨网络中断后无需手动刷新自动恢复模式和按钮；随后再次从网页开启维护模式验证同一流程。实际热点是否重新关联取决于手机网络设置，网页不能替手机选择热点。
