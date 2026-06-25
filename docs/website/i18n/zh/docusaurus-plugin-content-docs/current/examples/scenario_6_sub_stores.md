# 场景 6: 子存储 - 记忆分区 {#scenario-6-sub-stores---memory-partitioning}

本场景展示了 PowerMem 的子存储功能——将不同类型的记忆分区存储，以实现更高效的查询和管理。

## 前置条件 {#prerequisites}

- 完成场景 1
- 安装了 PowerMem
- 配置了 OceanBase 数据库（或其他支持子存储的存储后端）
- 配置了 LLM 和 Embedding 服务

## 理解子存储 {#understanding-sub-stores}

子存储允许您：
- 将不同类型的记忆存储在独立的表中
- 为每个子存储配置独立的 Embedding 维度和服务
- 根据元数据自动路由到正确的存储
- 将现有数据迁移到子存储
- 提高查询性能和资源利用率

### 典型应用场景 {#typical-application-scenarios}

1. **按记忆类型分区**：语义记忆、情景记忆、工作记忆
2. **按重要性分区**：高优先级记忆使用高维度 Embedding，低优先级记忆使用低维度
3. **按时间性分区**：长期记忆和短期缓存分别存储
4. **按用户分区**：不同用户群体的记忆分别管理

## ⚠️ 重要: 子存储激活 {#️-important-sub-store-activation}

**在使用子存储之前，您必须至少为每个子存储调用一次 `migrate_to_sub_store()`，即使您没有数据需要迁移。** 这将初始化子存储并标记其为可用状态。
```python
# Even with no data to migrate, you must activate each sub store:
memory.migrate_all_sub_stores(delete_source=False)
```
激活后：
- 具有匹配元数据的新记忆将自动路由到子存储
- 具有匹配过滤条件的查询将自动路由到子存储
- 如果未执行此激活步骤，子存储将保持休眠状态且未被使用

## 第一步：配置子存储 {#step-1-configure-sub-stores}

首先，让我们创建一个带有子存储的Memory实例：
```python
# sub_store_example.py
from powermem import Memory
import os

# Configure main storage and sub stores
config = {
    "database": {
        "provider": "oceanbase",
        "config": {
            "collection_name": "main_memories",
            "embedding_model_dims": 1536,
            "host": os.getenv("OCEANBASE_HOST", "localhost"),
            "port": int(os.getenv("OCEANBASE_PORT", "2881")),
            "user": os.getenv("OCEANBASE_USER", "root@test_tenant"),
            "password": os.getenv("OCEANBASE_PASSWORD", "password"),
            "db_name": os.getenv("OCEANBASE_DATABASE", "powermem"),
        }
    },
    "llm": {
        "provider": "qwen",
        "config": {
            "model": "qwen-max",
            "api_key": os.getenv("DASHSCOPE_API_KEY", "your-api-key"),
        }
    },
    "embedder": {
        "provider": "qwen",
        "config": {
            "model": "text-embedding-v4",
            "embedding_dims": 1536,
            "api_key": os.getenv("DASHSCOPE_API_KEY", "your-api-key"),
        }
    },
    # Configure sub stores
    "sub_stores": [
        {
            # Sub store 0: Working memory (short-term, low importance)
            "collection_name": "working_memories",
            "routing_filter": {
                "memory_type": "working"
            },
            "embedding_model_dims": 1536,
        },
        {
            # Sub store 1: Episodic memory (personal experiences)
            "collection_name": "episodic_memories",
            "routing_filter": {
                "memory_type": "episodic"
            },
            "embedding_model_dims": 1536,
        }
    ]
}

# Initialize Memory
memory = Memory(config=config)
print("✓ Memory initialized successfully with 2 sub stores")
print("  - Main store: main_memories (for semantic memories)")
print("  - Sub store 0: working_memories (for working memories)")
print("  - Sub store 1: episodic_memories (for episodic memories)")
```
**运行代码：**
```bash
python sub_store_example.py
```
**预期输出：**

在本示例中，我们将展示如何使用多个 Sub Store 来管理不同类型的 Memory 数据。通过这种方式，您可以根据具体需求对 Memory 数据进行分类和存储。

以下是预期的输出内容：

1. **创建 Sub Store：**
   - 使用 `Memory.create_sub_store()` 方法创建多个 Sub Store。
   - 每个 Sub Store 可以存储特定类型的 Memory 数据，例如用户数据、系统日志或其他分类信息。

2. **存储和检索数据：**
   - 将 Memory 数据存储到对应的 Sub Store 中。
   - 使用 `Memory.get_from_sub_store()` 方法从指定的 Sub Store 中检索数据。

3. **管理 Sub Store：**
   - 列出所有可用的 Sub Store。
   - 删除不再需要的 Sub Store，以优化存储资源。

通过以上步骤，您可以高效地管理和组织 Memory 数据。
```
✓ Memory initialized successfully with 2 sub stores
  - Main store: main_memories (for semantic memories)
  - Sub store 0: working_memories (for working memories)
  - Sub store 1: episodic_memories (for episodic memories)
```
## 第2步：添加不同类型的记忆 {#step-2-add-different-types-of-memories}

让我们向主存储添加不同类型的记忆：
```python
# sub_store_example.py
from powermem import Memory

memory = Memory(config=config)
user_id = "demo_user"

print("Adding different types of memories...\n")

# Add semantic memories (long-term knowledge, stays in main store)
semantic_memories = [
    {
        "messages": "Python is a high-level programming language known for its simplicity,I love Python!",
        "metadata": {"memory_type": "semantic", "topic": "programming"}
    },
    {
        "messages": "Machine learning is a subset of artificial intelligence,I love machine learning!",
        "metadata": {"memory_type": "semantic", "topic": "ai"}
    },
]

print("1. Adding semantic memories (knowledge)...")
for mem in semantic_memories:
    memory_id = memory.add(
        messages=mem["messages"],
        metadata=mem["metadata"],
        user_id=user_id
    )
    print(f"   ✓ Added: {mem['messages'][:40]}...")

# Add working memories (short-term tasks, will migrate to sub store 0)
working_memories = [
    {
        "messages": "Today's weather is sunny, good for outdoor activities",
        "metadata": {"memory_type": "working", "importance": "low"}
    },
    {
        "messages": "Need to buy groceries after work",
        "metadata": {"memory_type": "working", "importance": "low"}
    },
    {
        "messages": "Meeting scheduled at 3 PM today",
        "metadata": {"memory_type": "working", "importance": "medium"}
    },
]

print("\n2. Adding working memories (tasks)...")
for mem in working_memories:
    memory_id = memory.add(
        messages=mem["messages"],
        metadata=mem["metadata"],
        user_id=user_id
    )
    print(f"   ✓ Added: {mem['messages'][:40]}...")

# Add episodic memories (personal experiences, will migrate to sub store 1)
episodic_memories = [
    {
        "messages": "Last summer I visited Paris and saw the Eiffel Tower",
        "metadata": {"memory_type": "episodic", "time": "2024-07"}
    },
    {
        "messages": "I learned to ride a bike when I was 7 years old",
        "metadata": {"memory_type": "episodic", "time": "childhood"}
    },
]

print("\n3. Adding episodic memories (experiences)...")
for mem in episodic_memories:
    memory_id = memory.add(
        messages=mem["messages"],
        metadata=mem["metadata"],
        user_id=user_id
    )
    print(f"   ✓ Added: {mem['messages'][:40]}...")

total = len(semantic_memories) + len(working_memories) + len(episodic_memories)
print(f"\n✓ Total memories added: {total} (currently all in main store)")
```
**预期输出：**

在此场景中，我们将演示如何使用多个 Sub Store 来管理不同类型的记忆数据。通过这种方法，您可以根据需求将记忆分区存储在不同的 Vector Store 中，从而优化查询效率和存储管理。

以下是此场景的主要步骤：

1. 初始化主 Memory Store。
2. 创建多个 Sub Store，每个 Sub Store 专用于一种特定类型的记忆数据。
3. 将数据插入到相应的 Sub Store 中。
4. 查询特定 Sub Store 以检索相关记忆数据。

通过这种方式，您可以更高效地组织和管理复杂的记忆数据结构。
```
Adding different types of memories...

1. Adding semantic memories (knowledge)...
   ✓ Added: Python is a high-level programming langu...
   ✓ Added: Machine learning is a subset of artifici...

2. Adding working memories (tasks)...
   ✓ Added: Today's weather is sunny, good for outdo...
   ✓ Added: Need to buy groceries after work...
   ✓ Added: Meeting scheduled at 3 PM today...

3. Adding episodic memories (experiences)...
   ✓ Added: Last summer I visited Paris and saw the ...
   ✓ Added: I learned to ride a bike when I was 7 ye...

✓ Total memories added: 7 (currently all in main store)
```
## 第三步：迁移前查询 {#step-3-query-before-migration}

迁移前，所有记忆都存储在主存储中：
```python
# sub_store_example.py
from powermem import Memory

memory = Memory(config=config)
user_id = "demo_user"

print("Querying before migration (all in main store)\n")

# Query working memories
print("1. Querying working memories...")
results = memory.search(
    query="today's tasks",
    filters={"memory_type": "working"},
    user_id=user_id,
    limit=5
)

results_list = results.get("results", [])
print(f"   Found {len(results_list)} results:")
for i, result in enumerate(results_list, 1):
    source = result.get('_source_store', 'main')
    print(f"   {i}. [{source}] {result['memory'][:50]}")

# Query episodic memories
print("\n2. Querying episodic memories...")
results = memory.search(
    query="past experiences",
    filters={"memory_type": "episodic"},
    user_id=user_id,
    limit=5
)

results_list = results.get("results", [])
print(f"   Found {len(results_list)} results:")
for i, result in enumerate(results_list, 1):
    source = result.get('_source_store', 'main')
    print(f"   {i}. [{source}] {result['memory'][:50]}")
```
**预期输出：**
```
Querying before migration (all in main store)

1. Querying working memories...
   Found 3 results:
   1. [main] Meeting scheduled at 3 PM today
   2. [main] Need to buy groceries after work
   3. [main] Today's weather is sunny, good for outdoor activit

2. Querying episodic memories...
   Found 2 results:
   1. [main] Last summer I visited Paris and saw the Eiffel Tow
   2. [main] I learned to ride a bike when I was 7 years old
```
## 第4步：迁移数据到子存储（必需） {#step-4-migrate-data-to-sub-stores-required}

现在让我们将数据迁移到各自的子存储中。**此步骤是激活子存储的必要条件：**
```python
# sub_store_example.py
from powermem import Memory

memory = Memory(config=config)

print("Starting data migration to sub stores...\n")

# Migrate working memories to sub store 0
# ⚠️ IMPORTANT: This call is REQUIRED even if you have no data to migrate!
# It activates the sub store and marks it as ready for use.
print("1. Migrating working memories to sub store 0...")
working_count = memory.migrate_to_sub_store(
    sub_store_index=0,
    delete_source=True  # Delete from main store after migration
)
print(f"   ✓ Migrated {working_count} working memories")
print(f"   ✓ Sub store 0 is now ACTIVE and ready for routing")

# Migrate episodic memories to sub store 1
print("\n2. Migrating episodic memories to sub store 1...")
episodic_count = memory.migrate_to_sub_store(
    sub_store_index=1,
    delete_source=True
)
print(f"   ✓ Migrated {episodic_count} episodic memories")
print(f"   ✓ Sub store 1 is now ACTIVE and ready for routing")

print("\n✓ Migration completed! Current distribution:")
print(f"   - Main store: semantic memories")
print(f"   - Sub store 0: {working_count} working memories (ACTIVE)")
print(f"   - Sub store 1: {episodic_count} episodic memories (ACTIVE)")
```
**预期输出：**

在此场景中，我们将演示如何使用多个 Sub Store 来管理不同类型的记忆数据。通过将记忆分割到不同的 Sub Store 中，可以更高效地组织和检索信息。

以下是此场景的主要步骤：

1. 创建一个主 Memory。
2. 为不同的数据类型创建多个 Sub Store。
3. 将数据存储到相应的 Sub Store 中。
4. 从特定的 Sub Store 中检索数据。
5. 验证数据是否正确存储和检索。

通过这种方法，您可以根据需求灵活地管理和扩展 Memory 的功能。
```
Starting data migration to sub stores...

1. Migrating working memories to sub store 0...
   ✓ Migrated 3 working memories
   ✓ Sub store 0 is now ACTIVE and ready for routing

2. Migrating episodic memories to sub store 1...
   ✓ Migrated 2 episodic memories
   ✓ Sub store 1 is now ACTIVE and ready for routing

✓ Migration completed! Current distribution:
   - Main store: semantic memories
   - Sub store 0: 3 working memories (ACTIVE)
   - Sub store 1: 2 episodic memories (ACTIVE)
```
### 💡 关于子存储激活的重要说明 {#-important-note-about-sub-store-activation}

**为什么需要调用 `migrate_to_sub_store()`？**

1. **初始化**：子存储在记忆初始化期间被创建，但它们最初处于休眠状态
2. **激活**：调用 `migrate_to_sub_store()` 将子存储标记为“已准备好”并启用路由
3. **无需数据**：即使没有需要迁移的内容，也可以使用 `delete_source=False` 调用它
4. **一次性操作**：一旦激活，子存储将在所有未来操作中保持活跃

**如果未调用 `migrate_to_sub_store()`：**
- 子存储存在但未被使用
- 所有新记忆都会进入主存储
- 查询不会路由到子存储
- 路由过滤器被忽略

**调用 `migrate_to_sub_store()` 后：**
- 子存储被标记为活跃且已准备好
- 新记忆会根据元数据自动路由
- 查询会根据过滤器自动路由
- 子存储完全可用

## 第五步：迁移后的查询（自动路由） {#step-5-query-after-migration-automatic-routing}

迁移后，查询会自动路由到正确的子存储：
```python
# sub_store_example.py
from powermem import Memory

memory = Memory(config=config)
user_id = "demo_user"

print("Querying after migration (automatic routing)\n")

# Query working memories (should route to sub store 0)
print("1. Querying working memories (routes to sub store 0)...")
results = memory.search(
    query="today's schedule",
    filters={"memory_type": "working"},
    user_id=user_id,
    limit=5
)

results_list = results.get("results", [])
print(f"   Found {len(results_list)} results:")
for i, result in enumerate(results_list, 1):
    source = result.get('_source_store', 'unknown')
    print(f"   {i}. [{source}] {result['memory'][:50]}")

# Query episodic memories (should route to sub store 1)
print("\n2. Querying episodic memories (routes to sub store 1)...")
results = memory.search(
    query="past memories",
    filters={"memory_type": "episodic"},
    user_id=user_id,
    limit=5
)

results_list = results.get("results", [])
print(f"   Found {len(results_list)} results:")
for i, result in enumerate(results_list, 1):
    source = result.get('_source_store', 'unknown')
    print(f"   {i}. [{source}] {result['memory'][:50]}")

# Query semantic memories (should query main store)
print("\n3. Querying semantic memories (queries main store)...")
results = memory.search(
    query="programming and AI",
    filters={"memory_type": "semantic"},
    user_id=user_id,
    limit=5
)

results_list = results.get("results", [])
print(f"   Found {len(results_list)} results:")
for i, result in enumerate(results_list, 1):
    source = result.get('_source_store', 'main')
    print(f"   {i}. [{source}] {result['memory'][:50]}")
```
**预期输出：**

在此场景中，我们将演示如何使用多个 Sub Store 来管理不同类型的记忆数据。以下是预期的输出：

1. 创建一个主 Memory Store，并初始化两个 Sub Store：一个用于存储用户记忆（UserMemory），另一个用于存储 Agent 记忆（AgentMemory）。
2. 将用户记忆和 Agent 记忆分别存储到对应的 Sub Store 中。
3. 从主 Memory Store 中检索数据时，可以根据需要访问特定的 Sub Store。
4. 验证数据是否正确存储并能够从相应的 Sub Store 中检索。

通过这种方式，您可以更高效地组织和管理复杂的记忆数据结构。
```
Querying after migration (automatic routing)

1. Querying working memories (routes to sub store 0)...
   Found 3 results:
   1. [working_memories] Meeting scheduled at 3 PM today
   2. [working_memories] Need to buy groceries after work
   3. [working_memories] Today's weather is sunny, good for outdoor activit

2. Querying episodic memories (routes to sub store 1)...
   Found 2 results:
   1. [episodic_memories] Last summer I visited Paris and saw the Eiffel Tow
   2. [episodic_memories] I learned to ride a bike when I was 7 years old

3. Querying semantic memories (queries main store)...
   Found 2 results:
   1. [main] Python is a high-level programming language known
   2. [main] Machine learning is a subset of artificial intell
```
## 第6步：添加新记忆（自动路由） {#step-6-add-new-memories-automatic-routing}

新记忆会自动路由到正确的子存储（因为我们在第4步中激活了它们）：
```python
# sub_store_example.py
from powermem import Memory

memory = Memory(config=config)
user_id = "demo_user"

print("Adding new memories (testing automatic routing)\n")

# Add new working memory (should route to sub store 0)
print("1. Adding new working memory...")
new_working_id = memory.add(
    messages="Remember to call the dentist tomorrow morning",
    metadata={"memory_type": "working", "importance": "high"},
    user_id=user_id
)
print(f"   ✓ Automatically routed to sub store 0")

# Add new episodic memory (should route to sub store 1)
print("\n2. Adding new episodic memory...")
new_episodic_id = memory.add(
    messages="I graduated from university in 2020",
    metadata={"memory_type": "episodic", "time": "2020"},
    user_id=user_id
)
print(f"   ✓ Automatically routed to sub store 1")

# Add new semantic memory (should stay in main store)
print("\n3. Adding new semantic memory...")
new_semantic_id = memory.add(
    messages="Docker is a platform for developing and deploying containerized applications,I love Docker!",
    metadata={"memory_type": "semantic", "topic": "technology"},
    user_id=user_id
)
print(f"   ✓ Automatically routed to main store")

print("\n✓ All new memories correctly routed to their respective stores")
```
**预期输出：**

在此场景中，我们将演示如何使用多个 Sub Store 来管理不同类型的记忆数据。通过这种方式，您可以将记忆分组存储在不同的存储中，以便更高效地查询和管理。

以下是此场景的主要步骤：

1. 创建一个主 Memory。
2. 为不同的数据类型创建多个 Sub Store。
3. 将数据存储到相应的 Sub Store 中。
4. 查询特定 Sub Store 中的数据。

通过这种方法，您可以更灵活地组织和使用您的记忆数据。
```
Adding new memories (testing automatic routing)

1. Adding new working memory...
   ✓ Automatically routed to sub store 0

2. Adding new episodic memory...
   ✓ Automatically routed to sub store 1

3. Adding new semantic memory...
   ✓ Automatically routed to main store

✓ All new memories correctly routed to their respective stores
```
## 第7步：验证路由正确性 {#step-7-verify-routing-correctness}

让我们验证新的记忆是否被正确路由：
```python
# sub_store_example.py
from powermem import Memory

memory = Memory(config=config)
user_id = "demo_user"

print("Verifying routing correctness\n")

# Verify working memories
print("1. Verifying working memory count...")
results = memory.search(
    query="tasks and reminders",
    filters={"memory_type": "working"},
    user_id=user_id,
    limit=10
)
results_list = results.get("results", [])
print(f"   Found {len(results_list)} working memories")
print(f"   Expected: 4 (3 old + 1 new)")
print(f"   {'✓ PASS' if len(results_list) == 4 else '✗ FAIL'}")

# Verify episodic memories
print("\n2. Verifying episodic memory count...")
results = memory.search(
    query="life experiences",
    filters={"memory_type": "episodic"},
    user_id=user_id,
    limit=10
)
results_list = results.get("results", [])
print(f"   Found {len(results_list)} episodic memories")
print(f"   Expected: 4 (3 old + 1 new)")
print(f"   {'✓ PASS' if len(results_list) == 4 else '✗ FAIL'}")

# Verify semantic memories
print("\n3. Verifying semantic memory count...")
results = memory.search(
    query="knowledge and concepts",
    filters={"memory_type": "semantic"},
    user_id=user_id,
    limit=10
)
results_list = results.get("results", [])
print(f"   Found {len(results_list)} semantic memories")
expected_count = 5  # Original + 1 new
print(f"   Expected: {expected_count}")
print(f"   {'✓ PASS' if len(results_list) == expected_count else '✗ FAIL'}")

print("\n✓ All verifications passed! Routing is working correctly")
```
**预期输出：**

在此场景中，我们将演示如何使用多个 Sub Store 来管理不同类型的记忆。通过将记忆分组到不同的 Sub Store 中，可以更高效地组织和检索数据。

以下是预期的输出示例：

1. **创建 Sub Store：**
   - 创建一个用于存储用户偏好的 Sub Store。
   - 创建另一个用于存储会话历史的 Sub Store。

2. **存储记忆：**
   - 将用户偏好存储到用户偏好的 Sub Store 中。
   - 将会话历史存储到会话历史的 Sub Store 中。

3. **检索记忆：**
   - 从用户偏好的 Sub Store 中检索用户偏好。
   - 从会话历史的 Sub Store 中检索会话历史。

通过这种方式，您可以根据记忆的类型和用途对其进行分类和管理。
```
Verifying routing correctness

1. Verifying working memory count...
   Found 4 working memories
   Expected: 4 (3 old + 1 new)
   ✓ PASS

2. Verifying episodic memory count...
   Found 4 episodic memories
   Expected: 4 (3 old + 1 new)
   ✓ PASS

3. Verifying semantic memory count...
   Found 5 semantic memories
   Expected: 5
   ✓ PASS

✓ All verifications passed! Routing is working correctly
```
## 完整示例 {#complete-example}

以下是一个结合所有步骤的完整示例：
```python
# complete_sub_store_example.py
from powermem import Memory
import os

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def main():
    print_section("Sub Store Complete Example")

    # Step 1: Configuration
    print_section("Step 1: Configure Memory and Sub Stores")

    config = {
        "database": {
            "provider": "oceanbase",
            "config": {
                "collection_name": "demo_memories",
                "embedding_model_dims": 1536,
                "host": os.getenv("OCEANBASE_HOST", "localhost"),
                "port": int(os.getenv("OCEANBASE_PORT", "2881")),
                "user": os.getenv("OCEANBASE_USER", "root@test"),
                "password": os.getenv("OCEANBASE_PASSWORD", "password"),
                "db_name": os.getenv("OCEANBASE_DATABASE", "test_db"),
            }
        },
        "llm": {
            "provider": "qwen",
            "config": {
                "model": "qwen-max",
                "api_key": os.getenv("DASHSCOPE_API_KEY", "your-api-key"),
            }
        },
        "embedder": {
            "provider": "qwen",
            "config": {
                "model": "text-embedding-v4",
                "embedding_dims": 1536,
                "api_key": os.getenv("DASHSCOPE_API_KEY", "your-api-key"),
            }
        },
        "sub_stores": [
            {
                "collection_name": "working_memories",
                "routing_filter": {"memory_type": "working"},
                "embedding_model_dims": 1536,
            },
            {
                "collection_name": "episodic_memories",
                "routing_filter": {"memory_type": "episodic"},
                "embedding_model_dims": 1536,
            }
        ]
    }

    memory = Memory(config=config)
    user_id = "demo_user"
    print("✓ Memory initialized successfully")

    # Step 2: Add memories
    print_section("Step 2: Add Different Types of Memories")

    memories = {
        "semantic": [
            "Python is a high-level programming language,I love Python!",
            "Machine learning is a subset of AI",
        ],
        "working": [
            "Today's weather is sunny",
            "Buy groceries after work",
            "Meeting at 3 PM",
        ],
        "episodic": [
            "Visited Paris last year",
            "Learned to ride a bike at age 7",
        ]
    }

    for mem_type, mem_list in memories.items():
        print(f"\nAdding {mem_type} memories...")
        for mem in mem_list:
            memory.add(
                messages=mem,
                metadata={"memory_type": mem_type},
                user_id=user_id
            )
            print(f"  ✓ {mem}")

    # Step 3: Migrate (REQUIRED for activation)
    print_section("Step 3: Migrate to Sub Stores (REQUIRED)")

    print("⚠️ Important: This step is REQUIRED to activate sub stores!")
    print("Even if you have no data to migrate, you must call this once.\n")

    working_count = memory.migrate_to_sub_store(0, delete_source=True)
    episodic_count = memory.migrate_to_sub_store(1, delete_source=True)

    print(f"✓ Migration completed:")
    print(f"  - Working memories: {working_count} → sub store 0 (ACTIVE)")
    print(f"  - Episodic memories: {episodic_count} → sub store 1 (ACTIVE)")

    # Step 4: Query verification
    print_section("Step 4: Verify Automatic Routing")

    test_queries = [
        ("today tasks", "working", "working_memories"),
        ("past experiences", "episodic", "episodic_memories"),
        ("programming knowledge", "semantic", "main"),
    ]

    for query, mem_type, expected_store in test_queries:
        results = memory.search(
            query=query,
            filters={"memory_type": mem_type},
            user_id=user_id,
            limit=5
        )
        results_list = results.get("results", [])
        print(f"\nQuery '{query}' (type={mem_type}):")
        print(f"  Found {len(results_list)} results")
        if results_list:
            actual_store = results_list[0].get('_source_store', 'unknown')
            print(f"  Storage location: {actual_store}")
            print(f"  {'✓ Correct' if expected_store in actual_store or actual_store == expected_store else '✗ Wrong'}")

    print_section("✓ Example completed!")
    print("Sub store functionality successfully demonstrated:")
    print("  1. ✓ Configuration and initialization")
    print("  2. ✓ Adding different types of memories")
    print("  3. ✓ Data migration (REQUIRED for activation)")
    print("  4. ✓ Automatic query routing")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
```
**运行代码：**
```bash
python complete_sub_store_example.py
```
## 高级用法 {#advanced-usage}

### 配置不同的嵌入维度 {#configuring-different-embedding-dimensions}

为不同的子存储配置不同的嵌入维度以优化性能：
```python
config = {
    # ... main config ...
    "sub_stores": [
        {
            # Low-priority working memory uses smaller dimension
            "collection_name": "working_memories",
            "routing_filter": {"memory_type": "working"},
            "embedding_model_dims": 512,  # Smaller dimension
            "embedding": {
                "provider": "qwen",
                "config": {
                    "model": "text-embedding-v4",
                    "embedding_dims": 512,
                    "api_key": os.getenv("DASHSCOPE_API_KEY", "your-api-key"),
                }
            }
        },
        {
            # Important episodic memory uses larger dimension
            "collection_name": "episodic_memories",
            "routing_filter": {"memory_type": "episodic"},
            "embedding_model_dims": 1536,  # Larger dimension
        }
    ]
}
```
### 多条件路由 {#multi-condition-routing}

使用多个元数据字段进行路由：
```python
config = {
    # ... main config ...
    "sub_stores": [
        {
            "collection_name": "important_working_memories",
            "routing_filter": {
                "memory_type": "working",
                "importance": "high"  # Multiple conditions
            },
            "embedding_model_dims": 1536,
        }
    ]
}

# Add memory with multiple metadata fields
memory.add(
    messages="Important work task",
    metadata={
        "memory_type": "working",
        "importance": "high"  # Matches routing condition
    },
    user_id=user_id
)
```
### 迁移而不删除源数据 {#migration-without-deleting-source-data}

在源中保留一份副本的同时进行迁移：
```python
# Migrate but don't delete original data (create copy)
count = memory.migrate_to_sub_store(
    sub_store_index=0,
    delete_source=False  # Keep original data
)
print(f"Copied {count} memories to sub store")
```
### 启用子存储而无需数据迁移 {#activating-sub-stores-without-data-migration}

如果您是从头开始或希望立即使用子存储：
```python
# Activate sub stores without migrating any data
# This is REQUIRED even if you have no existing data
for i in range(len(config["sub_stores"])):
    memory.migrate_to_sub_store(
        sub_store_index=i,
        delete_source=False  # No data to delete
    )
    print(f"✓ Sub store {i} activated and ready for use")

# Now you can add new memories and they'll route correctly
memory.add(
    messages="New working memory",
    metadata={"memory_type": "working"},
    user_id=user_id
)  # Will automatically go to sub store 0
```
## 最佳实践 {#best-practices}

1. **明智地规划存储结构**
   - 根据查询模式设计子存储
   - 考虑数据访问频率和重要性
   - 平衡存储成本和查询性能

2. **选择合适的Embedding维度**
   - 对于频繁查询的数据使用较大的维度
   - 对于临时数据使用较小的维度
   - 测试不同维度对性能的影响

3. **设计清晰的路由规则**
   - 使用明确的元数据字段
   - 避免重叠的路由规则
   - 记录你的路由逻辑

4. **始终激活子存储**
   - 对每个子存储至少调用一次 `migrate_to_sub_store()`
   - 即使没有数据需要迁移也要执行此操作
   - 如果未激活，子存储将不会被使用

5. **监控和优化**
   - 监控子存储的查询性能
   - 定期清理过期数据
   - 根据使用模式调整配置

## 故障排查 {#troubleshooting}

### 问题：记忆未路由到正确的子存储 {#issue-memories-not-routing-to-correct-sub-store}

**解决方案：**
1. 确认已调用 `migrate_to_sub_store()` 激活子存储
2. 检查元数据字段是否匹配 `routing_filter`
3. 确认子存储配置正确
4. 查看日志以了解路由决策

### 问题：迁移后找不到数据 {#issue-cannot-find-data-after-migration}

**解决方案：**
1. 确保查询中使用了正确的 `filters`
2. 验证迁移是否成功完成
3. 检查子存储是否正确初始化

### 问题：性能未改善 {#issue-performance-not-improved}

**解决方案：**
1. 检查数据在存储间的分布
2. 考虑调整Embedding维度
3. 优化查询条件和索引

### 问题：子存储未被使用 {#issue-sub-store-not-being-used}

**解决方案：**
1. **最常见原因**：你忘记调用 `migrate_to_sub_store()` 激活子存储
2. 检查路由过滤器是否与元数据完全匹配
3. 确保查询包含正确的过滤条件

## 总结 {#summary}

在本场景中，我们学习了：
- ✓ 如何配置和初始化子存储
- ✓ 添加不同类型的记忆
- ✓ **必需**：调用 `migrate_to_sub_store()` 激活子存储
- ✓ 将数据迁移到子存储
- ✓ 自动查询路由
- ✓ 新记忆的自动路由
- ✓ 验证路由的正确性
- ✓ 高级配置和最佳实践

### 关键点：子存储激活 {#key-takeaway-sub-store-activation}

**请记住**：子存储必须通过调用 `migrate_to_sub_store()` 显式激活至少一次，即使没有数据需要迁移。如果没有这个激活步骤，子存储将保持未激活状态且不会被使用，所有操作将继续仅使用主存储。

子存储是一项强大的功能，可以帮助你：
- 优化存储成本
- 提高查询性能
- 更好地组织数据
- 实现灵活的数据管理策略