# 项目需求

## 当前目标

做一个本地可运行的中国象棋教学网页：

- 左侧棋盘可以正常下棋。
- 玩家执红，Pikafish 执黑。
- 右侧聊天区可以根据当前局面回答问题。

## 当前范围

当前版本需要保证：

1. 标准中国象棋开局与完整走子规则。
2. 点击选子、显示合法落点、支持吃子。
3. Pikafish 三档难度。
4. 基于当前棋局的聊天分析。
5. 运行方式简单，文档和报错信息清楚。

## 运行要求

- Python 3.11
- `pip install -r requirements.txt`
- 已初始化 Pikafish：`bash scripts/setup_pikafish.sh`
- 已配置 `config.yaml`

## 验收标准

1. 页面能正常显示棋盘。
2. 红方能走子，也能正常吃黑棋。
3. 黑方会自动应手。
4. 聊天区发送后能收到模型回复，或收到明确的失败提示。
5. `python -m unittest discover -s tests` 可以通过。
