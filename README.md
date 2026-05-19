## 项目简介

本项目是一个面向 Python 初学者的中国象棋 Agent 学习项目。

当前阶段的目标不是一次性完成完整的智能体系统，而是先从最基础的棋盘和走子规则开始，逐步搭建一个清晰、容易学习、方便扩展的项目。

项目后续计划会逐步加入以下能力：

1. 中国象棋棋盘与规则引擎。
2. 与象棋引擎对接，让机器人可以自动走子。
3. 接入大模型，对机器人推荐走法进行讲解。
4. 通过完整项目帮助初学者学习 Python 语法、模块化设计、测试和文档维护。

## 当前版本功能

当前版本已经实现桌面版中国象棋棋盘程序，包含以下内容：

1. 初始化标准中国象棋棋盘。
2. 在桌面窗口中显示棋盘。
3. 支持鼠标点击选择棋子和落点。
4. 支持高亮显示当前棋子的合法落点。
5. 支持流畅的走子动画效果。
6. 使用官方 Pikafish 子模块作为黑方对手。
7. 支持三档机器人难度：`Beginner`、`Medium`、`Master`。
8. 支持红黑双方轮流下棋。
9. 按照中国象棋基本规则校验走法。
10. 支持将军合法性检查，避免己方老将暴露。
11. 提供基础自动化测试。

当前版本不包含以下能力：

1. LLM 棋局讲解。
2. 对局存档与复盘。

## 项目结构

```text
chinese-chess-agent/
├── .gitmodules
├── README.md
├── docs/
│   ├── log.md
│   └── requirements.md
├── src/
│   ├── __init__.py
│   ├── board.py
│   ├── gui.py
│   └── main.py
│   └── pikafish_engine.py
├── third_party/
│   └── Pikafish/
└── tests/
    └── test_board.py
```

## 运行方法

先初始化子模块并编译 Pikafish：

```bash
git submodule update --init --recursive
cd third_party/Pikafish/src
make -j build ARCH=native
cd ../../..
```

也可以直接执行一键脚本：

```bash
bash scripts/setup_pikafish.sh
```

确保本机安装了 Python 3，并且本地 Python 带有 `tkinter` 图形库。

运行命令：

```bash
python3 -m src.main
```

程序启动后，会打开桌面棋盘窗口。

操作方式：

1. 玩家默认执红，机器人默认执黑。
2. 点击当前行棋方的棋子。
3. 棋盘会高亮显示该棋子的合法落点。
4. 再点击目标位置完成走子。
5. 走子时会播放平滑动画。
6. 玩家走完后，机器人会自动思考并落子。
7. 顶部可以切换机器人难度：`Beginner`、`Medium`、`Master`。

## 引擎说明

当前项目使用 [official-pikafish/Pikafish](https://github.com/official-pikafish/Pikafish) 作为官方子模块引擎。

图形界面通过 UCI 协议与 Pikafish 通信，三档难度通过不同搜索时间和深度实现：

1. `Beginner`：较短思考时间，适合新手。
2. `Medium`：中等思考时间，适合一般玩家。
3. `Master`：更深搜索，适合较强对手。

## Git 说明

当前仓库已经按 Git submodule 方式接入 Pikafish。

建议首次克隆后执行：

```bash
git submodule update --init --recursive
```

## 运行测试

```bash
python3 -m unittest discover -s tests
```

## 开发原则

本项目遵循以下原则：

1. 代码尽量简单清晰，适合初学者阅读。
2. 关键逻辑使用中文注释说明。
3. 每次更新都同步维护测试。
4. 每次更新都同步维护 README 和日志。

## 后续计划

在当前版本基础上，下一阶段会考虑：

1. 强化机器人棋力。
2. 加入悔棋、复盘和重新开局之外的更多控制项。
3. 加入大模型讲解能力。
