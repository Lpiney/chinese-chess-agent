# Chinese Chess Agent

中国象棋教学 Web Demo：左侧是浏览器里的中国象棋棋盘，右侧是类似微信 / WhatsApp 的聊天窗口。玩家执红，Pikafish 执黑；当玩家在右侧提问时，系统会先把当前棋局交给 Pikafish 求出最优推荐，再把引擎结论交给 `deepseek-v4-flash` 解释为什么这一步最好。

## 项目结构

```text
chinese-chess-agent/
├── main.py                 # Flask Web 入口
├── board.py                # 中国象棋棋盘规则
├── pikafish_engine.py      # Pikafish UCI 封装
├── board_serializer.py     # 棋局状态序列化
├── deepseek_client.py      # DeepSeek API 客户端
├── chess_agent.py          # Pikafish + DeepSeek 编排模块
├── templates/
│   └── index.html          # Web 页面模板
├── static/
│   ├── app.css             # 页面样式
│   └── app.js              # 前端交互逻辑
├── config.example.yaml     # DeepSeek 配置示例
├── requirements.txt        # Python 依赖
├── env/
│   ├── conda-environment.yml
│   └── README.md
├── docs/
│   ├── log.md
│   └── requirements.md
├── tests/
│   └── test_board.py
├── scripts/
│   └── setup_pikafish.sh
└── third_party/
    └── Pikafish/           # 官方子模块
```

## 功能

1. 浏览器棋盘交互。
2. 鼠标点击走子与合法落点高亮。
3. Pikafish 作为黑方机器人。
4. 三档难度：`Beginner`、`Medium`、`Master`。
5. 右侧网页聊天窗口。
6. 用户提问后：
   当前棋局 → Pikafish 分析 → DeepSeek 解释推荐走法。

## 环境准备

推荐使用 Conda：

```bash
conda env create -f env/conda-environment.yml
conda activate chinese-chess-agent
```

如果你想手动安装：

```bash
conda create -n chinese-chess-agent python=3.11
conda activate chinese-chess-agent
pip install -r requirements.txt
```

## 配置 DeepSeek

先复制配置：

```bash
cp config.example.yaml config.yaml
```

然后填写你的 API Key：

```yaml
deepseek:
  api_key: "你的真实 API Key"
  base_url: "https://api.deepseek.com"
  model_name: "deepseek-v4-flash"
```

## 初始化 Pikafish

```bash
bash scripts/setup_pikafish.sh
```

## 运行

```bash
python main.py
```

程序会启动本地 Web 服务，并自动尝试打开浏览器：

```text
http://127.0.0.1:5000
```

## 停止服务

如果服务正在当前终端前台运行，直接按：

```bash
Ctrl + C
```

如果你已经关掉了原来的终端，可以执行：

```bash
bash scripts/stop_web.sh
```

## 使用方式

1. 在左侧棋盘点击红方棋子。
2. 点击高亮落点完成走子。
3. Pikafish 会自动回应。
4. 右侧聊天区可直接提问：
   - “下一步该怎么走？”
   - “为什么这步最好？”
   - “现在谁更好？”
   - “这步是不是在保护将？”

## 测试

```bash
python -m unittest discover -s tests
```
