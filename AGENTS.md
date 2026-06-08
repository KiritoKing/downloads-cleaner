# AGENTS.md

## 项目定位

- 项目代码位于当前仓库根目录。
- 默认配置安装路径是 `~/.config/downloads-cleaner/rules.toml`。
- 默认日志路径是 `~/Library/Logs/downloads-cleaner.log`。
- LaunchAgent 路径是 `~/Library/LaunchAgents/com.local.downloads-cleaner.plist`。

## 安全边界

- 禁止直接删除、`rm`、`unlink` 用户下载文件。
- cleanup 只能移动到 `_trash_candidate`，不能永久删除。
- 修改真实 `~/Downloads` 前必须先 dry-run。
- 不要自动执行 `scripts/install-launchd.sh`，除非用户明确要求安装或启用定时任务。
- 不要覆盖已有 `~/.config/downloads-cleaner/rules.toml`。

## 开发约束

- 核心实现保持 Python 3.11 标准库，测试使用 pytest。
- 优先使用 `.venv/bin/python` 或显式 Python 3.11+ 解释器。
- 修改代码后运行 `.venv/bin/python -m pytest`。
- 配置变更后运行 `PYTHONPATH=src python3.11 -m downloads_cleaner.main validate-config --config rules.toml`。
- 测试必须使用临时目录，不允许触碰真实 `~/Downloads`。
- 先沿用现有模块职责，不做无关重构。

## 跨 Agent 交接

- 每次完成实质修改后更新 `HANDOFF.md`。
- `HANDOFF.md` 必须包含当前状态、验证命令、结果、未完成事项和下一步命令。
- 如果任务中断，下一个 agent 应能只读 `HANDOFF.md` 后继续。
