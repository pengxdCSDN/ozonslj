-- DQ-001 数据来源标签：业务事实必须携带来源，公开样本和推导结果显式标记估算。
CREATE TABLE IF NOT EXISTS data_source_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('official_private', 'operator_imported', 'public_sample', 'derived_estimate')),
    label TEXT NOT NULL,
    estimated BOOLEAN NOT NULL,
    description TEXT NOT NULL,
    UNIQUE (source)
);
INSERT INTO data_source_labels (source, label, estimated, description) VALUES
('official_private', '官方私有', FALSE, 'Seller/Performance 官方接口的店铺事实'),
('operator_imported', '运营导入', FALSE, '运营人员导入并确认的业务补充事实'),
('public_sample', '公开样本', TRUE, '公开页面受控采样，不代表全市场精确值'),
('derived_estimate', '推导估算', TRUE, '系统基于输入事实计算的决策辅助结果')
ON CONFLICT (source) DO NOTHING;
