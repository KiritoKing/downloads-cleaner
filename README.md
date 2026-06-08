# downloads-cleaner

macOS Downloads 自动分类与安全清理工具。它按 TOML 规则整理 `~/Downloads` 根目录文件，并把过期归档文件移动到 `_trash_candidate`，不直接删除用户文件。

## 安装

开发运行：

```bash
cd downloads-cleaner
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
```

安装为当前用户可用的命令：

```bash
python3.11 -m pip install --user .
```

安装 LaunchAgent：

```bash
./scripts/install-launchd.sh
```

安装脚本会创建虚拟环境、安装本项目、复制默认配置到 `~/.config/downloads-cleaner/rules.toml`，并注册用户级 LaunchAgent。

如果本机 `python3` 指向低于 3.11 的系统 Python，可显式指定：

```bash
DOWNLOADS_CLEANER_PYTHON="$(command -v python3.11)" ./scripts/install-launchd.sh
```

## 配置

默认配置文件：

```txt
~/.config/downloads-cleaner/rules.toml
```

项目内模板：

```txt
rules.toml
```

新增分类时，在 `[[rules]]` 中增加规则：

```toml
[[rules]]
name = "invoices"
target = "documents/invoices"
filename_patterns = ["*invoice*", "*receipt*", "*发票*", "*收据*"]
extensions = ["pdf", "png", "jpg"]
```

规则按顺序匹配，先命中先执行；同一规则内多个条件是 AND。

## 使用

先 dry-run：

```bash
downloads-cleaner run --config ~/.config/downloads-cleaner/rules.toml --dry-run --verbose
```

正式执行：

```bash
downloads-cleaner run --config ~/.config/downloads-cleaner/rules.toml
```

只分类，不清理旧文件：

```bash
downloads-cleaner run --no-cleanup
```

只执行 cleanup：

```bash
downloads-cleaner run --only-cleanup
```

校验配置：

```bash
downloads-cleaner validate-config --config ~/.config/downloads-cleaner/rules.toml
```

打印计划：

```bash
downloads-cleaner print-plan --dry-run --verbose
```

## launchd

检查服务：

```bash
launchctl print gui/$(id -u)/com.local.downloads-cleaner
```

立即触发：

```bash
launchctl kickstart -k gui/$(id -u)/com.local.downloads-cleaner
```

卸载：

```bash
./scripts/uninstall-launchd.sh
```

卸载脚本不会删除配置、日志或已整理文件。

## 日志

默认日志：

```txt
~/Library/Logs/downloads-cleaner.log
```

launchd stdout/stderr：

```txt
~/Library/Logs/downloads-cleaner.out
~/Library/Logs/downloads-cleaner.err
```

## 安全策略

- 不直接删除用户文件。
- `direct_delete = true` 会被拒绝。
- cleanup 只移动到 `~/Downloads/_trash_candidate`。
- 默认只扫描 `~/Downloads` 根目录，不递归处理管理目录。
- 跳过下载中临时文件、隐藏文件、目录、刚修改文件和超过配置大小的文件。
- 目标冲突默认重命名为 `foo (1).ext`。
- 单文件异常会记录日志，不中断整轮任务。

## 常见问题

### 为什么文件没有被移动？

常见原因是文件太新、是隐藏文件、正在下载、超过大小限制，或位于 `_sorted`、`_inbox_review`、`_trash_candidate` 管理目录内。查看日志可看到 skip reason。

### 为什么刚下载完不会立刻移动？

配置里的 `safety.min_age_seconds` 默认是 120 秒，用来避免移动仍在写入的文件。

### 如何新增分类？

编辑 `~/.config/downloads-cleaner/rules.toml` 的 `[[rules]]`。更具体的规则应放在更通用规则前面，例如 screenshots 应在 images 前。

### 如何恢复误移动文件？

从 `~/Downloads/_sorted`、`~/Downloads/_inbox_review` 或 `~/Downloads/_trash_candidate` 手动移回需要的位置。本工具不会永久删除文件。

### 如何完全停用？

运行：

```bash
./scripts/uninstall-launchd.sh
```

然后保留或手动删除配置、日志和 Downloads 内的管理目录。
