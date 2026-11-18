# 当前验收报告（2026-11-17）

## 已完成

- Ubuntu 26.04.1 开发环境；源码锁定、NTG6 分支祖先关系确认、独立补丁与可重复构建脚本。
- 自编译静态 ARM64 musl release 成功；Rust 测试309项通过，原生与 QEMU 的真实离线 HTTP 集成各3项通过。补丁修复 LIVI CpConfig API、musl ioctl 及 NO_COLOR 单测依赖，增加只读诊断模式。
- 获用户批准，准确识别 WD SN740 512GB 后刷官方 Lite Trixie，Imager 100% 回读校验；Pi5 实际从 NVMe 启动，内核6.18.50+rpt-rpi-2712。主机两块 NVMe 未刷写。
- 预置公钥及固定主机公钥校验，取得以太网 SSH；实际运行官方 Release 和自编译补丁版。
- DWC2/ConfigFS/FunctionFS、g_ether 双向通信、AOA v2 重枚举、CarLife 基础信息/视频初始化与内置 H264 向导帧通过。
- 5GHz AP、真实 iPhone DHCP/关联和用户确认管理页访问通过；BlueZ 基础、classic SDP/RFCOMM 发布已有证据。
- systemd 分层服务、一次暖重启自动启动、进程 SIGKILL 自动恢复通过；重复 bootstrap 保持配置 SHA 不变，完整部署健康检查通过。
- 记录暖重启、20秒空闲 RSS/CPU/I/O/温度及欠压证据，详见07；初次部署版本87c325b12e0493aa；认证能力修正版1e053a7df327b9f7。

## 未完成及实际限制

- **用户提供的 MFi 文件已安装并加载，真实 iAP2 MFi challenge 和 AirPlay pair-verify 已通过；清除旧配对并修正能力声明后，AirPlay MFiSAP 认证、SETUP/RECORD、Wi-Fi iAP2、linked 与 iPhone H264 首帧均已实际观察到。** 本地格式解析与证书/私钥公钥匹配检查通过；Pi --check 返回 parsed_unverified，目录0700、文件0600，重启后 HTTP 正常。 自编译没有 CarLife 私钥；官方 Release 运行报告 key_loaded1024，但未验证认证 challenge 或 NTG6 接受情况。
- 没有 A35 NTG6 端到端证据：真实视频、音频、触摸、Siri、方向盘、锁屏/点火重连及首帧均未验收。内置向导视频不代表 iPhone 视频。
- **供电出现过欠压和历史节流，可靠性未通过。** 暂未进行高负载、长期稳定性、强制断电及多次冷启动测试。
- BLE 独立测试未完成；当前已观察到的是 classic CarPlay 路径发布，不宣称 BLE CarPlay 成功。
- 回滚机制已实现，实际回滚未测试；Linux 完整 CarLifePort 移植未完成。Buildroot 只具准备条件，当前仍使用 Pi OS 验证平台。

## 使用与证据

以太网当前192.168.50.65：`ssh -F .tools/ssh/config pi5`。SSID raspberry_NTG6_5G，管理页 http://192.168.4.1/ ，凭据仅在 `.tools/pi5-connection-details.txt`。管理页无认证，仅在受信 AP 使用。

原始证据在 logs/：pi5-baseline.log、pi5-hardware-final.json、aoa-upstream-smoke.log、aoa-patched-protocol-smoke.log、pi5-guide-first.h264/png、pi5-iphone-page-evidence.log、pi5-autostart-after-reboot.log、pi5-autostart-journal.log、pi5-crash-restart-test.log、pi5-bootstrap-idempotence.log、pi5-deploy-full-health.log、pi5-runtime-resources.json。保留初期失败日志，未将失败改记为成功。

构建产物在 artifacts/，SHA256SUMS 同目录；工具链及镜像元数据在 configs/pi5/。源码、补丁、脚本、配置和报告提交 Git；日志、镜像、工具链、用户密码、SSH 私钥与认证材料不提交。

下一阶段需要确认所提供 MFi 材料的授权并完成音频/交互及实车验证、稳定供电及驻车状态的真实 NTG6 测试，不能据基础测试宣布完整移植验收通过。

手机侧结果补充：23:28:22 video.stream_attached→phase linked→video.first_frame，状态 authenticated=true、airplay verified/encrypted=true、video.active=true；证据 logs/pi5-phone-latest.log、pi5-phone-latest-status.json。Ubuntu 接收工具只丢弃 USB 数据，无显示界面。本次尚未将手机视频解码显示，也未测试音频/触摸；状态中的 video.frames/messages 为0，不能当作媒体数量统计。

只读改造补充：已启用 overlayroot RAM覆盖层、底层ext4及boot FAT只读、/var/log 64MiB tmpfs、纯zram无磁盘后备；保护→维护→保护的重启流程、临时修改丢弃及原配置基线保留均通过。详见09。此前关于可写根和文件日志写SSD的描述仅适用于改造前阶段；目前日常模式的这些写入均进内存。未做强制断电测试，欠压和SSD硬件掉电风险仍在。

2026-11-18 管理页补充：新增维护、普通模式及关机按钮与当前模式提示；网页普通模式切换、API维护/普通切换的实际重启均通过。关机确认打开/取消及未确认请求拒绝通过，未执行实机关机。蓝牙/CarPlay显示名raspberry_NTG6_BT，Linux主机名不变，Wi-Fi及控制器地址/配对基线保留。Rust312项、原生及QEMU离线HTTP各3项、只读启动配置3项通过。部署版本ca22a9181f348ab8；证据logs/pi5-web-controls-deploy.log、pi5-web-mode-normal-then-maintenance.log、pi5-web-maintenance-boot.log。

2026-11-18 故障修正：维护模式“读取失败”为页面缺少断线重试，后端模式接口实际200正常。已部署c1be1f7ac26f5cf1，增加自动重试、boot_id变化后自动刷新和蓝牙等待车机提示；真实浏览器普通模式切换跨断网自动恢复已观察到，三项JS恢复回归测试通过。未开启模拟车机，蓝牙等待真实车机会话为预期状态。

2026-11-18 最终配对固化：按用户要求在维护模式临时模拟车机，实际观察BT/Wi-Fi iAP2 MFi通过、AirPlay MFiSAP签名、linked和手机H264首帧；随后停止模拟器、停止服务并同步保存配对，私密备份在.tools/readonly-backup/paired-20261118.tar.gz。已重启回普通保护模式，逐文件SHA核对SSD只读基线与备份一致，当前服务等待真实车机，模拟器进程不存在。证据logs/pi5-final-maintenance-pairing.log、pi5-paired-protected-final.log、pi5-final-pairing-baseline-check.log。真实NTG6仍需实测。

2026-11-18 首次实车失败：用户确认 NTG6 曾用安卓成功连接 CarLife，本次 Pi 未进入 CarLife。截图显示 USB 已枚举并收到两次 AOA GET_PROTOCOL，未见后续52/53或 CarLife 会话。回家后 Ubuntu 对同一 Pi 两次实际读取均得到0200；未启动模拟器、未修改配置。USB实车兼容性仍待定位，详见10-ntg6-usb-diagnosis.md。

2026-11-18 实车新日志更新：完整50行日志显示52/53、18d1:2d00重枚举及CarLife协议2.0已收到。随后HU_AUTHEN_REQUEST被action=none reason=no_key跳过；此前“只停在AOA查询”的判断仅适用早先截图。当前明确缺少CarLife认证响应，需编译时补齐适用密钥后验证，尚未修复或实车通过。

2026-11-18 CarLife认证修复：按用户授权从百度官网渠道APK提取与上游公钥匹配的RSA常量，编译部署27d9e599728f392f。Pi真实USB对实车384_1.0.0及另一挑战均返回可验证正确响应，缺少密钥的阻断已修复；Rust312、HTTP3、只读3、网页3、新增密钥/构建防护3项通过。实车接受及端到端画面仍待复验。详见05与10。

修复后已重启回protected模式，确认SSD上的current仍为27d9e599728f392f，启动实际报告auth.key_loaded bits=1024，预检carlife_key_embedded=true。分辨率1920×720@60及既有配对保留。证据logs/pi5-carlife-key-protected-final.log。

## 2026-11-18 首次真实 NTG6 连接成功

用户确认车机可正常使用，并提供231行日志及两张状态截图。当前版本27d9e599728f392f：21.466秒收到实车HU_AUTHEN_RESULT=true，21.477秒CarLife session_up，25.347秒iPhone video.first_frame；真实CarLife为Harman/DAIMLER渠道20062105，车机主动声明协议2.0。截图显示两侧1920×720@60参数、H264 High L4.2；这是会话/配置参数，不是独立测得的屏幕实际刷新率。

本次蓝牙确实参与：22.773秒acl_up，24.417秒BT iAP2 MFi通过，24.529秒BT CarPlayStartSession；随后Wi-Fi iAP2 MFi通过，25.278秒收到disableBluetooth并断开BT，视频继续。不能据连接后的蓝牙断开推断冷启动仅需Wi-Fi。

导航/默认音频Opus收到首包并转为CarLife 16kHz单声道TTS；媒体AAC-LC收到首包并转为48kHz双声道PCM，媒体元数据/封面发送有日志。用户确认正常使用；没有单独验收方向盘、触摸、通话、Siri双向麦克风及长期稳定性。115秒附近出现3条video outlet_backlog_dropped并请求关键帧，未据此宣称全程无掉帧。

自动启动仍未解决：用户需手动选择车机CarLife。6.869秒USB configured，6.874/7.371秒只有AOA查询，19.903秒才开始52字符串请求；进入CarLife后认证及手机连接成功。源码HU_INFO阶段已发送FOREGROUND；此消息只能在协议通道建立后发送，不能直接证明车机菜单自动发起连接的问题已解决。具体是否车机记忆/授权、Pi USB身份或启动时序，尚无结论。

证据logs/pi5-ntg6-first-success-20261118.log。本节替代此前“尚无真实NTG6成功”的阶段描述，首次实车成功不等于全部功能与可靠性验收完成。本轮仅检查日志和记录结果，未修改Pi配置。

2026-11-18 自动启动实验第一阶段：用户要求开机直接呈现18d1:2d00，已部署4a14d00925f586a4并重启回protected，实际USB和启动日志均确认直接accessory。真实USB测试不发51/52/53、等待5秒再发协议，CarLife2.0及两次签名验证通过。发现并修复旧静默探测超时留下半帧的问题，回归测试修前失败/修后通过；Rust313及HTTP/只读/网页/密钥防护各3项通过。10个配置与配对文件SHA保持一致；previous指向实车成功的27d9e599728f392f。是否触发NTG6自动启动尚待实车，本阶段没有添加延时自动重枚举，详见11。

2026-11-18 实车反馈及暂停恢复修正：直接2d00没有触发NTG6自动打开画面，用户仍需手动启动；返回主目录数秒后再次进入报连接失败。cp2cl+4.log末尾收到VIDEO_ENCODER_PAUSE，此后没有START。发现原代码PAUSE同时停掉心跳，现对DAIMLER渠道20062105后台按100ms保活、暂停图像并保留会话，START后恢复原前台通知和关键帧请求。部署66208fae6dc77fab，真实USB三轮暂停各6秒均收到60个心跳并恢复视频；真实iPhone在测试中连接并有首帧。Rust314及HTTP/只读/网页/密钥防护各3项通过，10个配置/配对文件SHA未变。自动启动仍未解决，真实NTG6的重进修复效果待复验。详见12。
