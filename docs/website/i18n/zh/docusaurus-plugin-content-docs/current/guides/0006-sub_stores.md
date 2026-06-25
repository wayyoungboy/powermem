# 子存储指南 {#sub-stores-guide}

完整指南：使用子存储进行高级记忆分区和优化。

## 概述 {#overview}

子存储允许您将记忆数据分区到独立的向量表中，每个表具有以下特点：

- **独立的路由规则**：基于元数据自动路由数据
- **不同的Embedding服务**：使用不同的模型和维度
- **自定义存储配置**：不同的索引类型、数据库参数等
- **独立的性能优化**：针对不同的数据特性进行优化

**注意**：子存储目前仅支持OceanBase向量存储。

## 快速开始 {#quick-start}

### 基本配置 {#basic-configuration}
```python
from powermem import Memory

config = {
    "vector_store": {
        "provider": "oceanbase",
        "config": {
            "collection_name": "main_memories",
            "embedding_model_dims": 1536,
            "host": "localhost",
            "port": "2881",
            "user": "root@test",
            "password": "password",
            "db_name": "test_db",
        }
    },
    "embedding": {
        "provider": "openai",
        "config": {
            "api_key": "your-api-key",
            "model": "text-embedding-3-large",
            "embedding_dims": 1536,
        }
    },
    # Configure sub stores
    "sub_stores": [
        {
            # Sub store 1: Inherits main config
            "routing_filter": {"type": "semantic"}
        },
        {
            # Sub store 2: Uses different embedding
            "routing_filter": {"type": "working"},
            "embedding_model_dims": 768,
            "embedding": {
                "provider": "qwen",
                "config": {
                    "model": "text-embedding-v4",
                    "embedding_dims": 768,
                    "api_key": "your-qwen-key",
                }
            }
        }
    ]
}

memory = Memory(config=config)
```
### 初始化子存储路由 {#initialize-sub-store-routing}

**重要**：在使用子存储路由之前，即使没有数据需要迁移，也必须至少运行一次迁移以激活路由功能：
```python
# Initialize sub store routing (required before first use)
memory.migrate_all_sub_stores(delete_source=False)
```
这确保了子存储的迁移状态在数据库中被正确初始化，从而启用自动路由。

### 使用子存储 {#using-sub-stores}

一旦初始化完成，数据将根据元数据自动路由到适当的子存储：
```python
# Add data - automatically routed to sub stores
memory.add(
    "Python is a programming language",
    metadata={"type": "semantic"}  # Routes to sub store 1
)

memory.add(
    "Buy milk today",
    metadata={"type": "working"}  # Routes to sub store 2
)

# Search from specific sub store
results = memory.search(
    "programming concepts",
    filters={"type": "semantic"},  # Searches in sub store 1
    limit=5
)
```
## 配置选项 {#configuration-options}

### 必需参数 {#required-parameters}

#### routing_filter {#routing_filter}

定义哪些数据应被路由到此子存储：
```python
"routing_filter": {
    "type": "working",      # Single condition
    "priority": "high"      # Multiple conditions (AND logic)
}
```
### 可选参数 {#optional-parameters}

#### collection_name {#collection_name}

自定义表名。默认值为 `{main_table_name}_sub_{index}`：
```python
"collection_name": "memories_important"
```
#### embedding_model_dims {#embedding_model_dims}

向量维度。默认为主存储的维度：
```python
"embedding_model_dims": 768
```
#### embedding {#embedding}

子存储特定的嵌入服务：
```python
"embedding": {
    "provider": "qwen",
    "config": {
        "model": "text-embedding-v4",
        "embedding_dims": 768,
        "api_key": "your-api-key",
    }
}
```
**重要**: `embedding.config.embedding_dims` 必须与 `embedding_model_dims` 匹配。

#### vector_store {#vector_store}

覆盖主存储的 vector_store 配置：
```python
"vector_store": {
    "index_type": "HNSW",           # Use HNSW index
    "vector_weight": 0.7,           # Vector search weight
    "fts_weight": 0.3,              # Full-text search weight
    "host": "different-host",       # Use different database
    # Any vector_store parameter can be overridden
}
```
#### index_type {#index_type}

此子存储的索引类型：
```python
"index_type": "HNSW"  # Options: "HNSW", "IVF_FLAT", "IVF_PQ"
```
## 数据迁移 {#data-migration}

### 将数据迁移到 Sub Store {#migrate-data-to-sub-store}
```python
# Method 1: Migrate by index
count = memory.migrate_to_sub_store(
    sub_store_index=0,      # Sub store index
    delete_source=False     # Keep source data
)

# Method 2: Migrate by name
count = memory.migrate_to_sub_store(
    sub_store_name="memories_sub_0",
    delete_source=True      # Delete source after migration
)

# Method 3: Migrate all sub stores
count = memory.migrate_all_sub_stores(delete_source=False)
```
### 监控迁移状态 {#monitor-migration-status}
```python
# Check migration status
status = memory.get_sub_store_migration_status("memories_sub_0")

print(f"Status: {status['status']}")           # PENDING/MIGRATING/COMPLETED/FAILED
print(f"Progress: {status['migrated_count']}/{status['total_count']}")
print(f"Percentage: {status['progress']}%")
```
### 迁移过程 {#migration-process}

在迁移过程中：
1. 根据 `routing_filter` 匹配记录进行查询
2. 使用子存储的 `embedding_service` **重新生成向量**
3. 将新向量和有效负载插入子存储
4. 可选地删除源数据

## 高级配置 {#advanced-configuration}

### 多嵌入维度 {#multiple-embedding-dimensions}
```python
config = {
    "vector_store": {"config": {"embedding_model_dims": 1536}},
    "embedding": {
        "provider": "openai",
        "config": {"model": "text-embedding-3-large", "embedding_dims": 1536}
    },
    "sub_stores": [
        {
            "routing_filter": {"priority": "low"},
            "embedding_model_dims": 384,  # Smaller dimension
            "embedding": {
                "provider": "qwen",
                "config": {"model": "text-embedding-v4", "embedding_dims": 384}
            }
        },
        {
            "routing_filter": {"priority": "high"},
            "embedding_model_dims": 3072,  # Larger dimension
            "embedding": {
                "provider": "openai",
                "config": {"model": "text-embedding-3-large", "embedding_dims": 3072}
            }
        }
    ]
}
```
### 不同的索引类型 {#different-index-types}
```python
config = {
    "vector_store": {
        "config": {"index_type": "IVF_FLAT"}  # Main store: balanced
    },
    "sub_stores": [
        {
            "routing_filter": {"access_pattern": "hot"},
            "vector_store": {
                "index_type": "HNSW",      # Fast retrieval
                "vector_weight": 0.8,
                "fts_weight": 0.2,
            }
        },
        {
            "routing_filter": {"access_pattern": "cold"},
            "vector_store": {
                "index_type": "IVF_PQ"     # Compressed storage
            }
        }
    ]
}
```
### 自定义数据库配置 {#custom-database-configuration}
```python
config = {
    "vector_store": {...},
    "sub_stores": [
        {
            "routing_filter": {"tenant": "enterprise_a"},
            "collection_name": "memories_enterprise_a",
            "vector_store": {
                "database": "tenant_a_db",     # Different database
                "host": "db-a.example.com",    # Different host
            }
        }
    ]
}
```
## 常见模式 {#common-patterns}

### 模式 1：按记忆类型 {#pattern-1-by-memory-type}
```python
"sub_stores": [
    {
        "routing_filter": {"type": "episodic"},
        "embedding_model_dims": 1536,
    },
    {
        "routing_filter": {"type": "semantic"},
        "embedding_model_dims": 768,
        "embedding": {...}  # Different model
    }
]
```
### 模式 2：按优先级划分 {#pattern-2-by-priority-level}
```python
"sub_stores": [
    {
        "routing_filter": {"priority": "high"},
        "vector_store": {
            "index_type": "HNSW"  # Fast queries
        }
    },
    {
        "routing_filter": {"priority": "low"},
        "vector_store": {
            "index_type": "IVF_PQ"  # Save resources
        }
    }
]
```
### 模式 3：按访问频率 {#pattern-3-by-access-frequency}
```python
"sub_stores": [
    {
        "routing_filter": {"frequency": "hot"},
        "vector_store": {
            "index_type": "HNSW",
            "vector_weight": 0.7,
            "fts_weight": 0.3
        }
    },
    {
        "routing_filter": {"frequency": "cold"},
        "vector_store": {
            "index_type": "IVF_FLAT"
        }
    }
]
```
## 重要说明 {#important-notes}

### 使用前初始化 {#initialize-before-use}

**重要**：在使用子存储路由之前，您必须至少初始化一次迁移系统：
```python
memory.migrate_all_sub_stores(delete_source=False)
```
即使您没有现有数据需要迁移，这也是必需的。此步骤会在数据库中初始化子存储的状态，从而启用路由机制。如果跳过此步骤，所有数据将继续流向主存储。

### 维度一致性 {#dimension-consistency}

确保两个维度参数匹配：
```python
{
    "embedding_model_dims": 768,  # Database table structure
    "embedding": {
        "config": {
            "embedding_dims": 768,  # API returns this dimension
        }
    }
}
```
维度不匹配将导致错误：`"expected 1536 dimensions, not 768"`

### 路由规则 {#routing-rules}

- 子存储的 `routing_filter` 与记忆的 `metadata` 匹配
- 所有过滤条件必须匹配（AND 逻辑）
- 如果没有子存储匹配，数据将进入主存储
- 仅支持精确匹配（不支持 OR/NOT 逻辑）

## 相关文档 {#related-documentation}

- [快速开始](./0001-getting_started.md) - 快速入门
- [配置指南](./0003-configuration.md) - 基本配置
- [集成指南](./0009-integrations.md) - 嵌入服务

## 示例 {#examples}

查看完整示例：
- `examples/sub_store_simple.py` - 子存储的基本用法
- `examples/multi_agent.py` - 使用子存储的 Multi-Agent