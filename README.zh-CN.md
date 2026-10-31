# oura-ring

[![License: MIT](https://img.shields.io/github/license/SherryLi-vc/oura-ring-skill)](./LICENSE)

[English](./README.md) · **简体中文**

<!-- POSITIONING-PLACEHOLDER: tagline + opening paragraph to be written by the repo-description editor. Do not edit by hand. -->
用于通过 OAuth2 配置 Oura Ring 数据访问并获取个人健康摘要的技能。

本项目为非官方社区 skill，并非 Oura 官方产品。Oura 为其所有者的商标。

> 通过 Oura Cloud API 读取 Oura Ring 数据。

使用此技能授权访问 Oura 账户，并获取睡眠、准备度、活动、心率和血氧数据。

- **OAuth2 配置**：通过 Oura 和 PKCE 完成授权，并在本地安全保存凭据。
- **数据获取**：分页读取每日数据和心率数据。
- **简洁摘要**：查看指定日期范围内的每日评分和趋势。
- **隐私优先**：健康数据和凭据保留在用户设备上。

## 快速开始

1. 安装到文件夹 `oura-ring`。
2. 将 Client ID 和 Client Secret 写入 `~/.config/oura/oura.env`，或设置 `OURA_ENV_FILE` 指向该文件。
3. 进入技能文件夹（例如 `cd ~/.agents/skills/oura-ring`），运行 `python3 scripts/oura_auth.py authorize` 完成授权，再运行 `python3 scripts/oura_fetch.py daily_sleep --days 3 --summary` 验证。

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
Oura 也提供用于持续更新的 webhooks；本技能按需轮询，无需使用它们。

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

## 仓库简介 / Topics（占位）
<!-- ABOUT-TOPICS-PLACEHOLDER: to be filled by the repo-description editor -->
