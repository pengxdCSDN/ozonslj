-- 为 SQL-RAG 补齐数据库语义元数据。
-- 规则：保留已有中文说明；缺失说明由“表级业务语境 + 字段级数据语义”组合生成。
-- 注释不得包含凭据或客户数据，只描述用途、归属、单位、边界与约束。
DO $$
DECLARE
    table_record record;
    column_record record;
    table_description text;
    column_description text;
BEGIN
    CREATE TEMP TABLE sql_rag_table_descriptions (
        table_name text PRIMARY KEY,
        description text NOT NULL
    ) ON COMMIT DROP;

    INSERT INTO sql_rag_table_descriptions (table_name, description) VALUES
        ('advertising_analysis_reports', '广告综合分析报告；保存工作区级诊断结论与可追溯输出。'),
        ('advertising_analysis_snapshots', '广告分析计算快照；冻结一次分析的输入、结果与生成时间。'),
        ('advertising_boundary_audits', '广告操作边界审计；记录动作是否获准及其判定原因。'),
        ('advertising_boundary_checks', '组织级广告操作边界检查；供执行前授权与审计使用。'),
        ('advertising_calendar_snapshots', '广告日历快照；保存指定起始日后的每日计划。'),
        ('advertising_calendars', '组织级广告投放日历；描述工作区的日期化投放安排。'),
        ('advertising_campaigns', 'Ozon 广告活动同步事实；按组织与工作区隔离。'),
        ('advertising_keyword_diagnosis_reports', '广告关键词诊断报告；保存阈值判定后的关键词结论。'),
        ('advertising_keyword_diagnosis_snapshots', '广告关键词诊断快照；冻结阈值版本、输入与诊断结果。'),
        ('advertising_metric_snapshots', '广告指标窗口快照；保存币种、完整性和结构化指标。'),
        ('advertising_reports', '广告活动日粒度事实；保存曝光、点击、订单、销售额与花费。'),
        ('advertising_threshold_versions', '广告诊断阈值版本；同一工作区按版本号只追加保存。'),
        ('agent_permission_checks', '智能体权限判定记录；保存主体、决策与工作区边界。'),
        ('agent_permission_snapshots', '智能体权限配置快照；明确能力、SQL、凭据及外部写入边界。'),
        ('agent_triggers', '智能体触发器配置；描述计划或事件触发及只读限制。'),
        ('audit_events', '通用业务审计事件；只追加记录事件类型、主体与脱敏详情。'),
        ('competition_analyses', '竞争度分析结果；保存样本、价格带、集中度和估算声明。'),
        ('competitor_seeds', '竞品采样种子；保存公开页面入口、状态与停止原因。'),
        ('competitor_selection_analysis_reports', '竞品选品分析报告；保存工作区级结构化分析输出。'),
        ('competitor_selection_analysis_snapshots', '竞品选品分析快照；冻结来源窗口、输入与结果。'),
        ('cost_sensitivities', '成本敏感性场景；保存输入假设和多场景计算结果。'),
        ('cost_sensitivity_analyses', '成本敏感性分析结果；用于比较成本变化对经营结果的影响。'),
        ('data_freshness_checks', '数据新鲜度检查；记录数据域是否满足分析时效要求。'),
        ('data_provenance', '数据来源说明；记录业务事实来源、观察时间及解释。'),
        ('data_quality_schema_snapshots', '数据质量结构检查快照；保存检查行数、发现项和有效性。'),
        ('data_source_labels', '数据来源标签字典；解释来源名称及是否为估算数据。'),
        ('diff_previews', '变更差异预览；在实际写入前保存可审阅的结构化差异。'),
        ('execution_results', '受控命令执行结果；保存工作区级脱敏执行回执。'),
        ('external_notification_configs', '外部通知配置；定义渠道、模板、重试和敏感数据边界。'),
        ('inventory_analysis_reports', '库存分析报告；保存工作区级结构化库存结论。'),
        ('inventory_analysis_snapshots', '库存分析快照；冻结一次分析的输入和结果。'),
        ('keyword_report_import_rows', '关键词报告导入明细；保存标准化关键词及来源行数据。'),
        ('keyword_report_imports', '关键词报告导入批次；用指纹保证同一来源文件幂等。'),
        ('listing_fabe_drafts', '商品 F A B E 文案草稿；保存证据约束下的可编辑内容。'),
        ('listing_keyword_layers', '商品关键词分层结果；保存关键词层级、理由与人工确认状态。'),
        ('listing_keywords', '商品文案关键词事实；保存来源、语言、层级与适用商品范围。'),
        ('listing_publish_commands', '商品文案发布命令；保存幂等键、请求、回读及匹配状态。'),
        ('listing_risk_reports', '商品文案风险报告；保存原文、风险发现与可审阅结论。'),
        ('listing_smart_search_reports', '商品智能搜索覆盖报告；保存覆盖词、缺失词与有效性。'),
        ('listing_title_drafts', '商品标题草稿；保存覆盖词、缺失词、长度和风险。'),
        ('listing_versions', '商品文案版本；只追加保存原文、编辑稿、差异与状态。'),
        ('manual_approvals', '人工审批记录；控制高风险命令的审核、幂等与决定时间。'),
        ('model_adapter_configs', '模型适配器配置；保存提供方、模型、端点及凭据是否已配置。'),
        ('parser_alerts', '公开页面解析告警；记录字段变化、严重级别与处理状态。'),
        ('performance_credential_status', '广告绩效凭据状态快照；仅保存各凭据是否存在，不保存明文。'),
        ('performance_oauth_credentials', '广告绩效 OAuth 加密凭据；与卖家 API 凭据严格隔离。'),
        ('price_batch_validations', '批量价格变更校验结果；执行前保存结构化验证结论。'),
        ('profit_models', '利润模型计算结果；保存假设版本及 FBO、FBS 两种履约结果。'),
        ('public_snapshots', '竞品公开页面采样快照；仅保存公开且已白名单化的数据。'),
        ('quality_isolation_records', '数据质量隔离明细；保存无法进入业务事实层的原始行摘要。'),
        ('readback_verifications', '写入后回读验证；确认外部状态与请求目标是否一致。'),
        ('readonly_tool_audits', '只读工具调用审计；记录工具是否获准及拒绝原因。'),
        ('readonly_tool_authorizations', '只读工具授权结果；明确参数、SQL 权限和判定原因。'),
        ('relationship_quality_findings', '关系数据质量发现；保存跨实体一致性问题。'),
        ('sales_analysis_reports', '销售分析报告；保存工作区级结构化销售结论。'),
        ('sales_analysis_snapshots', '销售分析快照；冻结当前窗口、对比窗口、输入和结果。'),
        ('search_attribute_reports', '搜索属性建议报告；保存属性覆盖率、必填缺口与可编辑状态。'),
        ('search_attributes_reports', '搜索属性综合报告；保存商品范围、报告内容与覆盖情况。'),
        ('selection_decision_books', '选品决策书；保存结构化决策内容与人工确认状态。'),
        ('selection_expansions', '选品词根扩展结果；保存核心词、属性词、场景词和候选变体。'),
        ('selection_opportunities', '选品机会评分；保存关键词指标、覆盖缺口、估算标记与理由。'),
        ('selection_validations', '选品可行性验证；保存 SKU 假设、结果快照与完整性。'),
        ('seller_fulfillment_sync_snapshots', '卖家履约同步响应快照；保存分页游标、数量与脱敏明细。'),
        ('seller_order_sync_snapshots', '卖家订单同步响应快照；保存分页游标、数量与脱敏明细。'),
        ('seller_product_sync_snapshots', '卖家商品同步响应快照；保存分页游标、数量与脱敏明细。'),
        ('seller_stock_sync_snapshots', '卖家库存同步响应快照；保存分页游标、数量与脱敏明细。'),
        ('source_conflicts', '数据来源冲突；保存同一事实的来源差异及处理上下文。'),
        ('summary_report_snapshots', '汇总报告快照；冻结报告类型、统计周期与结果。'),
        ('summary_reports', '组织级汇总报告；保存报告类型、统计周期与结构化内容。'),
        ('sync_watermarks', '资源同步成功水位；仅在完整成功后推进分页游标。');

    FOR table_record IN
        SELECT c.oid, c.relname, obj_description(c.oid, 'pg_class') AS current_description
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname <> 'schema_migrations'
    LOOP
        SELECT description INTO table_description
        FROM sql_rag_table_descriptions
        WHERE table_name = table_record.relname;
        table_description := COALESCE(table_record.current_description, table_description);
        IF table_description IS NULL THEN
            RAISE EXCEPTION '缺少表 % 的 SQL-RAG 中文业务说明', table_record.relname;
        END IF;
        IF table_record.current_description IS NULL THEN
            EXECUTE format('COMMENT ON TABLE public.%I IS %L', table_record.relname, table_description);
        END IF;

        FOR column_record IN
            SELECT a.attname, col_description(table_record.oid, a.attnum) AS current_description
            FROM pg_attribute AS a
            WHERE a.attrelid = table_record.oid AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
        LOOP
            IF column_record.current_description IS NOT NULL THEN
                CONTINUE;
            END IF;
            column_description := CASE column_record.attname
                WHEN 'id' THEN '该记录的应用内唯一标识；仅用于稳定引用，不承载可变业务名称。'
                WHEN 'organization_id' THEN '所属组织标识；用于租户隔离，必须与关联工作区的组织一致。'
                WHEN 'workspace_id' THEN '所属卖家工作区标识；所有查询和写入必须限制在该工作区。'
                WHEN 'user_id' THEN '关联用户标识；用于权限、成员关系或审计主体引用。'
                WHEN 'operator_id' THEN '旧版运营人员标识；仅供兼容迁移和历史审计引用。'
                WHEN 'created_at' THEN '记录创建时间；使用带时区时间并按 UTC 写入。'
                WHEN 'updated_at' THEN '记录最近更新时间；业务内容变化时由应用或数据库更新。'
                WHEN 'occurred_at' THEN '业务事件实际发生时间；与记录写入时间分开保存。'
                WHEN 'observed_at' THEN '数据从来源被观察到的时间；用于判断来源时效。'
                WHEN 'synced_at' THEN '该事实最近一次成功同步时间；失败同步不得推进。'
                WHEN 'last_seen_at' THEN '最近一次在成功同步页面中见到该对象的时间。'
                WHEN 'expires_at' THEN '凭据、会话或授权的到期时间；到期后不得继续使用。'
                WHEN 'revoked_at' THEN '会话或授权被撤销的时间；为空表示尚未撤销。'
                WHEN 'resolved_at' THEN '告警或质量问题被确认解决的时间；为空表示待处理。'
                WHEN 'decided_at' THEN '人工审批作出最终决定的时间；待审批时为空。'
                WHEN 'status' THEN '当前业务状态；取值范围由本表约束或对应领域状态机限定。'
                WHEN 'name' THEN '面向运营人员展示的业务名称；不作为稳定主键。'
                WHEN 'display_name' THEN '面向界面展示的名称；允许修改且不得用于实体关联。'
                WHEN 'email' THEN '登录邮箱的规范化值；比较时使用去空格后的小写形式。'
                WHEN 'password_hash' THEN '不可逆密码哈希；禁止保存、记录或返回明文密码。'
                WHEN 'role' THEN '组织或旧账号角色；权限判断必须使用受控角色集合。'
                WHEN 'currency' THEN 'ISO 4217 三位大写币种代码；与金额最小单位字段配套。'
                WHEN 'source' THEN '该记录的数据来源标识；用于区分真实同步、公开采样或估算。'
                WHEN 'url' THEN '受控来源页面或服务地址；使用前必须通过允许范围校验。'
                WHEN 'base_url' THEN '模型服务基础地址；不得接受绕过安全校验的任意内网地址。'
                WHEN 'title' THEN '来源或草稿标题文本；不得包含凭据和客户敏感数据。'
                WHEN 'description' THEN '面向运营或 RAG 的业务说明；不得写入凭据和客户敏感数据。'
                WHEN 'reason' THEN '产生判定、拒绝、告警或隔离结果的可审计原因。'
                WHEN 'message' THEN '面向运营人员的脱敏结果或错误摘要。'
                WHEN 'detail' THEN '脱敏结构化详情；禁止保存凭据、完整请求体和客户隐私。'
                WHEN 'report' THEN '结构化分析报告内容；字段结构由对应领域契约约束。'
                WHEN 'result' THEN '结构化计算或执行结果；不得作为未经验证的业务事实直接覆盖来源数据。'
                WHEN 'inputs' THEN '生成本次结果时冻结的结构化输入；用于重放和解释。'
                WHEN 'input_assumptions' THEN '计算采用的结构化业务假设；结果解释必须引用其版本或内容。'
                WHEN 'items' THEN '当前同步页的脱敏业务明细数组；不保存凭据或客户隐私。'
                WHEN 'payload' THEN '经白名单过滤的结构化命令载荷；执行前必须再次校验。'
                WHEN 'parameters' THEN '只读工具调用的结构化参数；不得包含凭据或任意 SQL。'
                WHEN 'record' THEN '被质量规则隔离的脱敏原始记录摘要；不进入业务事实表。'
                WHEN 'findings' THEN '结构化诊断或风险发现列表；每项应包含可解释原因。'
                WHEN 'diagnoses' THEN '按阈值生成的关键词诊断集合；可追溯到输入和阈值版本。'
                WHEN 'metrics' THEN '指定时间窗口内的结构化广告指标集合。'
                WHEN 'scenarios' THEN '基于输入假设生成的多个敏感性计算场景。'
                WHEN 'previews' THEN '实际写入前生成的结构化差异预览集合。'
                WHEN 'verification' THEN '写入后回读比对的结构化结论与证据。'
                WHEN 'validation' THEN '执行前结构化校验结果；失败时不得继续写入外部系统。'
                WHEN 'content' THEN '结构化业务正文；格式由对应决策书契约约束。'
                WHEN 'cursor' THEN '上游分页游标；仅在成功处理对应页面后保存。'
                WHEN 'fingerprint' THEN '来源内容的稳定指纹；用于识别重复导入而不保存原文件。'
                WHEN 'idempotency_key' THEN '调用方幂等键；相同业务范围内重复请求必须复用原结果。'
                WHEN 'token_hash' THEN '会话令牌的不可逆哈希；数据库和日志均不得保存令牌明文。'
                WHEN 'encrypted_access_token' THEN '加密后的 OAuth 访问令牌；只有凭据适配器可解密。'
                WHEN 'encrypted_refresh_token' THEN '加密后的 OAuth 刷新令牌；不得进入日志或 API 响应。'
                WHEN 'credential_scope' THEN 'OAuth 凭据授权范围；仅允许执行明确获准的绩效接口操作。'
                WHEN 'campaign_id' THEN 'Ozon 广告活动外部标识；在工作区范围内解释。'
                WHEN 'campaign_type' THEN '广告活动类型；取值来自已验证的 Ozon 响应映射。'
                WHEN 'keywords' THEN '广告活动关联关键词的结构化集合。'
                WHEN 'keyword' THEN '经过规范化处理前或后的搜索关键词文本。'
                WHEN 'normalized_keyword' THEN '用于去重和比较的规范化关键词；保留原词用于展示。'
                WHEN 'language' THEN '关键词或文案使用的语言代码；不得由内容盲目推断。'
                WHEN 'layer' THEN '关键词所属业务层级；用于核心词、属性词和场景词区分。'
                WHEN 'product_scope' THEN '文案或分析适用的商品范围；必须限制在当前工作区。'
                WHEN 'version' THEN '业务对象的版本号或版本文本；旧版本只读保留。'
                WHEN 'version_no' THEN '同一工作区内单调递增的阈值版本号。'
                WHEN 'threshold_version' THEN '本次诊断采用的阈值版本引用；用于结果重放。'
                WHEN 'original_text' THEN '生成或编辑前的原始文案快照；用于差异审计。'
                WHEN 'edited_text' THEN '人工或模型编辑后的候选文案；发布前仍需审核。'
                WHEN 'requested_text' THEN '发布命令期望写入的文本快照。'
                WHEN 'readback_text' THEN '外部写入后重新读取到的文本；用于一致性验证。'
                WHEN 'diff' THEN '原文与编辑稿之间的结构化差异。'
                WHEN 'bullets' THEN 'F A B E 草稿的结构化要点列表。'
                WHEN 'long_description' THEN '商品长描述草稿；仅使用有来源证据的卖点。'
                WHEN 'image_copy_suggestions' THEN '图片文案建议列表；仅供人工编辑，不直接发布。'
                WHEN 'missing_evidence' THEN '当前草稿仍缺少的事实证据列表。'
                WHEN 'covered_terms' THEN '当前文案已经覆盖的目标关键词集合。'
                WHEN 'missing_terms' THEN '当前文案尚未覆盖的目标关键词集合。'
                WHEN 'risks' THEN '文案中识别出的结构化风险列表。'
                WHEN 'suggestions' THEN '搜索属性的结构化改进建议。'
                WHEN 'missing_required' THEN '尚未满足的必填属性集合。'
                WHEN 'coverage_percent' THEN '目标属性或关键词覆盖百分比；范围由数据库约束限定。'
                WHEN 'character_count' THEN '按产品规则计算的字符数量；用于标题长度校验。'
                WHEN 'editable' THEN '结果是否允许人工继续编辑；不代表已获准发布。'
                WHEN 'matched' THEN '回读结果是否与请求目标一致；不一致时发布不得视为成功。'
                WHEN 'allowed' THEN '权限或边界检查是否允许该动作；必须与原因一并审计。'
                WHEN 'enabled' THEN '配置是否启用；停用时保留历史配置与审计记录。'
                WHEN 'read_only' THEN '触发器是否被强制限制为只读能力。'
                WHEN 'audit_required' THEN '该动作是否必须追加审计事件后才可执行。'
                WHEN 'sensitive_data_allowed' THEN '通知是否允许包含受控敏感数据；默认必须为否。'
                WHEN 'preview_only' THEN '通知配置是否仅生成预览而禁止真实外发。'
                WHEN 'credential_configured' THEN '对应模型凭据是否已安全配置；不包含凭据内容。'
                WHEN 'client_id_present' THEN '绩效 OAuth Client ID 是否已配置；仅保存布尔状态。'
                WHEN 'access_token_present' THEN '绩效访问令牌是否已配置；仅保存布尔状态。'
                WHEN 'refresh_token_present' THEN '绩效刷新令牌是否已配置；仅保存布尔状态。'
                WHEN 'isolated_from_seller' THEN '绩效凭据是否与卖家 API 凭据完成存储隔离。'
                WHEN 'estimated' THEN '结果是否包含估算值；为真时界面和报告必须明确标示。'
                WHEN 'complete' THEN '指标窗口数据是否完整；不完整结果不得伪装为全量结论。'
                WHEN 'valid' THEN '结构或业务校验是否全部通过。'
                WHEN 'incomplete' THEN '验证所需输入是否存在缺口；为真时不得给出确定性结论。'
                WHEN 'manually_confirmed' THEN '关键词分层是否经过人工确认。'
                WHEN 'confirmation_status' THEN '决策书的人工确认状态；控制是否可进入后续流程。'
                WHEN 'decision' THEN '权限、新鲜度或策略检查输出的结构化判定。'
                WHEN 'action' THEN '被边界检查或审计的广告动作名称。'
                WHEN 'agent' THEN '发起检查或受约束的智能体标识。'
                WHEN 'tool' THEN '被授权或审计的只读工具名称。'
                WHEN 'provider' THEN '模型服务提供方标识。'
                WHEN 'model' THEN '模型提供方内部的模型名称；不得包含访问凭据。'
                WHEN 'adapter' THEN '应用内模型适配器名称；决定请求与响应转换契约。'
                WHEN 'channel' THEN '外部通知渠道类型；真实发送必须通过渠道白名单。'
                WHEN 'template' THEN '通知内容模板；渲染前必须执行敏感字段过滤。'
                WHEN 'trigger_type' THEN '触发方式类型，例如计划触发或领域事件触发。'
                WHEN 'target' THEN '触发器调用的受控任务目标。'
                WHEN 'schedule' THEN '计划触发配置；格式由调度契约校验。'
                WHEN 'event_name' THEN '领域事件名称；仅事件触发器使用。'
                WHEN 'event_type' THEN '审计事件分类；用于检索而不是承载事件详情。'
                WHEN 'subject_id' THEN '审计事件涉及的业务主体标识。'
                WHEN 'data_domain' THEN '被检查的新鲜度数据域，例如商品、库存或订单。'
                WHEN 'field_name' THEN '发生解析变化或质量问题的字段名称。'
                WHEN 'old_value' THEN '变更前的脱敏字段值；仅用于解析告警对比。'
                WHEN 'new_value' THEN '变更后的脱敏字段值；仅用于解析告警对比。'
                WHEN 'severity' THEN '问题严重级别；决定阻断、告警或仅记录。'
                WHEN 'row_index' THEN '来源批次中的零基或一基行位置，以导入契约定义为准。'
                WHEN 'source_row' THEN '导入文件中的原始行号；用于向运营人员定位错误。'
                WHEN 'row_count' THEN '该导入批次接受的明细行数量。'
                WHEN 'retry_limit' THEN '外部通知允许的最大重试次数；禁止无边界重试。'
                WHEN 'start_date' THEN '广告日历覆盖区间的起始日期。'
                WHEN 'days' THEN '从起始日期开始的结构化每日计划集合。'
                WHEN 'metric_window' THEN '广告指标统计时间窗口；用于解释所有聚合指标。'
                WHEN 'report_date' THEN '广告日事实所属的自然日期。'
                WHEN 'impressions' THEN '广告曝光次数；非负整数。'
                WHEN 'clicks' THEN '广告点击次数；非负整数且用于点击率计算。'
                WHEN 'orders' THEN '广告归因订单数量；口径以来源报告为准。'
                WHEN 'sales_minor' THEN '广告归因销售额，使用对应币种的最小货币单位整数。'
                WHEN 'spend_minor' THEN '广告花费，使用对应币种的最小货币单位整数。'
                WHEN 'min_impressions' THEN '触发广告诊断所需的最低曝光次数。'
                WHEN 'min_clicks' THEN '触发广告诊断所需的最低点击次数。'
                WHEN 'high_cvr_percent' THEN '判定高转化率的百分比阈值。'
                WHEN 'high_spend_minor' THEN '判定高花费的最小货币单位整数阈值。'
                WHEN 'sample_count' THEN '参与本次分析的有效样本数量。'
                WHEN 'sample_size' THEN '公开采样快照声明的样本规模。'
                WHEN 'competition_score' THEN '竞争度综合评分；计算口径由分析契约定义。'
                WHEN 'median_price_minor' THEN '样本价格中位数，使用对应币种的最小货币单位整数。'
                WHEN 'price_band_low_minor' THEN '建议价格带下界，使用最小货币单位整数。'
                WHEN 'price_band_high_minor' THEN '建议价格带上界，使用最小货币单位整数。'
                WHEN 'seller_concentration_percent' THEN '样本卖家集中度百分比。'
                WHEN 'brand_concentration_percent' THEN '样本品牌集中度百分比。'
                WHEN 'caveat' THEN '分析局限和口径说明；解释估算或样本不足风险。'
                WHEN 'last_sampled_at' THEN '该竞品入口最近一次成功公开采样时间。'
                WHEN 'stop_reason' THEN '停止继续采样该入口的业务或安全原因。'
                WHEN 'source_window' THEN '分析采用的来源数据时间窗口。'
                WHEN 'current_window' THEN '销售分析当前统计窗口。'
                WHEN 'previous_window' THEN '用于同比或环比的对照统计窗口。'
                WHEN 'period' THEN '汇总报告覆盖的统计周期。'
                WHEN 'report_type' THEN '汇总报告类型；决定统计口径与结果契约。'
                WHEN 'sku' THEN '被验证的卖家 SKU 或候选商品标识。'
                WHEN 'seed_product' THEN '词根扩展的种子商品摘要。'
                WHEN 'core_terms' THEN '与商品主体直接相关的核心词集合。'
                WHEN 'attribute_terms' THEN '描述商品属性的关键词集合。'
                WHEN 'scene_terms' THEN '描述使用场景的关键词集合。'
                WHEN 'variant_candidates' THEN '基于种子和词根生成的候选变体集合。'
                WHEN 'score' THEN '选品机会综合评分；仅用于排序并需结合理由解释。'
                WHEN 'search_count' THEN '来源报告中的搜索次数或搜索量。'
                WHEN 'conversion_rate' THEN '来源报告中的转化率；单位和口径由导入契约限定。'
                WHEN 'own_coverage_gap' THEN '当前自有商品对目标关键词的覆盖缺口。'
                WHEN 'reasons' THEN '形成评分或建议的结构化理由集合。'
                WHEN 'assumption_version' THEN '利润计算采用的假设版本；用于结果重放。'
                WHEN 'fbo_result' THEN 'FBO 履约模式下的结构化利润计算结果。'
                WHEN 'fbs_result' THEN 'FBS 履约模式下的结构化利润计算结果。'
                WHEN 'seed_id' THEN '产生该公开快照的竞品种子标识。'
                WHEN 'sampled_at' THEN '公开页面内容实际被采样的时间。'
                WHEN 'price_minor' THEN '公开样本价格，使用对应币种的最小货币单位整数。'
                WHEN 'rating' THEN '公开页面展示的评分值；保留来源精度。'
                WHEN 'review_count' THEN '公开页面展示的评价数量。'
                WHEN 'image_url' THEN '公开商品主图地址；不得用于绕过网络访问白名单。'
                WHEN 'attributes' THEN '公开页面提取的白名单商品属性。'
                WHEN 'allowed_capabilities' THEN '明确授予智能体的能力名称集合。'
                WHEN 'denied_capabilities' THEN '明确拒绝智能体使用的能力名称集合。'
                WHEN 'sql_access' THEN '智能体是否可执行受控只读 SQL；不代表可运行任意 SQL。'
                WHEN 'credential_access' THEN '智能体是否可请求凭据能力；默认必须拒绝。'
                WHEN 'external_write_access' THEN '智能体是否可执行外部写入；需额外授权和审计。'
                WHEN 'sql_allowed' THEN '本次只读工具授权是否允许受控 SQL 查询。'
                WHEN 'finding' THEN '跨实体关系质量问题的结构化说明。'
                WHEN 'conflict' THEN '多个来源对同一业务事实产生的结构化冲突详情。'
                WHEN 'checked_rows' THEN '本次质量检查覆盖的记录行数。'
                WHEN 'label' THEN '面向界面和报告展示的数据来源中文标签。'
                WHEN 'reviewer' THEN '作出人工审批决定的用户或受控审核主体标识。'
                WHEN 'approval_id' THEN '人工审批记录的唯一标识。'
                ELSE table_description || '；字段 ' || column_record.attname || ' 保存该记录对应的受控业务属性，类型、空值和取值边界以数据库约束为准。'
            END;
            EXECUTE format(
                'COMMENT ON COLUMN public.%I.%I IS %L',
                table_record.relname,
                column_record.attname,
                table_description || '；' || column_description
            );
        END LOOP;
    END LOOP;

    IF EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname <> 'schema_migrations'
          AND obj_description(c.oid, 'pg_class') IS NULL
    ) OR EXISTS (
        SELECT 1
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        JOIN pg_attribute AS a ON a.attrelid = c.oid
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
          AND c.relname <> 'schema_migrations'
          AND a.attnum > 0 AND NOT a.attisdropped
          AND col_description(c.oid, a.attnum) IS NULL
    ) THEN
        RAISE EXCEPTION 'SQL-RAG 中文表字段说明不完整';
    END IF;
END $$;
