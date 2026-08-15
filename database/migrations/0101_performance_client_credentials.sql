-- Performance API Client Credentials：保存服务账号密钥的加密值，令牌由后端按需获取。
BEGIN;

ALTER TABLE performance_oauth_credentials
    ADD COLUMN IF NOT EXISTS encrypted_client_id BYTEA,
    ADD COLUMN IF NOT EXISTS encrypted_client_secret BYTEA;

-- Client Credentials 首次保存时尚未获取 access token，因此令牌列必须允许为空；
-- 这也让“已保存密钥但尚未换取令牌”成为可明确表达的中间状态。
ALTER TABLE performance_oauth_credentials
    ALTER COLUMN encrypted_access_token DROP NOT NULL;

COMMENT ON COLUMN performance_oauth_credentials.encrypted_client_id IS
    'Ozon Performance 服务账号 Client ID 的加密值，不得返回浏览器或写入日志。';
COMMENT ON COLUMN performance_oauth_credentials.encrypted_client_secret IS
    'Ozon Performance 服务账号 Client Secret 的加密值，不得返回浏览器或写入日志。';

COMMIT;
