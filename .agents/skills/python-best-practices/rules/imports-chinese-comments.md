---
title: Write Developer Comments and Docstrings in Simplified Chinese
impact: MEDIUM
impactDescription: keeps project documentation readable and consistent for the Chinese-speaking team
tags: comments, docstrings, documentation, chinese, project-convention
---

## Write Developer Comments and Docstrings in Simplified Chinese

本项目新增或修改 Python 代码时，开发者编写的注释和文档字符串统一使用简体中文。公共模块、类和函数应说明职责；复杂业务规则、兼容逻辑、迁移步骤及安全边界应解释“为什么”，不要逐行复述代码。

**Incorrect:**

```python
def migrate_price(price: Decimal) -> int:
    # Convert the decimal price to minor currency units.
    return int(price * 100)
```

**Correct:**

```python
def migrate_price(price: Decimal) -> int:
    """将旧版十进制价格转换为数据库使用的最小货币单位。"""

    # 迁移必须保持金额精度，不能通过四舍五入静默修正历史数据。
    minor_price = price * 100
    if minor_price != minor_price.to_integral_value():
        raise ValueError(f"价格最多支持两位小数：{price!r}")
    return int(minor_price)
```

变量名、类名、函数名、第三方 API 字段和协议约定继续使用其原始英文形式。显而易见的赋值、循环或条件不需要注释；无信息量的中文注释同样应删除。
