# Ozon Performance API 凭据闭环

Performance API 使用独立的服务账号 Client Credentials，不复用 Seller API 的 Client ID、API Key 或浏览器会话。

## 配置流程

1. 在 Ozon 后台创建 Performance 服务账号，取得 Client ID 和 Client Secret。
2. 进入“系统工具 → Performance 凭据（配置与状态）”。
3. 保存 Client ID 和 Client Secret；后端使用凭据保护器加密保存，浏览器不持久化密钥。
4. 点击“获取 Token 并测试连接”；后端调用 `https://performance.ozon.ru/api/client/token`，保存短期 access token 并返回脱敏状态。

## HTTP 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/v1/advertising/performance-oauth/store-workspaces/{workspace_id}/credentials` | 查询是否已配置密钥、是否已获取令牌和过期时间 |
| POST | `/v1/advertising/performance-oauth/store-workspaces/{workspace_id}/client-credentials` | 加密保存 Client ID 与 Client Secret |
| POST | `/v1/advertising/performance-oauth/store-workspaces/{workspace_id}/token` | 获取并加密保存 access token |

## 状态和排错

“密钥已配置、令牌未获取”是正常中间状态，点击获取 Token 即可继续。401/403 通常表示服务账号、组织权限或密钥不匹配；不要填 Seller API API Key。任何 token、secret、完整 Client ID 和外部响应都不得写入日志、浏览器存储或 Git。

当前闭环先覆盖认证与连接验证；广告活动、报表等真实只读同步必须在 Performance API 账号具备相应权限后，通过独立适配器接入，不能猜测接口路径或把认证接口当作业务数据接口。
