# Codex Gateway Manager

> Codex Desktop 第三方模型可视化管理工具

一个 Windows 桌面应用程序，为 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 提供图形化管理界面，让你在 Codex Desktop 中无缝使用 GPT 订阅和第三方自定义模型。

![platform](https://img.shields.io/badge/platform-Windows-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## 功能

- **运行状态监控** — 实时查看网关运行状态、PID、端口和已加载模型列表
- **配置管理** — 可视化添加、修改、删除第三方模型，支持 OpenAI / Codex Responses / Claude 三类接口
- **开机自启** — 一键开启/关闭网关开机自启动，后台运行无弹窗
- **端口设置** — 可视化修改网关监听端口
- **Codex 修复** — 一键检测并修复 Codex Desktop 的 provider 配置
- **版本更新** — 通过 GitHub Release 自动检查更新
- **单文件 exe** — 无需安装，双击即用

## 快速开始

### 方式一：下载预编译版本

1. 前往 [Releases](https://github.com/zhaoxinyi02/codex-gateway-manager/releases) 下载最新版 `CodexGatewayManager_V*.exe`
2. 双击运行

### 方式二：从源码构建

```bash
git clone https://github.com/zhaoxinyi02/codex-gateway-manager.git
cd codex-gateway-manager
pip install pyyaml pyinstaller
pyinstaller build.spec --noconfirm
```

生成的 exe 在 `dist/` 目录。

## 使用前提

- 已安装 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 并完成初始配置
- 已安装 Codex Desktop 并完成 ChatGPT 登录
- Windows 10/11

## 工作原理

Codex Desktop 的模型下拉列表在同一时间只能绑定一个 provider。本工具通过本地代理网关 (CLIProxyAPI) 统一管理多个模型来源：

- ChatGPT 订阅模型（GPT-5.5、GPT-5.4 等）通过 OAuth 授权接入
- 第三方模型（火山引擎、DeepSeek、MiMo 等）通过 API Key 接入
- 所有模型共用同一个 provider，在对话中可自由切换

网关配置存储在 `%LOCALAPPDATA%\CLIProxyAPI\config.yaml`，Codex 模型目录存储在 `~/.codex/custom-model-catalog.json`。

## 版本号规则

版本号采用日期格式 `VYYYY.MM.DD`，例如 `V2026.07.06`。

## 技术栈

- Python 3 + tkinter（GUI）
- PyYAML（配置读写）
- PyInstaller（打包）

## 相关项目

- [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) — 本地模型代理网关
- [Codex](https://developers.openai.com/codex/) — OpenAI 编程助手

## License

MIT
