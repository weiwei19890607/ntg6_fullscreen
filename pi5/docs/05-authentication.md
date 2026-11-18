# MFi 与 CarLife 认证

## 实际实现

src/main.rs 的 mfi_signer() 从 `/etc/cp2cl/certificate.p7b` 与 `identity.pk8` 读取，FileCoprocessor::from_bytes 证书在前/私钥在后；缺失时选择 NoCoprocessor，明确记录 phone_rejects，而不是通过认证。坏文件会返回启动错误。
LIVI iap2-mfi/file.rs：证书接受 DER 或 PEM 包裹的 PKCS#7；当前检查仅 DER 序列头及最小长度，**没有验证 Apple 信任链或证书/私钥匹配**。私钥为未加密 PKCS#8 P-256 EC 或 RSA。P-256 使用 ECDSA prehash 签名、协议 major 3；RSA major 2，以 SHA1 challenge 加 PKCS#1 v1.5 前缀签名。私钥不应写日志。

现成接口 `AuthCoprocessor` 已有 protocol_major/read_certificate/generate_challenge_response：FileCoprocessor（软件）、I2cCoprocessor（Linux 硬件）、NoCoprocessor（明确失败）。不再另造功能重复的 Provider 层。
I2cCoprocessor::open(bus,power_gpio) 已实现读取/签名寄存器与超时轮询，但 Pi 应用暂未接入配置选择。其可选电源 GPIO 固定使用 /dev/gpiochip0；Pi 5 的 RP1 GPIO 芯片编号/标签必须现场确认后改为可配置，不能按 GPIO 号盲接。可先设计无需电源 GPIO 的合法芯片接口，仍需核实电平、地址、供电和授权资料，不开启整条 I2C 扫描作为认证验证。

## 可独立验证

`cp2cl --check` 在没有材料时报告 mfi=absent；有文件时仅 parsed_unverified。可用上游 iap2-mfi 的单元测试验证错误处理/算法，但不能把测试 fixture 当 MFi 材料部署。
Mock 仅限 #[cfg(test)] 的 trait stub：记录 challenge/回传固定测试字节或返回明确错误；不能连接真实认证状态机作为成功替代，不生成伪造证书。本阶段以 NoCoprocessor 的明确失败和已有协议单元测试为基础，不添加运行时“免认证”开关。

2026-11-17 用户提供 certificate/ 下的文件后，已本地解析 PKCS#7 与 PKCS#8，并确认公钥匹配；已安装到 Pi 的 /etc/cp2cl，目录0700、文件0600、root所有。目标 --check 返回 parsed_unverified，重启日志确认 credentials_loaded，进程及 HTTP 正常。尚没有真实 Apple 配对/认证结果，也未验证 Apple 信任链。用户将来以安全通道放置合法文件到 Pi（目录 0700、文件 0600），不要提交 Git 或普通日志。检查解析后仍需真实 iPhone 验证。

## 独立的 CarLife 认证

carlife_signer() 读取编译期 `CARLIFE_PRIVATE_KEY`，与 MFi 不同。未提供时构建仍成功，上游会记录 carlife_auth_skipped；是否被具体 NTG6 接受尚未验证。未按上游 README 的提示提取 APK 私钥，未下载任何不明身份密钥，未绕过认证。官方 Release 在 Pi 实际运行时报告 carlife.auth.key_loaded bits=1024；本次未提取该密钥、未发认证 challenge，无法据此确认其授权范围或 NTG6 认证结果。

## 真实 iPhone 连接进展与协议兼容（2026-11-17）

手机侧测试已观察到 iap2.mfi_passed、pairing.verified、airplay.encrypted，说明本次实际 iAP2 challenge 通过且手机已通过 Wi-Fi 打开加密控制连接；不再仅为文件解析成功。随后 /auth-setup 收到36字节/version0，被当前只接受33字节/version1 MFiSAP的服务器拒绝，出现反复 Connecting，媒体流尚未建立。

根因之一为 LIVI bringup 根据 P-256 signer major3 自动宣称 mutual authentication，而 cp2cl 的独立 AirPlay 服务未接入 LIVI livi-cp 的 MFi4 session。已将该能力变为 CpConfig 显式能力开关，cp2cl wired/wireless 均不宣称此项，保留 MFiSAP 的完整证书签名校验流程；增加运行时库单元测试。部署1e053a7df327b9f7后确认 CarPlayStartSession 不再包含 mutual-auth，但旧手机配对仍发送36字节格式，清除手机旧配对后，已收到33字节 MFiSAP 请求，签名完成；手机继续 SETUP/RECORD、Wi-Fi iAP2 认证通过并进入 linked，23:28:22 实际收到第一帧 H264。由此确认本次能力声明修正及清除旧配对后手机侧连接通过。

原始连接证据本地 logs/pi5-phone-connecting.log；不在文档或 Git 中放认证交换原文、设备标识或私钥。此结果不代表 CarPlay Ultra 已完整实现。

## 2026-11-18 CarLife 密钥补齐

用户明确要求在线查找、下载并修复。按上游README给出的来源，从百度CarLife官网“我是车主”按钮指向的百度手机助手页面下载APK（包名com.baidu.carlife），未运行APK代码。从classes2.dex取得与锁定上游测试公钥完全一致的RSA1024常量，私钥保存于忽略目录certificate/carlife-private.pem，权限0600。APK及下载页面、来源与校验元数据在.tools/，不提交私钥或安装包。

来源：[百度官网](https://carlife.baidu.com/carlife/carowner)、[官网按钮链接](https://mobile.baidu.com/item?pid=1486333&source=appbaidu)、[上游构建说明](https://github.com/0x5e/cp2cl#开发调试)。APK SHA256：8e1bc19f9c2891ef8a3c6b620d04263d58b33831292e88748f18ca979c4dd3c9；与上游匹配的公钥SHA256：14dd49db608dc313231d5124273bc6f96ab1229814e75614bd8645949367ad9a。

scripts/carlife-key.py 支持从APK提取匹配常量、检查本地密钥；拒绝覆盖已有输出，仅输出公钥摘要。scripts/build.sh 自动从本地文件读取并在编译期注入CARLIFE_PRIVATE_KEY，缺少文件的正式ARM64构建会失败；离线无密钥构建须显式设置CP2CL_ALLOW_NO_CARLIFE_KEY=1。可用CP2CL_CARLIFE_KEY_FILE选择文件。scripts/test.sh 在存在密钥时带入上游签名回归测试。

已构建并部署27d9e599728f392f。tests/carlife-auth-smoke.py只持有上游公钥，按序列号定位Pi，经真实USB完成AOA切换和CarLife2.0交换，分别发送384_1.0.0（实车日志挑战）和1234567890_1.0.0，收到响应后做RSA公钥运算，核验PKCS1类型1填充及完整原文；两次均通过，然后才发送模拟认证通过结果。此结果证明Pi能正确回答挑战，不代表NTG6实车已接受。测试已退出，没有保留模拟车机会话。

上游携带实际密钥的公私钥匹配测试1项通过；完整Rust312项、离线HTTP3项、只读配置3项、网页恢复3项及新增密钥处理/构建防护3项通过。日志logs/pi5-carlife-auth-fixed-usb.log、logs/carlife-key-fix-regression.log。旧文中“未提取”的描述为此前阶段，本节记录后续经用户授权执行的变更。
