# Troubleshooting

本文件记录可复现或高成本的开发环境故障。每条记录包含现象、原因判断、恢复办法和预防措施。

## 2026-07-31：前端验证异常等待约 47 分钟

### 现象

在 Windows Codex 工作区内验证扩展前端时，一次组合命令长时间没有返回。工具记录该执行单元耗时 `2803.5` 秒（约 46 分 43 秒），但随后读取结果时显示命令本身只用了约 `2.5` 秒并正常退出。同期还出现：

- `pnpm typecheck` / `pnpm build` 因无交互终端触发 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`。
- 从仓库根目录直接调用 Vite 时找不到 `sidepanel.html`。
- Vite 清空 `extension/dist/assets` 时因 Windows 文件占用或权限限制报 `EPERM`。
- Playwright 通过 npx 启动时，npm 缓存目录创建临时文件报 `EPERM`。

### 原因判断

主要耗时不是 TypeScript 编译或文件清理，而是 Codex 工具执行单元、子进程状态或结果回传出现异常等待。依据是工具显示约 47 分钟墙钟时间，而同一执行单元最终报告的实际命令时间只有约 2.5 秒。

放大因素包括：

1. 把类型检查、构建和清理组合在同一命令中，无法快速判断具体卡点。
2. pnpm 检测到现有 `node_modules` 与当前运行环境不一致，尝试进行需要交互确认的目录处理。
3. Vite 命令工作目录错误，入口文件相对于错误目录解析。
4. `extension/dist` 或 npm 缓存被其他进程占用，触发 Windows `EPERM`。
5. 对失败命令进行多轮串行重试，累计增加等待时间。

### 解决办法

将验证步骤拆开，并给每一步设置独立、较短的超时时间：

```powershell
# 在仓库根目录执行类型检查
.\extension\node_modules\.bin\tsc.CMD -b extension\tsconfig.json --pretty false

# 在 extension 目录执行 Vite
Set-Location .\extension
.\node_modules\.bin\vite.CMD build `
    --configLoader runner `
    --outDir ..\verify-dist `
    --emptyOutDir false
```

构建成功后，只清理经过绝对路径校验的临时目录：

```powershell
$verifyPath = (Resolve-Path -LiteralPath '..\verify-dist').Path
if ($verifyPath -eq 'D:\learn\gpt\ozonslj\verify-dist') {
    Remove-Item -LiteralPath $verifyPath -Recurse -Force
}
```

如果必须使用 pnpm，在无交互环境中先设置：

```powershell
$env:CI = 'true'
pnpm typecheck
pnpm build
```

如果 npm 或 Playwright 缓存仍报 `EPERM`，先确认没有遗留的 Node、Vite 或浏览器自动化进程，再使用已批准的非沙箱执行权限；不要循环重试同一个失败命令。

### 预防措施

- 不把类型检查、生产构建、截图和临时目录清理放进同一个长命令。
- 首次无输出超过合理时间时终止并分步诊断，不等待几十分钟。
- Vite 始终从 `extension` 目录运行，或显式提供正确的 root/入口。
- 被占用的 `dist` 不作为验证输出目录；使用工作区内独立的 `verify-dist`。
- Playwright 在一个浏览器会话内完成导航与多张截图，减少重复 npx 和浏览器启动。
- 记录每条验证命令的退出码；超时或被终止的命令不得计为通过。
