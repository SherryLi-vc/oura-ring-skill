# oura-ring

[![License: MIT](https://img.shields.io/github/license/SherryLi-vc/oura-ring-skill)](./LICENSE)

[English](./README.md) · **简体中文**

> 一个 Agent Skill：让你的 AI 助手通过 Oura 官方 Cloud API v2 读取**你本人**的 Oura Ring 数据，并且只汇总给你本人看。

**是什么：** 一份可移植的 `SKILL.md`（Agent Skills 格式），附 Python 标准库脚本，用于一次性完成 OAuth2 授权，并读取每日睡眠、活动、准备度、血氧（SpO2）和心率序列。

**给谁用：** 戴 Oura Ring、想让 AI 助手按日期范围汇总自己评分和趋势的人。

**不是什么：** 不是医疗建议，也不是 Oura 官方产品。本项目为非官方社区 skill，Oura 为其所有者的商标。仓库里不含任何令牌或密钥。

- **OAuth2 + PKCE**：授权码流程并校验 state。Oura 已于 2025 年 12 月停用个人访问令牌。
- **自动续期**：遇到 401 自动刷新一次，并把新的一次性刷新令牌原子回写到权限为 600 的文件。
- **凭据位置自定**：先读环境变量，其次读 `OURA_ENV_FILE`，默认读 `~/.config/oura/oura.env`。
- **五类数据，自动翻页**：`daily_sleep`、`daily_activity`、`daily_readiness`、`daily_spo2`、`heartrate`（或 `all`），按 `next_token` 读完所有页。
- **本地时区默认值**：默认取你所在时区最近 7 个日历日，可用 `--tz` 覆盖；支持 `--summary`、`--json`、`--dry-run`。
- **轻量通用**：标准 `SKILL.md`；只需 Python 3.9+ 标准库。

## 快速开始

**1. 安装**到通用用户级目录（其他宿主见[安装](#安装)）：

    git clone https://github.com/SherryLi-vc/oura-ring-skill.git ~/.agents/skills/oura-ring

**2. 注册 Oura 应用并创建凭据文件**：见[一次性 OAuth2 配置](#一次性-oauth2-配置)第 1–3 步。

**3. 授权并验证：**

    cd ~/.agents/skills/oura-ring
    python3 scripts/oura_auth.py authorize
    python3 scripts/oura_fetch.py daily_sleep --days 3 --summary

## 安装

仓库根目录就是技能文件夹；将其克隆或复制到技能目录，并确保文件夹名称与技能 `name` 一致（`oura-ring`）。脚本须与 `SKILL.md` 放在同一目录。

Codex、Cursor、Gemini CLI 和 OpenCode 均可读取的用户级目录：

```sh
git clone https://github.com/SherryLi-vc/oura-ring-skill.git ~/.agents/skills/oura-ring
```

Claude Code（Cursor 和 OpenCode 也可读取）：

```sh
git clone https://github.com/SherryLi-vc/oura-ring-skill.git ~/.claude/skills/oura-ring
```

Gemini CLI 也可使用：

```sh
gemini skills install https://github.com/SherryLi-vc/oura-ring-skill.git
```

项目级安装：将文件夹放在项目的 `.agents/skills/oura-ring/`（或 `.claude/skills/oura-ring/`）下。其他支持加载 `SKILL.md` 文件夹的宿主可复制整个文件夹，包括同级脚本。

| 宿主 | 调用方式 |
|---|---|
| 所有宿主 | 当技能描述与请求匹配时自动加载。 |
| Claude Code | `/oura-ring` |
| Codex | `$oura-ring`（也可通过技能列表使用 `/oura-ring`） |
| Cursor | 使用 `/` 菜单。 |
| Gemini CLI | 通过 `activate_skill` 流程加载。 |

**兼容性：**[Agent Skills 规范](https://agentskills.io/specification)；[Claude Code](https://code.claude.com/docs/en/skills)；[OpenAI Codex](https://developers.openai.com/codex/skills)；[Cursor](https://cursor.com/docs/context/skills)；[Gemini CLI](https://geminicli.com/docs/cli/skills/)；[OpenCode](https://opencode.ai/docs/skills/)。

## 一次性 OAuth2 配置

1. 在 [Oura Cloud API 应用页面](https://cloud.ouraring.com/oauth/applications)注册应用，填写名称、网站和重定向 URI。已登记的重定向 URI 是白名单，必须完全一致。部分用户反馈 `http://localhost:8080/callback` 可用；如果门户不接受，请使用自己控制的 HTTPS 地址。
2. 复制 Client ID 和 Client Secret。妥善保管 Secret。应用获 Oura 批准前最多可供 10 位用户使用，个人使用不受影响。
3. 创建凭据文件（替换占位内容，不要保留尖括号），并限制文件权限：

   ```sh
   mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/oura"
   chmod 700 "${XDG_CONFIG_HOME:-$HOME/.config}/oura"
   cat > "${XDG_CONFIG_HOME:-$HOME/.config}/oura/oura.env" <<'EOF'
   OURA_CLIENT_ID=your_client_id
   OURA_CLIENT_SECRET=your_client_secret
   OURA_REDIRECT_URI=http://localhost:8080/callback
   OURA_SCOPES="daily heartrate spo2"
   EOF
   chmod 600 "${XDG_CONFIG_HOME:-$HOME/.config}/oura/oura.env"
   ```

   也可通过 `OURA_ENV_FILE` 指定其他 dotenv 格式文件。每个键均优先读取环境变量。
4. 在 Oura 授权页面选择 `daily`、`heartrate` 和 `spo2` 权限。也可通过 `OURA_SCOPES` 修改请求范围。Oura 认证文档将 `heartrate` 范围描述为“面向 Gen 3 用户的心率时间序列”。
5. 运行 `python3 scripts/oura_auth.py authorize`。打开输出的链接并同意授权，然后粘贴完整重定向 URL。如果重定向页面打不开，可复制地址栏 URL。流程会验证 state 并使用 PKCE。
6. 检查配置并获取示例数据：

   ```sh
   python3 scripts/oura_auth.py status
   python3 scripts/oura_fetch.py daily_sleep --days 3 --summary
   ```

配置了刷新凭据时，遇到 401 后会自动刷新访问令牌。Oura 刷新令牌只能使用一次；脚本会立即保存新刷新令牌和访问令牌。Oura 也提供用于持续更新的 webhooks；本技能按需轮询，无需使用它们。

## 获取数据

```sh
python3 scripts/oura_fetch.py daily_sleep --days 7 --summary
python3 scripts/oura_fetch.py all --start 2026-10-24 --end 2026-10-31 --summary
python3 scripts/oura_fetch.py heartrate --days 3 --tz America/Los_Angeles --json
```

未指定 `--start` 和 `--end` 时，默认获取用户本地时区最近七个日历日的数据。可用 `--tz` 和 IANA 时区名称覆盖。`--dry-run` 只打印请求，不访问网络。所需权限为 `daily heartrate spo2`。

## 故障排查

| 问题 | 检查方法 |
|---|---|
| `invalid_request` 或重定向地址不匹配 | 重定向 URI 必须与注册值完全一致；必要时注册自己控制的 HTTPS 地址。 |
| 400 / 422 | 400 = 查询参数验证错误（文档）；422 = 验证错误（OpenAPI）。 |
| 401 | 检查令牌；配置完整时脚本会尝试刷新一次，否则重新授权。 |
| 403 | 检查授权范围和 Oura 会员状态。请求会携带非空 User-Agent。 |
| 429 | 脚本会根据 `Retry-After` 等待并重试一次；仍受限时稍后再试。 |
| 缺少权限 | 重新授权并授予所需的 `daily`、`heartrate` 或 `spo2` 权限。 |
| `access_denied` | 用户拒绝了授权；重新发起授权并同意所需权限。 |

## 隐私与安全

健康数据仅供用户本人使用。不要发布给其他人、频道或共享日志。不要分享令牌或 Client Secret，也不要将原始 API 响应写入共享日志。请使用 OAuth2；个人访问令牌已于 2025 年 12 月弃用且不再提供。不要抓取 Cookie 或伪造凭据。

## 非医疗建议

此技能只汇总 Oura 测量数据，不用于诊断或提供用药建议。如数值令人担忧，请咨询临床医生。

## 来源

- [认证](https://cloud.ouraring.com/docs/authentication)
- [Oura API v2 文档](https://cloud.ouraring.com/v2/docs)（[OpenAPI](https://cloud.ouraring.com/v2/static/json/openapi-1.43.json)）
- [Oura API 文档](https://cloud.ouraring.com/docs/)
- [错误处理](https://cloud.ouraring.com/docs/error-handling)

## 许可证

MIT © 2026 SherryLi-vc
