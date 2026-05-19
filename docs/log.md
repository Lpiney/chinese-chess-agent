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
