version: 0.1.0
date: 2026-05-19
description:
- 重写 README，明确当前阶段目标是先实现最小可运行的中国象棋棋盘程序。
- 重写 requirements，收敛第一阶段范围，只保留基础棋盘与走子规则需求。
- 新增 src/board.py，实现棋盘初始化、终端显示、走子校验、将军检查和胜负判断。
- 新增 src/main.py，提供最小命令行对局入口。
- 新增 tests/test_board.py，补充基础规则测试。

version: 0.1.1
date: 2026-05-19
description:
- 在 requirements 中补充 Conda 环境建议。
- 在 requirements 中补充推荐 Python 版本为 3.11。
- 在 requirements 中说明当前版本不需要额外安装第三方 pip 包。

version: 0.2.0
date: 2026-05-19
description:
- 新增 tkinter 桌面图形界面，支持鼠标点击选择棋子和落子。
- 新增合法落点高亮提示，帮助玩家直观看到当前棋子可以走到的位置。
- 默认启动入口改为桌面界面，不再默认使用终端交互方式。
- 更新 README 和 requirements，补充桌面版运行方式与 tkinter 依赖说明。
- 补充 get_valid_moves 相关测试，确保图形界面依赖的合法走法查询功能可用。

version: 0.3.0
date: 2026-05-19
description:
- 新增走子动画，让棋子在棋盘上平滑移动。
- 新增内置机器人对手，默认由玩家执红、机器人执黑。
- 新增三档机器人难度：beginner、medium、master。
- 新增 ai 模块，并补充机器人与棋盘克隆相关测试。
- 更新 README 和 requirements，补充动画、机器人和难度说明。

version: 0.4.0
date: 2026-05-19
description:
- 将机器人从本地简易 AI 切换为官方 Pikafish 子模块引擎。
- 新增 Pikafish UCI 封装，支持通过外部进程获取 bestmove。
- 新增棋盘到 FEN 和 UCI 坐标转换逻辑，用于与 Pikafish 通信。
- 更新图形界面，使机器人走子改为由 Pikafish 驱动，并保留动画与三档难度。
- 更新 README 和 requirements，补充子模块初始化、编译步骤和系统工具要求。

version: 0.4.1
date: 2026-05-19
description:
- 新增 .gitignore，忽略 Python 缓存文件和 Pikafish 编译产物。
- 新增 scripts/setup_pikafish.sh，提供子模块初始化和引擎编译的一键脚本。
- 更新 README 和 requirements，补充脚本使用方式与 Git 说明。

version: 0.5.0
date: 2026-05-19
description:
- 参考 Lpiney/chess-agent 的结构，将项目重构为根目录主模块风格。
- 新增 board_serializer.py、deepseek_client.py、chess_agent.py 和 config.example.yaml。
- 新增 requirements.txt，补充 DeepSeek 所需 Python 依赖。
- 将主入口改为 main.py，并重建 GUI 为左侧棋盘 + 右侧聊天侧栏布局。
- 聊天侧栏接入 DeepSeek v4 flash，分析流程改为先由 Pikafish 求最优步，再由 LLM 解释原因。
- 更新测试到新结构，并补充序列化提示词相关测试。
- 更新 README 和 docs/requirements，补充新结构、DeepSeek 配置和运行说明。

version: 0.5.1
date: 2026-05-19
description:
- 新增 env 目录，用于集中存放环境相关文件。
- 新增 env/conda-environment.yml，支持一键创建 Conda 环境。
- 新增 env/README.md，说明环境创建与本地配置方式。
- 更新 README 和 docs/requirements，将环境准备流程切换到 env 目录。

version: 0.5.2
date: 2026-05-19
description:
- 将 DeepSeek 默认 base_url 修正为 https://api.deepseek.com。
- 修复右侧聊天栏显示异常，补充聊天区域宽度同步逻辑。
- 调整聊天侧栏颜色对比，增强标题、正文和输入区域可见性。

version: 0.6.0
date: 2026-05-19
description:
- 将前端从 Tkinter 窗口重构为 Web 页面。
- 新增 Flask 后端入口，提供棋盘状态、走子、重置、难度切换和聊天 API。
- 新增 templates/index.html 与 static/app.css、static/app.js，实现浏览器棋盘和网页聊天侧栏。
- 保留 Pikafish 与 DeepSeek 分析链路，但改由 Web 界面驱动。
- 更新 README、requirements 与 env 文档，切换为浏览器运行说明。

version: 0.6.1
date: 2026-05-19
description:
- 新增 scripts/stop_web.sh，用于停止本地 Web 服务。
- 更新 README 和 docs/requirements，补充停止服务的方法。

version: 0.7.0
date: 2026-05-21
description:
- 将聊天模型接入从 DeepSeek 配置重构为通用百炼兼容配置，默认模型改为 qwen3.6-max-preview。
- 新增 llm_client.py，并保留 deepseek_client.py 兼容壳，避免旧导入路径失效。
- 更新 config.example.yaml、README、env/README 和前端标题文案，统一切换到阿里云百炼 / Qwen 配置说明。
- 收缩 chess_agent.py 与 course_manager.py 中的系统提示词，只保留必要约束，减少对模型表达和推理的过度限制。
- 删除课程 JSON 中逐课硬编码的 system_prompt 字段，改为仅保留课程主题、说明和节内容。

version: 0.7.1
date: 2026-05-21
description:
- 将 /api/chat 与 /api/course/chat 改为基于 SSE 的流式输出接口。
- 更新 static/app.js，新增流式响应解析、聊天气泡增量刷新和课程模式流式渲染逻辑。
- 保留课程模式的重写与兜底回复机制，但改为在流式完成后统一收尾。
- 修复流式展示中误把模型 reasoning_content 当作正文输出的问题，侧边栏仅显示最终可见内容。

version: 0.7.2
date: 2026-05-21
description:
- 在 llm_client.py 中默认向百炼兼容接口传入 enable_thinking=false，并关闭 preserve_thinking，降低回复延迟。
- 更新 config.example.yaml 与 README，明确 qwen3.6-max-preview 默认关闭思考模式。

version: 0.7.3
date: 2026-05-21
description:
- 为棋盘增加 UCI 坐标显示，前端棋盘现在直接显示 a-i 列与 9-0 行，便于和 LLM 回复中的格子名对齐。
- 在 board_serializer.py 中补充终局状态与坐标说明，并把棋子清单改为同时包含 UCI 坐标和内部 row/col。
- 在棋盘规则层补充“无合法应法即终局”的判定，使对面笑等将死局面无需吃将也会直接判胜。
- 调整课程模式与自由模式的状态文案和胜利提示，使课程中走成将死后界面会立即提示本节已结束。
- 更新 chess_agent.py 与 course_manager.py，在提示词中明确要求模型遇到终局时按终局解释，不再假设对方仍有后续应法。
- 补充测试，覆盖 FEN 还原、对面笑将死判胜、提示词坐标说明和棋子清单坐标输出。

version: 0.7.4
date: 2026-05-21
description:
- 收窄发给模型的坐标上下文，只保留 UCI 坐标，不再混入 row/col 说明，减少模型自我校对和坐标推导噪音。
- 在 chess_agent.py 中补充回复清洗逻辑，过滤“修正分析”“重新审视”“Final check”等中间分析痕迹。
- 收紧聊天输出风格，默认控制在 2 到 4 句内，并下调 max_tokens 以减少冗长回复。
- 修复课程模式首节理论页显示为标准开局的问题；进入课程后若当前节无 FEN，会优先显示后续最近的课程局面。
- 在聊天输入区新增“快捷提问”和“清空聊天”按钮，自由对弈和课程模式会自动发送不同的快捷问题。
- 将课程数据在加载时归一为“课程讲解 + 课后作业”两步，简化课程流程。
- 调整课程模式走子逻辑，玩家走完后会自动帮对手应招，不再需要手动替对方挪棋。
- 进一步将棋盘四周坐标标签外移，避免边线棋子遮挡坐标文字。
- 补充测试，覆盖课程压缩、课程首局面载入和课程模式自动应手。
