# 2026-11-18 NTG6 首次实车故障定位

用户反馈：安卓手机曾成功连接该 NTG6 的百度 CarLife；本次 Pi 接入后车机未进入 CarLife。目前 Pi 已回家，USB-C 接 Ubuntu，通过以太网可 SSH。

## 架构与启动策略

iPhone → 无线 CarPlay → Pi → USB CarLife → NTG6。Pi 提供 CarPlay 接收端，NTG6 接收 CarLife。上游程序的 car-first gate 在 CarLife session up 前保持 AirPlay held，暂不发布蓝牙 CarPlay 服务；这是软件策略，不是 CarPlay 协议本身的必要条件。普通蓝牙连接或 Wi-Fi 关联成功并不等于 CarPlay 会话已建立。

## 实车截图证据

应用约开机6.377秒启动，1920×720@60 配置及 MFi 文件加载。USB 约6.715秒配置完成；6.721秒与7.217秒收到 request51 GET_PROTOCOL，程序记录响应 version2。之后 probe not_taken，截图内未见 request52 SEND_STRING、request53 START、accessory 切换或 CarLife 会话建立。截图仅覆盖所显示的日志范围，不能证明后续永远没有请求。

因此首先定位 USB/AOA 握手。MFi 加载成功不等于本次手机认证成功；当前缺少 CarLife 编译密钥是另一个已知限制，但截图阶段尚未出现 CarLife 认证挑战，不能将它认定为本次停在51的原因。

## 家中只读核验

2026-11-18 通过固定 SSH 主机身份确认 Pi 仍为 protected/overlay 模式。当前 USB enumerated=true、accessory=false、session_up=false，在无模拟器的 Ubuntu 上符合预期。

Ubuntu libusb 测试先核对18d1:4ee1设备序列号cp2cl-pi5，然后间隔500毫秒发送两次0xc0/request51/value0/index0/length2。两次实际传输均返回2字节0200。未发送52/53，未启动模拟器，未修改设备配置。该结果仅证明 Ubuntu 主机能读到正确响应，不能代替 NTG6 的控制传输抓包。

源代码比较：当前锁定 cp2cl 与 ntg6_fullscreen 的 desc.rs 没有差异。现阶段没有充分依据随机修改 VID/PID、AOA 版本、USB 类别或设备字符串。

## 下次驻车测试应保留的证据

1. 使用此前安卓成功连接 CarLife 的同一个车机数据口；确认手机互联页面是否列出 Pi 或可选择 CarLife。
2. 上电后等待约一分钟，在管理网页下载完整日志，并保存状态页；拔线或关机前完成下载，普通模式日志在内存，重启后消失。
3. 如果仍只有51请求而没有52/53，下一步需要 NTG6 端或 USB 总线控制传输证据，核对车机是否收到版本响应及之后为何终止。电脑模拟成功不能证明实车互通。

本轮未改启动门控、USB 描述符或配对，未宣称修复完成。

## 后续完整日志：USB已通过，出现认证阻断

用户随后提供 /home/gawain/Downloads/cp2cl.log（50行），并确认车机列表已识别CarLife、两次启动均失败。证据归档 logs/pi5-ntg6-auth-request-20261118.log。此文件只显示一条连续初始化序列，不能分别重建两次点击过程。

新证据取代前述“只有51”的阶段判断：27.082秒收到六个52字符串，27.688秒完成53并切换18d1:2d00，28.184秒再次配置成功，28.692秒收到HU_PROTOCOL_VERSION 2.0，28.694秒收到HU_AUTHEN_REQUEST但action=none reason=no_key。USB/AOA及CarLife入站通道已实际工作，暂不需要盲改描述符。

已确认缺失CarLife认证响应，是当前明确需要解决的阻断点；不能在补齐并实车验证前宣称这是唯一原因。certificate目录现有两个文件仅为Apple MFi材料，与CarLife编译期CARLIFE_PRIVATE_KEY不同。源码option_env读取发生于编译期，单改systemd运行环境不会修复现有二进制。应在取得适用CarLife材料后保留现有补丁重新构建、验证挑战响应，再进行实车认证测试。日志未出现认证结果或视频初始化；不能据此宣称车机认证已经通过。

## 认证缺项已修复，待实车复验

用户要求在线取得密钥并修复后，已从官网渠道APK提取与上游测试公钥匹配的常量，编译部署27d9e599728f392f。Pi真实USB对实车同值挑战384_1.0.0及另一挑战均返回经公钥核验正确的响应；原reason=no_key已消除。详情见05-authentication.md。电脑测试不替代NTG6判定，下一次实车重点观察HU_AUTHEN_RESULT及后续HU_INFO/视频初始化，无需再次盲改AOA参数。
