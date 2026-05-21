# Chinese Chess Agent

一个本地运行的中国象棋教学 Demo。

- 左侧是中国象棋棋盘，玩家执红，Pikafish 执黑。
- 右侧是聊天区，提问时会先分析当前局面，再返回解释。
- 聊天依赖 `config.yaml` 里的百炼兼容 LLM 配置；如果模型返回空正文，后端会回退到引擎结论。

## 目录

```text
main.py               Flask 入口
board.py              棋盘与走子规则
pikafish_engine.py    Pikafish UCI 封装
chess_agent.py        引擎分析 + 聊天编排
llm_client.py         百炼 / OpenAI 兼容客户端
board_serializer.py   棋局文本化
templates/            页面模板
static/               前端脚本与样式
tests/                单元测试
```

## 依赖

- Python 3.11
- `pip install -r requirements.txt`
- `git`、`make`、C++ 编译器（用于构建 Pikafish）

## 配置

1. 复制配置文件：

```bash
cp config.example.yaml config.yaml
```

2. 填入你的阿里云百炼 API Key。默认已关闭 `qwen3.6-max-preview` 的思考模式，并将 `max_tokens` 收紧到较短回复，以减少延迟和冗长输出。

## 初始化 Pikafish

```bash
bash scripts/setup_pikafish.sh
```

## 运行

```bash
python main.py
```

浏览器打开 [http://127.0.0.1:5000](http://127.0.0.1:5000)。

## 使用

1. 点击红方棋子。
2. 点击高亮位置完成走子；如果目标格是黑棋，直接点黑棋即可吃子。
3. 在右侧输入问题，例如“下一步怎么走？”。

## 测试

```bash
python -m unittest discover -s tests
```
