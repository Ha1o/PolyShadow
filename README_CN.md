# 🕵️‍♂️ PolyShadow

> Polymarket 政治板块"内幕交易"与"聪明钱"链上监控系统。

[English](./README.md) | [中文文档](./README_CN.md)

PolyShadow 是一个 24/7 全天候运行的 Python 监控脚本。它专注于扫描 **Polymarket** 上的政治类预测市场，通过链上数据分析，捕捉那些**使用全新钱包（Fresh Wallets）进行大额逆势押注**的可疑行为。

这种行为模式（新号 + 重仓 + 反向）往往意味着极强的信息优势或内幕消息。

---

## 🚀 核心功能

* **全天候监控**: 实时扫描流动性最高的政治（Politics）预测事件。
* **内幕嗅探**: 自动识别"新钱包"地址（Nonce < 10），这是为了规避追踪的常见手段。
* **逆势捕捉**: 专注于捕捉赔率低于 30% 的反向押注（Contrarian Bets），过滤掉跟随大众的噪音。
* **分级警报**: 通过 Telegram 发送带有威胁等级的实时推送：
    * 👻 **S级 (GHOST)**: 极度可疑内幕 (新号 + 重仓)
    * 🐳 **A级 (WHALE)**: 巨鲸异动 (超大额资金)
    * 🦈 **B级 (SHARK)**: 聪明钱流入
* **100% 安全**: 仅使用公开的 RPC 和 GraphQL 数据，**不需要** 任何私钥或交易权限。

---

## 🛠 安装指南

### 1. 克隆项目

```bash
git clone https://github.com/Ha1o/PolyShadow.git
cd PolyShadow
```

### 2. 安装依赖

建议使用 Python 3.10+ 版本。

```bash
pip install -r requirements.txt
```

### 3. 配置环境

复制配置文件模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置信息：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `POLYGON_RPC_URL` | Polygon RPC 节点链接 | [Infura](https://infura.io/) 或 [Alchemy](https://alchemy.com/) |
| `TELEGRAM_BOT_TOKEN` | Telegram 机器人 Token | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | 你的 Telegram ID | [@userinfobot](https://t.me/userinfobot) |

---

## 🖥 使用方法

直接运行主程序即可开启监控：

```bash
python main.py
```

当捕捉到符合条件（金额 > $10k, 赔率 < 30%, 新钱包）的交易时，你的 Telegram 将立即收到如下格式的警报：

```
🚨 SUSPECTED INSIDER 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👻 Level S | GHOST

🎯 Event: Venezuela Election
🟢 Bet: YES
📉 Odds: 15% (Contrarian!)
💰 Size: $35.0K ($35,000)

🕵️ Wallet: 0x8aF1...3b12
   ├─ Nonce: 0 👻 Ghost
   └─ View on PolygonScan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🧪 测试

```bash
# 测试 API 连接
python -m tests.test_api

# 测试警报等级
python -m tests.test_alert_levels

# 发送测试消息到 Telegram
python -m tests.test_alert_levels --send
```

---

## 📁 项目结构

```
PolyShadow/
├── main.py              # 主监控循环
├── config.py            # 配置管理
├── polymarket_api.py    # Polymarket API 封装
├── wallet_checker.py    # Polygon Nonce 检查器
├── telegram_alert.py    # Telegram 推送模块
├── tests/               # 测试套件
├── .env.example         # 配置模板
├── requirements.txt     # Python 依赖
└── LICENSE              # MIT 许可证
```

---

## ⚠️ 免责声明

本项目仅供**区块链技术研究和数据分析学习**使用。

* 预测市场存在极高风险
* 本工具提供的任何数据**不构成投资建议 (NFA)**
* 请自行研究 (**DYOR**)

---

## 📄 开源协议

基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  <i>Built with 🐍 Python | Powered by Polymarket & Polygon</i>
</p>
