# 手机提前连接

需求：Pi 上电后先完成 iPhone CarPlay 连接，用户手动打开 NTG6 CarLife 时复用该会话，减少配对引导页等待。

配置 `/etc/cp2cl/config.json`：`"early_connect": true`，且必须明确配置 screen.width、height、fps。本机为 1920×720@60。默认关闭；未配置完整屏幕时回退原来的车机优先连接流程。网页保存分辨率时保留此字段。

实现补丁 `patches/0006-early-phone-connection.patch`：

- 使用固定屏幕初始化 CarPlay `/info`，开机开放手机连接。
- CarLife 上线/离线不再重启或关闭已连接的手机。实际协商屏幕发生变化时仍重新协商。
- 没有车机视频消费者时丢弃画面，不累计视频、不触发持续关键帧请求。
- 缓存 H.264 参数集，在后续关键帧附带；CarLife START 沿用已有请求新关键帧的流程。
- 保存音频格式和媒体元数据。CarLife 握手完成前不转发音频、元数据或手机桌面请求；完成后清理旧 PCM 并恢复当前格式，避免过期音频或未初始化的播放器。
- 保留原有 DAIMLER 暂停心跳修复与 USB 18d1:2d00 身份。

验证：321 项 Rust 测试通过（CarLife 129、CarPlay 102、主程序 90），HTTP/只读启动/密钥与网页恢复测试通过。包含提前音视频、音频格式恢复、关键帧参数集和车机会话反复切换的回归测试。

真实 NTG6 效果需上车验收：手机先连接成功，再点击 CarLife，观察是否直接显示画面；退出车机主页后等待十秒再进入两次。若 iPhone 尚未连接完成，仍会显示引导画面；首次配对本身的授权步骤仍需完成。本功能不保证车机自动打开 CarLife。

## Pi 实机验证（2026-11-18）

部署版本 `7de006c3c44e81e8`。手机在没有车机模拟的情况下完成无线 CarPlay MFi/AirPlay 认证并推送 H.264 High L4.2 首帧：系统单调时间 441.788 秒；USB 模拟车机于 459.941 秒完成 CarLife 会话，相差约 18 秒。两者之间及三次暂停/恢复中没有新的 AirPlay 连接或手机首帧事件，复用了同一个手机会话。

真实 Pi USB 上验证两次 RSA 挑战、CarLife 2.0、1920×720@60；三次暂停各六秒，每次收到 60 个后台心跳，恢复后均重新收到视频。测试进程已退出。这是模拟主机验收，不替代实际 NTG6 的启动显示验收。

日志：`logs/pi5-early-connect-before-car.log`、`logs/pi5-early-connect-session-journal.log`、`logs/pi5-early-connect-usb-smoke.log`。不把“首帧早于车机十八秒”解释成固定启动耗时；本次是维护模式中重启服务，冷启动耗时另看最终启动日志。

最终已重启并确认日常保护模式（当前和下次启动均 protected，根文件系统为 overlay），运行版本为 `7de006c3c44e81e8`，cp2cl 服务正常。重启后没有车机模拟，手机再次自动完成连接并发送首帧。原成功基线 `27d9e599728f392f` 保留在 previous；模拟测试进程已结束。最终日志 `logs/pi5-early-connect-protected-final.log`。
