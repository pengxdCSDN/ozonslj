# Seller 同步快照接口

四类接口都先执行领域映射和数据质量校验，再按当前工作区保存 PostgreSQL JSONB 快照。接口不会调用 Ozon 写入能力。

| 类型  | 接口                                                                          | 说明                    |
| --- | --------------------------------------------------------------------------- | --------------------- |
| 商品  | `POST /v1/seller/products/store-workspaces/{workspace_id}/sync-and-save`    | 保存商品、价格和可售库存摘要        |
| 库存  | `POST /v1/seller/stock/store-workspaces/{workspace_id}/sync-and-save`       | 保存商品/仓库库存快照           |
| 订单  | `POST /v1/seller/orders/store-workspaces/{workspace_id}/sync-and-save`      | 保存订单状态、金额和下单时间摘要      |
| 履约  | `POST /v1/seller/fulfillment/store-workspaces/{workspace_id}/sync-and-save` | 保存 FBO/FBS posting 摘要 |

约束：

- 工作区不存在返回 `404 workspace_not_found`。
- 上游数据映射失败返回 `422`，不写入快照。
- 快照来源固定为 `seller_api`，金额使用最小货币单位整数。
- `items` 必须为 JSON 数组，空游标不得写入。
- 订单、库存和履约接口拒绝当前页重复事实；商品接口拒绝重复商品仓库之外的非法字段类型。
- 自动化测试使用 Stub/Mock，不访问真实 Ozon 账号。
## 2026-08-09 开发状态同步

- 四类快照均支持 PostgreSQL 保存与历史查询；快照查询只返回内部模型字段，不透传上游原始敏感响应。
- 分页同步逐页落库但仅在全量成功后推进水位；失败任务保留可恢复状态。
- 当前实现仍为 Stub/适配端口，真实 Ozon 接入前必须确认官方路径、版本、权限、分页、限流和错误契约。
