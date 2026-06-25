# 场景 9：用户档案管理 {#scenario-9-user-profile-management}

本场景展示了 PowerMem 的 UserMemory 功能——自动用户档案提取、管理以及与记忆搜索的集成。

## 前置条件 {#prerequisites}

- Python 3.11+
- 已安装 powermem (`pip install powermem`)
- 已配置 LLM 提供商（用于档案提取）
- 已配置 OceanBase 作为向量存储（UserMemory 需要 OceanBase）

> **重要提示**: `UserMemory` 需要 OceanBase 作为存储后端。如果尝试使用其他存储提供商与 `UserMemory` 配合，将会引发 `ValueError`。请将 OceanBase 配置为您的向量存储提供商。

## 理解用户档案管理 {#understanding-user-profile-management}

UserMemory 扩展了 Memory 的功能，增加了用户档案管理能力：

- **自动档案提取**：从对话中提取与用户相关的信息（姓名、职业、兴趣、偏好等）
- **持续档案更新**：根据新的对话更新和完善档案
- **档案存储**：将档案与记忆分开存储，以提高检索效率
- **联合搜索**：在搜索记忆时可选地包含档案信息

## 第一步：初始化 UserMemory {#step-1-initialize-usermemory}

首先，让我们通过正确的配置初始化 UserMemory：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

# Load configuration (auto-loads from .env or uses defaults)
config = auto_config()

# Create UserMemory instance
user_memory = UserMemory(config=config)

print("✓ UserMemory initialized successfully!")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
✓ UserMemory initialized successfully!
```
## 第 2 步：添加对话并提取用户档案 {#step-2-add-conversation-and-extract-profile}

添加一段对话并自动提取用户档案信息：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

# Add a conversation
conversation = [
    {"role": "user", "content": "Hi, I'm Alice. I'm a 28-year-old software engineer from San Francisco. I work at a tech startup and love Python programming."},
    {"role": "assistant", "content": "Nice to meet you, Alice! Python is a great language for software engineering."}
]

result = user_memory.add(
    messages=conversation,
    user_id="user_001",
    agent_id="assistant_agent",
    run_id="session_001"
)

print(f"✓ Conversation added successfully")
print(f"  - Profile extracted: {result.get('profile_extracted', False)}")
if result.get('profile_content'):
    print(f"  - Profile content: {result['profile_content']}")
print(f"  - Memory results count: {len(result.get('results', []))}")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
✓ Conversation added successfully
  - Profile extracted: True
  - Profile content: Name: Alice. Age: 28. Location: San Francisco. Profession: Software engineer at a tech startup. Interests: Python programming.
  - Memory results count: 1
```
## 第三步：通过更多对话更新个人资料 {#step-3-update-profile-with-more-conversations}

添加更多对话以更新和优化用户个人资料：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

# First conversation
conversation1 = [
    {"role": "user", "content": "Hi, I'm Alice. I'm a software engineer from San Francisco."},
    {"role": "assistant", "content": "Nice to meet you, Alice!"}
]

result1 = user_memory.add(
    messages=conversation1,
    user_id="user_001",
    agent_id="assistant_agent"
)

print("=== First conversation ===")
print(f"Profile extracted: {result1.get('profile_extracted', False)}")
if result1.get('profile_content'):
    print(f"Profile: {result1['profile_content']}")

# Second conversation - adds more information
conversation2 = [
    {"role": "user", "content": "I also enjoy reading science fiction novels and playing tennis on weekends."},
    {"role": "assistant", "content": "That sounds like great hobbies!"}
]

result2 = user_memory.add(
    messages=conversation2,
    user_id="user_001",
    agent_id="assistant_agent"
)

print("\n=== Second conversation ===")
print(f"Profile updated: {result2.get('profile_extracted', False)}")
if result2.get('profile_content'):
    print(f"Updated profile: {result2['profile_content']}")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
=== First conversation ===
Profile extracted: True
Profile: Name: Alice. Profession: Software engineer. Location: San Francisco.

=== Second conversation ===
Profile updated: True
Updated profile: Name: Alice. Profession: Software engineer. Location: San Francisco. Hobbies: Reading science fiction novels, playing tennis.
```
## 第4步：获取用户档案 {#step-4-get-user-profile}

直接检索用户档案：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

# Add some conversations first
conversation = [
    {"role": "user", "content": "I'm Bob, a data scientist. I love machine learning and hiking."},
    {"role": "assistant", "content": "Great to meet you, Bob!"}
]

user_memory.add(
    messages=conversation,
    user_id="user_002",
    agent_id="assistant_agent"
)

# Get the user profile
profile = user_memory.profile(
    user_id="user_002"
)

if profile:
    print("✓ Profile retrieved successfully")
    print(f"  - Profile ID: {profile.get('id')}")
    print(f"  - User ID: {profile.get('user_id')}")
    if profile.get('profile_content'):
        print(f"  - Profile content: {profile.get('profile_content', '')}")
    if profile.get('topics'):
        print(f"  - Topics: {profile.get('topics')}")
    print(f"  - Created at: {profile.get('created_at')}")
    print(f"  - Updated at: {profile.get('updated_at')}")
else:
    print("✗ No profile found")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
✓ Profile retrieved successfully
  - Profile ID: 1234567890123456789
  - User ID: user_002
  - Agent ID: assistant_agent
  - Run ID:
  - Profile content: Name: Bob. Profession: Data scientist. Interests: Machine learning, hiking.
  - Created at: 2024-01-15T10:30:00
  - Updated at: 2024-01-15T10:30:00
```
## 第五步：在没有 Profile 的情况下搜索记忆 {#step-5-search-memories-without-profile}

在不包含 Profile 的情况下搜索记忆：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

user_id = "user_003"

# Add some conversations
user_memory.add(
    messages=[
        {"role": "user", "content": "I'm Charlie, a product manager. I work on mobile apps."},
        {"role": "assistant", "content": "Interesting!"}
    ],
    user_id=user_id,
    agent_id="assistant_agent"
)

user_memory.add(
    messages=[
        {"role": "user", "content": "I prefer agile development methodology."},
        {"role": "assistant", "content": "That's a popular approach."}
    ],
    user_id=user_id,
    agent_id="assistant_agent"
)

# Search without profile
results = user_memory.search(
    query="work and preferences",
    user_id=user_id,
    agent_id="assistant_agent",
    limit=5,
    add_profile=False  # Don't include profile
)

print(f"✓ Search completed")
print(f"  - Results count: {len(results.get('results', []))}")
print(f"  - Profile included: {'profile_content' in results}")

for i, result in enumerate(results.get('results', []), 1):
    print(f"  {i}. {result.get('memory', '')} (score: {result.get('score', 0):.2f})")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
✓ Search completed
  - Results count: 2
  - Profile included: False
  1. Works on mobile apps as a product manager (score: 0.85)
  2. Prefers agile development methodology (score: 0.78)
```
## 可选：使用用户画像进行查询重写 {#optional-query-rewrite-with-user-profile}

`UserMemory.search()` 可以选择使用用户画像来重写查询，以提高召回率。此功能是**可选的**，默认情况下处于禁用状态。仅当 `query_rewrite.enabled=True` 且提供了带有 `profile_content` 的 `user_id` 时才会运行。如果缺少画像、查询过短或重写失败，则会回退到原始查询。

实际示例（画像 + 模糊查询）：
```python

# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

user_id = "user_rewrite_demo"

# Build profile with relocation info
user_memory.add(
    messages="Last month I moved from Chengdu to Hangzhou, and started a new job.",
    user_id=user_id,
    profile_type="content"
)

# Ambiguous query that relies on profile context
results = user_memory.search(
    query="Recommend some delicious food near my place.",
    user_id=user_id,
    limit=5
)
```
对比：启用重写与禁用重写
```python
import os

# Enable query rewrite via env
os.environ["QUERY_REWRITE_ENABLED"] = "true"
user_memory_rewrite = UserMemory(config=auto_config())

# Disable query rewrite via env
os.environ["QUERY_REWRITE_ENABLED"] = "false"
user_memory_no_rewrite = UserMemory(config=auto_config())

# Same query, same user profile
query = "Recommend some delicious food near my place."

result_with_rewrite = user_memory_rewrite.search(
    query=query,
    user_id=user_id,
    limit=5
)

result_without_rewrite = user_memory_no_rewrite.search(
    query=query,
    user_id=user_id,
    limit=5
)
```
示例配置:
```python
config = {
    # ... other config
    "query_rewrite": {
        "enabled": True,
        # "prompt": "Rewrite queries to be specific and grounded in the user profile."
    }
}
```
环境变量也受到支持（参见 `.env.example`）：
```bash
QUERY_REWRITE_ENABLED=false
# QUERY_REWRITE_PROMPT=
# QUERY_REWRITE_MODEL_OVERRIDE=
```
- `QUERY_REWRITE_PROMPT` 是可选的自定义重写指令。
- `QUERY_REWRITE_MODEL_OVERRIDE` 是可选的，必须是同一 LLM 提供商系列中的另一个模型。

## 第6步：通过用户档案搜索记忆 {#step-6-search-memories-with-profile}

搜索记忆并在结果中包含用户档案：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

user_id = "user_004"

# Add conversations
user_memory.add(
    messages=[
        {"role": "user", "content": "I'm Diana, a UX designer. I love creating beautiful interfaces."},
        {"role": "assistant", "content": "That's wonderful!"}
    ],
    user_id=user_id,
    agent_id="assistant_agent"
)

# Search with profile
results = user_memory.search(
    query="user background and interests",
    user_id=user_id,
    agent_id="assistant_agent",
    limit=5,
    add_profile=True  # Include profile
)

print(f"✓ Search with profile completed")
print(f"  - Results count: {len(results.get('results', []))}")
print(f"  - Profile included: {'profile_content' in results}")

if 'profile_content' in results:
    print(f"\n  User Profile:")
    print(f"  {results['profile_content']}")

print(f"\n  Search Results:")
for i, result in enumerate(results.get('results', []), 1):
    print(f"  {i}. {result.get('memory', '')} (score: {result.get('score', 0):.2f})")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
✓ Search with profile completed
  - Results count: 1
  - Profile included: True

  User Profile:
  Name: Diana. Profession: UX designer. Interests: Creating beautiful interfaces.

  Search Results:
  1. Works as a UX designer, loves creating beautiful interfaces (score: 0.92)
```
## 第7步：以母语提取档案 {#step-7-extract-profile-in-native-language}

您可以指定一种母语用于档案提取，确保档案以用户偏好的语言编写，而不受对话语言的影响：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

# Example 1: English conversation, Chinese profile
conversation_en = [
    {"role": "user", "content": "I am a software engineer working in Beijing. I love drinking tea and reading books."},
    {"role": "assistant", "content": "That sounds great!"}
]

result_zh = user_memory.add(
    messages=conversation_en,
    user_id="user_bilingual_001",
    native_language="zh"  # Extract profile in Chinese
)

print("✓ English conversation processed")
if result_zh.get('profile_content'):
    print(f"  - Profile (Chinese): {result_zh['profile_content']}")

# Example 2: Chinese conversation, English profile
conversation_zh = [
    {"role": "user", "content": "I'm 25 years old, working at Microsoft in Seattle."},
    {"role": "assistant", "content": "Nice to meet you"}
]

result_en = user_memory.add(
    messages=conversation_zh,
    user_id="user_bilingual_002",
    native_language="en"  # Extract profile in English
)

print("\n✓ Chinese conversation processed")
if result_en.get('profile_content'):
    print(f"  - Profile (English): {result_en['profile_content']}")

# Example 3: Structured topics with native language
result_topics = user_memory.add(
    messages="I'm 25 years old, working at Microsoft in Seattle.",
    user_id="user_bilingual_003",
    profile_type="topics",
    native_language="zh"  # Topic values in Chinese, keys remain English
)

print("\n✓ Structured topics extracted")
if result_topics.get('topics'):
    print(f"  - Topics: {result_topics['topics']}")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**支持的语言代码：**

| Code | Language | Code | Language |
|------|----------|------|----------|
| zh | 中文 | en | 英文 |
| ja | 日文 | ko | 韩文 |
| fr | 法文 | de | 德文 |
| es | 西班牙文 | it | 意大利文 |
| pt | 葡萄牙文 | ru | 俄文 |
| ar | 阿拉伯文 | hi | 印地文 |
| th | 泰文 | vi | 越南文 |

## 第 8 步：删除用户档案 {#step-8-delete-user-profile}

删除用户档案：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config, agent_id="assistant_agent")

user_id = "user_007"

# Add conversation and create profile
user_memory.add(
    messages=[
        {"role": "user", "content": "I'm Grace, a teacher."},
        {"role": "assistant", "content": "Nice to meet you!"}
    ],
    user_id=user_id
)

# Get profile to confirm it exists
profile = user_memory.profile(user_id=user_id)
if profile:
    profile_id = profile.get('id')
    print(f"✓ Profile exists with ID: {profile_id}")

    # Delete the profile
    deleted = user_memory.delete_profile(
        user_id=user_id
    )

    if deleted:
        print(f"✓ Profile deleted successfully")
    else:
        print(f"✗ Failed to delete profile")

    # Verify deletion
    profile_after = user_memory.profile(user_id=user_id)
    if not profile_after:
        print("✓ Profile confirmed deleted")
    else:
        print("✗ Profile still exists")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
✓ Profile exists with ID: 1234567890123456789
✓ Profile deleted successfully
✓ Profile confirmed deleted
```
## 完整示例 {#complete-example}

以下是一个结合所有功能的完整示例：
```python
# complete_user_profile_example.py
from powermem import UserMemory, auto_config

def main():
    # Load configuration
    config = auto_config()

    # Initialize UserMemory
    user_memory = UserMemory(config=config, agent_id="demo_agent")
    user_id = "demo_user"

    print("=" * 60)
    print("UserMemory Profile Management Example")
    print("=" * 60)

    # Step 1: Add initial conversation
    print("\n1. Adding initial conversation...")
    conversation1 = [
        {"role": "user", "content": "Hi, I'm Alex, a 32-year-old data scientist from New York. I specialize in machine learning and love reading tech blogs."},
        {"role": "assistant", "content": "Nice to meet you, Alex! That's fascinating."}
    ]

    result1 = user_memory.add(
        messages=conversation1,
        user_id=user_id,
        run_id="session_001"
    )

    print(f"   ✓ Profile extracted: {result1.get('profile_extracted', False)}")
    if result1.get('profile_content'):
        print(f"   Profile: {result1['profile_content']}")

    # Step 2: Update profile with more information
    print("\n2. Updating profile with more conversations...")
    conversation2 = [
        {"role": "user", "content": "I also enjoy hiking and photography on weekends."},
        {"role": "assistant", "content": "Those are great hobbies!"}
    ]

    result2 = user_memory.add(
        messages=conversation2,
        user_id=user_id,
        run_id="session_002"
    )

    print(f"   ✓ Profile updated: {result2.get('profile_extracted', False)}")

    # Step 3: Get full profile
    print("\n3. Retrieving full profile...")
    profile = user_memory.profile(
        user_id=user_id
    )

    if profile:
        print(f"   ✓ Profile ID: {profile.get('id')}")
        print(f"   Profile content: {profile.get('profile_content', '')}")
        print(f"   Last updated: {profile.get('updated_at')}")

    # Step 4: Search with profile
    print("\n4. Searching memories with profile...")
    search_results = user_memory.search(
        query="user interests and hobbies",
        user_id=user_id,
        limit=5,
        add_profile=True
    )

    if 'profile_content' in search_results:
        print(f"   User Profile: {search_results['profile_content']}")

    print(f"\n   Found {len(search_results.get('results', []))} memories:")
    for i, result in enumerate(search_results.get('results', []), 1):
        print(f"   {i}. {result.get('memory', '')} (score: {result.get('score', 0):.2f})")

    # Step 5: Cleanup (optional)
    print("\n5. Cleaning up...")
    # Note: In production, you might want to keep the profiles
    # deleted = user_memory.delete_profile(user_id=user_id)
    # if deleted:
    #     print("   ✓ Profile deleted")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
```
**运行以下代码：**
```bash
python complete_user_profile_example.py
```
## 最佳实践 {#best-practices}

1. **始终提供 `user_id`**：`add()` 方法需要 `user_id`；确保每个用户都有唯一的标识符

2. **使用 `agent_id` 区分 Agents**：在Multi-Agent 场景中，使用 `agent_id` 来区分不同的配置文件和记忆

3. **适当使用 `run_id`**：使用 `run_id` 区分会话或运行，以便更精确地管理配置文件

4. **定期检查配置文件**：使用 `profile()` 定期检查并确保配置文件信息的准确性

5. **在需要时包含配置文件**：当额外的上下文信息有用时，设置 `add_profile=True` 以在搜索结果中包含用户配置文件

6. **处理空配置文件**：如果 `profile()` 返回 `{}`，说明尚未提取任何配置文件；请先使用对话数据调用 `add()`

7. **配置文件更新**：当您使用相同的 `user_id`、`agent_id` 和 `run_id` 组合添加新对话时，配置文件会自动更新

8. **消息过滤**：默认情况下，仅 `user` 角色的消息会用于配置文件提取（不包括 assistant 消息）。您可以通过 `include_roles` 和 `exclude_roles` 参数自定义此行为

9. **查询重写（可选）**：启用 `query_rewrite.enabled=True`，让 `search()` 使用配置文件内容重写查询；如果不可用，则回退到原始查询

## 第 8 步：按角色过滤消息 {#step-8-filter-messages-by-roles}

默认情况下，`UserMemory.add()` 仅从用户消息中提取配置信息。您可以自定义用于配置文件提取的消息角色：
```python
# user_profile_example.py
from powermem import UserMemory, auto_config

config = auto_config()
user_memory = UserMemory(config=config)

# Conversation with multiple roles
conversation = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hi, I'm Frank, a doctor from Boston."},
    {"role": "assistant", "content": "Nice to meet you, Frank!"},
    {"role": "tool", "content": "Weather data: Boston, 72°F"}
]

# Default behavior: only include 'user' messages, exclude 'assistant' messages
result = user_memory.add(
    messages=conversation,
    user_id="user_008"
)
print("Default filtering (user only):")
print(f"  Profile: {result.get('profile_content', 'N/A')}")

# Include all messages (disable filtering)
result = user_memory.add(
    messages=conversation,
    user_id="user_009",
    include_roles=None,  # or []
    exclude_roles=None   # or []
)
print("\nNo filtering (all roles):")
print(f"  Profile: {result.get('profile_content', 'N/A')}")

# Custom filtering: include user and system, exclude tool
result = user_memory.add(
    messages=conversation,
    user_id="user_010",
    include_roles=["user", "system"],
    exclude_roles=["tool"]
)
print("\nCustom filtering (user + system, exclude tool):")
print(f"  Profile: {result.get('profile_content', 'N/A')}")
```
**运行以下代码：**
```bash
python user_profile_example.py
```
**预期输出：**
```
Default filtering (user only):
  Profile: Name: Frank. Profession: Doctor. Location: Boston.

No filtering (all roles):
  Profile: Name: Frank. Profession: Doctor. Location: Boston.

Custom filtering (user + system, exclude tool):
  Profile: Name: Frank. Profession: Doctor. Location: Boston.
```
## 相关文档 {#related-documents}

- [UserMemory 指南](../guides/0010-user_memory.md) - 有关 UserMemory 功能的详细指南
- [快速开始](scenario_1_basic_usage.md) - 学习 PowerMem 的基础知识
- [Multi-Agent 指南](scenario_3_multi_agent.md) - 使用多个 Agent 与记忆