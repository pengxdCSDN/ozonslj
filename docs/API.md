# 前后端接口文档

## 1. 通用约定

- 基础地址：`http://127.0.0.1:8000`
- 数据格式：`application/json`
- 字符编码：UTF-8
- 时间格式：UTC ISO 8601
- 标识符：统一按字符串处理
- 当前版本前缀：业务接口使用 `/v1`
- 当前风险等级：只读

## 2. 通用错误格式

FastAPI 参数校验当前返回标准 `422` 结构。业务功能完善后统一为：

```json
{
  "error": {
    "code": "WORKSPACE_NOT_FOUND",
    "message": "店铺工作区不存在",
    "request_id": "req_xxx",
    "details": {}
  }
}
```

| 状态码 | 含义 |
|---|---|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求不符合业务规则 |
| 401 | 运营人员未认证 |
| 403 | 无权访问店铺工作区 |
| 404 | 资源不存在 |
| 409 | 重复操作或状态冲突 |
| 422 | 参数校验失败 |
| 429 | 请求过于频繁 |
| 502 | Ozon 上游响应异常 |
| 503 | 本地服务或上游暂不可用 |

## 3. 已实现接口

### 3.1 存活检查

`GET /health/live`

响应：

```json
{"status": "ok"}
```

### 3.2 就绪检查

`GET /health/ready`

响应：

```json
{"status": "ok"}
```

### 3.3 查询商品报价

`GET /v1/store-workspaces/{workspace_id}/product-offers`

路径参数：

| 参数 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `workspace_id` | string | 是 | 店铺工作区编号；当前仅支持 `local` |

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|---|---|---|---|---|
| `cursor` | string | 否 | 空 | 下一页游标 |
| `limit` | integer | 否 | 20 | 每页数量，范围 1～100 |

成功响应示例：

```json
{
  "items": [
    {
      "offer_id": "CN-MUG-420-BL",
      "ozon_product_id": "1847295031",
      "name": "双层保温杯 420ml",
      "price": "1290.00",
      "currency": "RUB",
      "available_stock": 37
    }
  ],
  "total": 3,
  "next_cursor": "1",
  "source": "sqlite"
}
```

字段说明：

| 字段 | 类型 | 描述 |
|---|---|---|
| `items` | array | 当前页商品报价 |
| `total` | integer | 总记录数 |
| `next_cursor` | string/null | 下一页游标，没有下一页时为空 |
| `source` | string | 数据来源，当前为 `sqlite` 或测试用 `stub` |

## 4. MVP 规划接口

以下是内部应用契约，不代表 Ozon 上游端点；开发时必须再次确认 Ozon 官方接口版本与字段。

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/v1/sessions` | 创建运营人员会话 |
| DELETE | `/v1/sessions/current` | 退出当前会话 |
| GET | `/v1/store-workspaces` | 查询店铺工作区 |
| POST | `/v1/store-workspaces` | 添加卖家账户并创建工作区 |
| POST | `/v1/store-workspaces/{id}/verify` | 验证卖家账户凭据 |
| GET | `/v1/store-workspaces/{id}/product-offers` | 查询商品报价 |
| GET | `/v1/store-workspaces/{id}/stock-positions` | 查询库存位置 |
| GET | `/v1/store-workspaces/{id}/customer-orders` | 查询客户订单 |
| GET | `/v1/store-workspaces/{id}/postings` | 查询履约单 |
| POST | `/v1/store-workspaces/{id}/sync-jobs` | 创建同步任务 |
| GET | `/v1/sync-jobs/{id}` | 查询同步任务状态 |
| GET | `/v1/store-workspaces/{id}/seller-operations` | 查询操作审计 |

## 5. 分页约定

- 客户端只把 `next_cursor` 原样传回，不解析其内部结构。
- `limit` 最大为 100。
- 返回空列表不视为错误。
- Ozon 上游分页参数由后端适配器转换，不能暴露给扩展形成耦合。

## 6. Ozon 上游调用约定

- 服务地址默认 `https://api-seller.ozon.ru`。
- `Client-Id` 和 `Api-Key` 只由后端设置。
- 每个业务功能实现前记录上游方法、版本化路径、请求/响应结构、分页、限制和错误码。
- 读取接口遇到可恢复错误可采用带抖动的指数退避，并遵守 `Retry-After`。
- 写接口默认不自动重试，除非已确认幂等语义或有重复抑制方案。
- 官方参考：[Ozon Seller API](https://docs.ozon.ru/api/seller/)。
