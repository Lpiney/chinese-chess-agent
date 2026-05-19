# 项目需求说明

## 一、当前目标

当前项目目标已经升级为：

1. 做一个浏览器版中国象棋教学 Agent。
2. 玩家通过网页在左侧棋盘下棋。
3. Pikafish 负责给出强引擎最优走法。
4. DeepSeek `deepseek-v4-flash` 负责把引擎结论解释成自然中文。
5. 右侧提供类微信 / WhatsApp 风格聊天窗口，允许玩家随时提问。

## 二、当前范围

当前版本必须覆盖：

1. 标准中国象棋初始棋盘。
2. 棋子合法走法与将军合法性校验。
3. 浏览器棋盘交互与落点提示。
4. 官方 Pikafish Git submodule 接入。
5. 三档机器人难度。
6. LLM 聊天侧栏。
7. LLM 分析链路：
   用户提问 → 先读取当前棋局 → 交给 Pikafish 分析 → 把引擎结论发给 DeepSeek → 返回逻辑解释。

## 三、项目结构要求

项目结构参考 `Lpiney/chess-agent` 的扁平主模块方式：

1. `main.py` 作为 Flask Web 主入口。
2. `board.py` 负责棋盘规则。
3. `pikafish_engine.py` 负责引擎通信。
4. `board_serializer.py` 负责棋局文本化。
5. `deepseek_client.py` 负责 LLM API 调用。
6. `chess_agent.py` 负责引擎与 LLM 的编排。
7. `templates/` 和 `static/` 负责网页界面。
8. `config.example.yaml` 提供配置模板。
9. `requirements.txt` 管理 Python 依赖。

## 四、运行环境要求

### 1. Python 版本

建议使用 `Python 3.11`。

### 2. Conda 环境

```bash
conda env create -f env/conda-environment.yml
conda activate chinese-chess-agent
```

项目新增了 `env/` 目录，用于集中存放环境文件。

### 3. Python 依赖

```bash
pip install -r requirements.txt
```

当前 Python 依赖：

1. `Flask`
2. `openai`
3. `PyYAML`

### 4. 系统工具

需要以下工具来拉取和编译 Pikafish：

1. `git`
2. `make`
3. `g++` 或 `clang++`

### 5. Pikafish 初始化

推荐使用：

```bash
bash scripts/setup_pikafish.sh
```

或者手动执行：

```bash
git submodule update --init --recursive
cd third_party/Pikafish/src
make -j build ARCH=native
cd ../../..
```

## 五、DeepSeek 配置要求

先复制配置：

```bash
cp config.example.yaml config.yaml
```

然后填写：

1. `api_key`
2. `base_url`
3. `model_name`

默认模型名为：

```text
deepseek-v4-flash
```

说明：

1. `env/` 目录负责存放环境文件。
2. 根目录下的 `config.yaml` 负责存放你自己的本地密钥配置。

## 六、运行与测试

运行项目：

```bash
python main.py
```

然后在浏览器打开：

```text
http://127.0.0.1:5000
```

停止项目：

```bash
bash scripts/stop_web.sh
```

运行测试：

```bash
python -m unittest discover -s tests
```

## 七、文档与日志要求

1. 每次更新代码后同步更新 `README.md`。
2. 每次更新代码后同步更新 `docs/log.md`。
3. 文档优先使用中文。
