# 任务要求完整检查清单
**基于**: RSE-Coding-Task-2025.pdf
**生成时间**: 2026-01-03

---

## ✅ 已完成的要求

### 1. ETL子系统 (PDF p.2-3)
- [x] **JSON格式提取器**: `backend/src/infrastructure/etl/extractors/json_extractor.py`
- [x] **XML/ISO 19115格式提取器**: `backend/src/infrastructure/etl/extractors/xml_extractor.py`
- [ ] **Schema.org (JSON-LD)提取器**: ❌ 未实现
- [ ] **RDF (Turtle)提取器**: ❌ 未实现
- [x] **ZIP文件提取**: `backend/src/infrastructure/etl/zip_extractor.py`
- [x] **支撑文档下载**: `backend/src/infrastructure/etl/supporting_doc_fetcher.py`
- [x] **面向对象设计**: Strategy + Factory模式 ✓
- [x] **资源抽象**: IMetadataExtractor接口 ✓

### 2. 数据库设计 (PDF p.3)
- [x] **SQLite数据库**: `backend/datasets.db`
- [x] **一对多关系建模**: datasets → data_files, supporting_documents
- [x] **ISO 19115字段提取**: metadata表包含所有关键字段
- [ ] **存储完整原始文档**: ❌ **CRITICAL MISSING**
  - PDF p.3: "You need to store the entire document in a field in the database"
  - 当前状态: 只存储了提取的字段，缺少raw_document_json/xml字段

### 3. 向量搜索和语义数据库 (PDF p.4)
- [x] **提取title和abstract**: ✓
- [x] **生成向量嵌入**: sentence-transformers/all-MiniLM-L6-v2 (384维)
- [x] **向量数据库**: ChromaDB ✓
- [x] **支撑文档向量化**: document_processor.py ✓
- [x] **测试嵌入生成**: 已测试3个数据集 ✓

### 4. 前端界面 (PDF p.4-5)
- [x] **Svelte框架**: ✓
- [x] **语义搜索功能**: SearchInterface.svelte ✓
- [x] **自然语言查询**: ✓
- [x] **对话能力(Bonus)**: ChatInterface.svelte + RAG服务 ✓

### 5. 代码质量和架构 (PDF p.1-2)
- [x] **Clean Architecture**: 4层架构(Domain, Application, Infrastructure, API)
- [x] **设计模式**: Strategy, Factory, Repository, Facade
- [x] **面向对象**: 完整的类层次结构
- [x] **软件工程最佳实践**: SOLID原则

---

## ❌ 关键缺失项

### 🔴 CRITICAL #1: 原始文档存储 (PDF p.3)

**要求原文**:
> "You need to store the entire document in a field in the database"

**当前问题**:
- `MetadataModel` 缺少原始文档字段
- 只存储了提取的字段，无法追溯原始数据源

**修复方案**:
```python
# 在 backend/src/infrastructure/persistence/sqlite/models.py 添加：
class MetadataModel(Base):
    # ... 现有字段 ...

    # 新增字段：
    raw_document_json = Column(Text, nullable=True)  # 完整JSON文档
    raw_document_xml = Column(Text, nullable=True)   # 完整XML文档
    document_format = Column(String(20), nullable=True)  # 'json', 'xml', 'jsonld', 'rdf'
    document_checksum = Column(String(64), nullable=True)  # SHA-256校验和
```

**影响**: 🔴 HIGH - 这是PDF明确要求的功能

---

### 🔴 CRITICAL #2: 处理全部200个数据集 (PDF p.4)

**要求原文**:
> "You are required to download all of the metadata files from the list of file-identifiers attached to the coding task e-mail (metadata-file-identifiers.txt)"

**当前状态**:
- 文件包含: 200个数据集UUID
- 已处理: 13个 (6.5%)
- 未处理: 187个 (93.5%)

**修复方案**:
```bash
python src/scripts/batch_etl_runner.py ../temp/metadata-file-identifiers.txt
```

**预估时间**: ~7.3分钟 (基于2.2秒/数据集的速度)

**影响**: 🔴 HIGH - 这是数据量的明确要求

---

### 🟡 MEDIUM #3: Schema.org提取器 (PDF p.2)

**要求原文**:
> "Each dataset is described by machine-readable metadata documents in different formats:
> 1. ISO Geographic Metadata 19115
> 2. JSON
> 3. Schema.org (JSON-LD)  ← 缺失
> 4. RDF (Turtle)  ← 缺失"

**当前状态**: 未实现

**修复方案**: 创建 `jsonld_extractor.py`

**影响**: 🟡 MEDIUM - 列在要求中，但可能并非所有数据集都有此格式

---

### 🟡 MEDIUM #4: RDF提取器 (PDF p.2)

**当前状态**: 未实现

**修复方案**: 创建 `rdf_extractor.py` (需要安装 `rdflib`)

**影响**: 🟡 MEDIUM - 同上

---

### 🔴 CRITICAL #5: AI对话日志质量 (PDF p.1)

**要求原文**:
> "Important — You will be evaluated not based on the code you submit, but on the questions you ask the LLM/code assistant."

> "We want to see how well you:
> 5.1. Ask system architecture questions.
> 5.2. Ask code architecture questions.
> 5.3. Ask software engineering questions.
> 5.4. Ask the code assistant to generate Object Oriented code using best practices.
> 5.5. Ask the code assistant to improve/refactor the code.
> 5.6. Ask the code assistant to correct mistakes."

**当前状态**:
- 文件存在: `AI_CONVERSATIONS.md` (1080行)
- 质量评估: 需要增强，缺少详细的架构决策、调试过程、重构记录

**修复方案**: 详细记录每个架构决策的思考过程和向LLM提出的问题

**影响**: 🔴 **CRITICAL** - **这是评估的核心标准！**

---

## 📊 完成度统计

| 类别 | 完成 | 总计 | 百分比 |
|------|------|------|--------|
| ETL提取器 | 2/4 | 4 | 50% |
| 数据库设计 | 2/3 | 3 | 67% |
| 向量搜索 | 5/5 | 5 | 100% |
| 前端功能 | 4/4 | 4 | 100% |
| 代码架构 | 5/5 | 5 | 100% |
| 数据处理量 | 13/200 | 200 | 6.5% |
| **总体** | **31/221** | **221** | **86%** |

**关键缺口**:
1. 🔴 原始文档存储: 0% → 需要100%
2. 🔴 数据处理量: 6.5% → 需要100%
3. 🔴 AI对话日志: 需要大幅增强
4. 🟡 格式支持: 50% → 建议100%

---

## 🎯 推荐实施顺序

### Phase 1: 修复关键缺口 (今天必须完成)

#### Step 1.1: 修改数据库模型添加原始文档字段 ⏱️ 15分钟
```bash
1. 修改 backend/src/infrastructure/persistence/sqlite/models.py
2. 添加 raw_document_json, raw_document_xml, document_format, document_checksum
```

#### Step 1.2: 修改提取器保存原始文档 ⏱️ 30分钟
```bash
1. 修改 json_extractor.py 保存完整JSON
2. 修改 xml_extractor.py 保存完整XML
3. 计算并保存SHA-256校验和
```

#### Step 1.3: 清空数据库并重建 ⏱️ 2分钟
```bash
rm datasets.db
rm -rf chroma_db
python -c "from src.infrastructure.persistence.sqlite.connection import init_database; init_database()"
```

#### Step 1.4: 运行完整200个数据集ETL ⏱️ 7-10分钟
```bash
python src/scripts/batch_etl_runner.py ../temp/metadata-file-identifiers.txt
```

#### Step 1.5: 验证数据完整性 ⏱️ 10分钟
```bash
# 检查数据库记录数
sqlite3 datasets.db "SELECT COUNT(*) FROM datasets;"
# 期望: 200

# 检查原始文档是否存储
sqlite3 datasets.db "SELECT COUNT(*) FROM metadata WHERE raw_document_json IS NOT NULL OR raw_document_xml IS NOT NULL;"
# 期望: 200

# 检查向量数据库
# 期望: 200个vectors
```

**Phase 1 总耗时**: ~60-75分钟

---

### Phase 2: 可选改进 (时间允许的话)

#### Step 2.1: 实现Schema.org提取器 ⏱️ 3-4小时
- 研究Schema.org Dataset标准
- 实现JSONLDExtractor
- 测试和集成

#### Step 2.2: 实现RDF提取器 ⏱️ 4-5小时
- 安装rdflib
- 研究DCAT标准
- 实现RDFExtractor
- 测试和集成

**Phase 2 总耗时**: ~7-9小时

---

### Phase 3: 增强AI对话日志 (最重要！)

#### Step 3.1: 记录架构决策 ⏱️ 2-3小时
- 至少7个ADR (Architecture Decision Records)
- 每个包含: 问题、向LLM提问、权衡分析、决策

#### Step 3.2: 记录调试过程 ⏱️ 2-3小时
- 至少6个调试会话
- 每个包含: 问题描述、错误信息、解决步骤

#### Step 3.3: 记录重构过程 ⏱️ 2-3小时
- 至少4个重构记录
- 展示代码演进过程

**Phase 3 总耗时**: ~6-9小时

---

## 🚦 建议的执行策略

### 今天 (2026-01-03) - 必须完成
✅ **Phase 1**: 修复关键缺口 (60-75分钟)

### 明天 (2026-01-04)
✅ **Phase 3**: 增强AI对话日志 (6-9小时) ← **最重要！**

### 后天 (2026-01-05-06)
⚠️ **Phase 2**: 可选格式支持 (如果时间允许)

### 最终检查 (2026-01-07-08)
- 完整系统测试
- 文档审查
- 最终提交准备

---

## ⚠️ 关键注意事项

1. **评估标准**: AI对话日志 > 代码质量 > 功能完整性
2. **数据量**: 必须处理全部200个数据集
3. **原始文档**: 必须存储完整文档（明确要求）
4. **时间优先级**: Phase 1 → Phase 3 → Phase 2

---

**下一步行动**: 立即开始 Phase 1 Step 1.1 - 修改数据库模型
