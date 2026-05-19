# 项目需求说明

## 一、项目目标

本项目旨在构建一个适合 Python 初学者学习的中国象棋 Agent 示例项目。

当前第一阶段的目标非常明确：

1. 先实现一个可以正常下中国象棋的基础棋盘程序。
2. 保证代码结构清楚，方便后续继续接入象棋引擎和大模型。
3. 让初学者能够通过真实项目学习 Python 基础语法、函数、类、模块和测试。

## 二、当前阶段范围

本阶段的核心目标调整为“做一个可以在桌面窗口中直接操作的中国象棋棋盘程序”。

需要完成的内容：

1. 创建标准中国象棋初始棋盘。
2. 支持桌面窗口显示棋盘。
3. 支持鼠标点击选择棋子。
4. 支持提示当前棋子的合法落点。
5. 支持流畅的走子动画。
6. 使用官方 Pikafish 作为机器人对手。
7. 通过 Git submodule 管理 Pikafish 源码。
8. 支持三档对战难度：`beginner`、`medium`、`master`。
9. 支持红黑双方轮流走子。
10. 校验各个棋子的基本走法规则。
11. 禁止吃掉己方棋子。
12. 禁止走出棋盘。
13. 禁止让己方老将处于被将军状态。
14. 支持一方老将被吃后结束对局。

本阶段暂不实现的内容：

1. 象棋引擎接入。
2. LLM 讲解功能。
3. 联网对战。
4. 对局保存与复盘。

## 三、代码要求

1. 所有代码尽量使用简单、直接、容易理解的写法。
2. 关键逻辑使用中文注释。
3. 模块划分清楚，避免把所有逻辑写在一个文件里。
4. 优先选择稳定、容易复现、适合初学者的方案。
5. 当前图形界面优先使用 `tkinter`，因为它随大多数 Python 发行版提供，便于快速运行。

## 四、测试要求

1. 为核心规则编写自动化测试。
2. 至少覆盖常见棋子走法校验。
3. 至少覆盖轮流走子和非法走子场景。
4. 每次功能更新后，同步补充或修改测试。

## 五、运行环境要求

### 1. 建议的 Python 版本

当前项目建议使用 `Python 3.11`。

原因如下：

1. 语法和类型标注支持较完整。
2. 与当前项目代码兼容性好。
3. 对初学者来说比较稳定，资料也比较多。

如果使用 `Python 3.10`，当前版本通常也可以运行。
不建议使用过低版本，例如 `Python 3.9` 及以下，以免后续类型写法和语法兼容性变差。

### 2. 建议的 Conda 环境

建议创建独立环境，例如：

```bash
conda create -n chinese-chess-agent python=3.11
conda activate chinese-chess-agent
```

### 3. 系统工具要求

当前版本除了 Python 以外，还依赖以下系统工具：

1. `git`
2. `make`
3. 可用的 C++ 编译器，例如 `g++` 或 `clang++`

因为 Pikafish 需要以 Git 子模块方式拉取源码，并在本地编译生成可执行文件。

### 4. Pikafish 子模块与编译要求

初始化子模块：

```bash
git submodule update --init --recursive
```

或者执行：

```bash
bash scripts/setup_pikafish.sh
```

编译 Pikafish：

```bash
cd third_party/Pikafish/src
make -j build ARCH=native
cd ../../..
```

编译完成后，默认会生成可执行文件：

```text
third_party/Pikafish/src/pikafish
```

项目根目录建议保留 `.gitignore`，避免把 Pikafish 编译产物和 Python 缓存文件提交到仓库。

### 5. 图形界面依赖说明

当前版本的桌面界面使用 `tkinter`。

`tkinter` 一般不需要通过 `pip install` 单独安装，它通常会随 Python 一起提供。

当前代码使用的都是 Python 标准库：

1. `copy`
2. `math`
3. `random`
4. `unittest`
5. `tkinter`

如果你使用的是标准 Conda Python，通常可以直接运行。
如果运行时报错提示缺少 `tkinter`，需要先确认当前 Python 发行版是否包含 Tk 支持。

兜底安装命令：

```bash
conda install tk
```

### 6. 需要安装的 pip 包

当前版本不需要额外安装第三方 pip 包。

也就是说，创建好 Conda 环境后，理论上不需要执行 `pip install ...`，只要 Python 版本合适且 `tkinter` 可用即可直接运行。

### 7. 当前版本运行命令

运行项目：

```bash
python -m src.main
```

运行测试：

```bash
python -m unittest discover -s tests
```

### 8. 难度策略说明

由于 Pikafish 没有直接提供初学者等级开关，当前项目通过搜索时间、搜索深度和哈希大小来区分三档难度：

1. `beginner`
2. `medium`
3. `master`

### 9. 后续依赖策略

后续如果项目接入象棋引擎、LLM 或更复杂的图形界面，再根据实际需要增加第三方依赖。

在那之前，保持“无第三方依赖”更适合初学者学习和环境搭建。

## 六、文档要求

1. 每次更新代码后，同步更新 `README.md`。
2. 每次更新代码后，同步更新 `log.md`。
3. 文档内容优先使用中文，表达准确、简洁。

## 七、日志格式

`log.md` 统一使用下面格式记录版本变更：

```text
version: x.x.x
date: xxxx-xx-xx
description:
- 变更内容 1
- 变更内容 2
```
