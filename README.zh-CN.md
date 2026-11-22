# 黄金矿工单人关卡本地双人 Mod

[English README](README.md) · [下载发行包](https://github.com/yuGAN6/gold-miner-solo-coop/releases/latest)

在《黄金矿工：经典版》原有的单人关卡中加入第二名独立操作的矿工。两人共享金钱、目标、道具和倒计时，分别控制抓钩。

## 安装

仅支持 Windows Steam 版，App ID `3777060`，游戏 `2.0.0`、build `26673644` 的指定原包。安装器会核对完整 SHA-256，版本不符或存在其他修改时会停止。

1. 从 Releases 下载 `GoldMiner-Solo-Coop-v0.1.0.zip`，完整解压。
2. 关闭游戏，双击 `Install.cmd`。
3. 自动识别失败时选择含 `GoldMiner.exe` 的游戏文件夹，也可把该文件夹拖到 `Install.cmd` 上。
4. 照常从 Steam 启动，进入“单人游戏”。

安装不需要 Python、Java、Node.js 或反编译工具，只使用 Windows 自带的 PowerShell 和 .NET。请下载发行包；GitHub 自动生成的 Source code 压缩包不含补丁数据。

## 操作

左侧使用原方向键；右侧使用 S 出钩、W 炸药、A/D 对应原左右方向键。经典玩法中 A 使用冰冻道具，D 通常无动作；手动回收玩法按原规则操作。矿工保留自动摆钩机制，WASD 不用于自由移动。

## 恢复原版

关闭游戏后运行 `Uninstall.cmd`。请保留 `resources/app.asar.goldminer-coop-original` 原包备份。Steam 更新或验证完整性可能覆盖 Mod，新构建需要匹配的新补丁；不要强行覆盖不同版本。

## 验证范围

已在正式游戏实测独立操作和共享计分，并在隔离副本中测试安装、卸载与失败保护。尚未逐关通关、覆盖全部后期道具机关，或在另一台实体电脑验证。原存档、成就和排行榜逻辑保留，没有独立的 Mod 记录系统。

本项目是非官方 Mod，与原游戏开发商或发行商无隶属关系，原游戏代码和素材归原权利人所有。
