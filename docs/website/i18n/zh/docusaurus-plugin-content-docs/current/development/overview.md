# 开发指南 {#development-guide}

本指南为希望为 PowerMem 做出贡献的开发者提供了全面的指导，包括如何设置开发环境、构建项目以及添加新的集成。

## 目录 {#table-of-contents}

- [开发环境设置](#development-environment-setup)
- [构建项目](#building-the-project)
- [贡献代码](#contributing-code)
- [添加 Vector Store](#adding-a-vector-store)
- [添加 LLM 提供商](#adding-an-llm-provider)
- [添加 Embedding 提供商](#adding-an-embedding-provider)
- [添加 Reranker 提供商](#adding-a-reranker-provider)
- [测试](#testing)
- [代码风格和标准](#code-style-and-standards)
- [发布到 PyPI](#publishing-to-pypi)
- [调试](#debugging)
- [性能优化](#performance-optimization)
- [常见问题及解决方案](#common-issues-and-solutions)
- [高级主题](#advanced-topics)
- [其他资源](#additional-resources)
- [获取帮助](#getting-help)

## 开发环境设置 {#development-environment-setup}

### 前置条件 {#prerequisites}

- Python 3.11 或更高版本
- pip（Python 包管理器）
- Git

### 安装 {#installation}

1. **克隆代码库：**
```bash
git clone https://github.com/oceanbase/powermem.git
cd powermem
```
2. **安装开发依赖：**
```bash
# Install the project in development mode with all dependencies
make install-dev

# Or install with test dependencies
make install-test
```
或者，您可以直接使用 pip：
```bash
pip install -e ".[dev,test]"
```
3. **设置环境变量：**

复制示例环境文件并进行配置：
```bash
cp .env.example .env
# Edit .env with your configuration
```
### 开发工具 {#development-tools}

该项目使用了几个通过 `dev` 依赖安装的开发工具：

- **pytest**: 测试框架
- **black**: 代码格式化工具
- **isort**: 导入排序工具
- **flake8**: 代码检查工具
- **mypy**: 类型检查工具

### 构建仪表板 {#build-dashboard}

要构建仪表板，您需要安装 Node.js 和 pnpm。然后运行：
```bash
cd dashboard
pnpm install
pnpm build
cd ..
cp -r dashboard/dist/* src/server/dashboard/
```
## 构建项目 {#building-the-project}

### 构建分发包 {#build-distribution-packages}

要构建 wheel 和源代码分发包：
```bash
make build-package
```
这将会：
- 清理之前的构建产物
- 构建 wheel (`.whl`) 和源分发 (`.tar.gz`) 包
- 将文件输出到 `dist/` 目录

### 检查已构建的包 {#check-built-package}

在发布之前，验证该包：
```bash
make build-check
```
这将运行 `twine check` 来验证包。

### 安装构建工具 {#install-build-tools}

如果需要手动安装构建工具：
```bash
make install-build-tools
```
这将安装 `build` 和 `twine` 包。

### 本地安装 {#install-locally}

要在本地安装已构建的包：
```bash
make install-local
```
这将从 `dist/` 目录安装 wheel 包。

## 贡献代码 {#contributing-code}

### 工作流程 {#workflow}

1. **在 GitHub 上 Fork 仓库**
2. **创建一个功能分支：**
```bash
git checkout -b feature/your-feature-name
```
3. **根据代码风格指南进行更改**
4. **为更改编写测试**
5. **运行测试**以确保所有内容通过：
```bash
make test
```
6. **格式化并检查代码：**
```bash
make format
make lint
```
7. **提交你的更改**，并使用清晰的提交信息
8. **推送到你的分叉仓库**，然后创建一个 Pull Request

### 提交信息指南 {#commit-message-guidelines}

- 使用清晰、描述性的提交信息
- 以祈使语气的动词开头（例如，“Add”、“Fix”、“Update”）
- 在适用时引用问题编号（例如，“Fix #123: Add error handling”）

### Pull Request 指南 {#pull-request-guidelines}

- 提供对更改的清晰描述
- 为新功能添加测试
- 如果需要，更新文档
- 确保所有测试通过
- 遵循代码风格指南

## 添加一个 Vector Store {#adding-a-vector-store}

要添加一个新的 Vector Store 提供商，你需要：

1. **创建 Vector Store 实现**
2. **创建配置类**
3. **在工厂中注册它**

### 第一步：创建 Vector Store 实现 {#step-1-create-vector-store-implementation}

在 `src/powermem/storage/your_provider/your_provider.py` 中创建一个新文件：
```python
"""
YourProvider vector store implementation
"""
import logging
from typing import Any, Dict, List, Optional

from powermem.storage.base import VectorStoreBase, OutputData
from powermem.utils.utils import generate_snowflake_id

logger = logging.getLogger(__name__)


class YourProviderVectorStore(VectorStoreBase):
    """YourProvider vector store implementation"""

    def __init__(
        self,
        collection_name: str = "memories",
        # Add your provider-specific parameters
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the collection
            host: Server host
            port: Server port
        """
        self.collection_name = collection_name
        # Initialize your provider client here
        logger.info(f"YourProviderVectorStore initialized")

    def create_col(self, name=None, vector_size=None, distance="cosine"):
        """Create a new collection."""
        collection_name = name or self.collection_name
        # Implement collection creation logic
        pass

    def insert(self, vectors: List[List[float]], payloads=None, ids=None) -> List[int]:
        """
        Insert vectors into the collection.

        Args:
            vectors: List of vectors to insert
            payloads: List of payload dictionaries
            ids: Optional list of IDs (if None, will generate Snowflake IDs)

        Returns:
            List[int]: List of generated or provided IDs
        """
        if not vectors:
            return []

        if payloads is None:
            payloads = [{} for _ in vectors]

        # Generate IDs if not provided
        if ids is None:
            ids = [generate_snowflake_id() for _ in range(len(vectors))]

        # Implement insertion logic
        # ...

        return ids

    def search(
        self,
        query: List[float],
        vectors: Optional[List[List[float]]] = None,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[OutputData]:
        """
        Search for similar vectors.

        Args:
            query: Query vector
            vectors: Optional list of vectors to search in
            limit: Maximum number of results
            filters: Optional metadata filters

        Returns:
            List[OutputData]: List of search results
        """
        # Implement search logic
        results = []
        # ...
        return results

    def delete(self, vector_id: int) -> bool:
        """Delete a vector by ID."""
        # Implement deletion logic
        return True

    def update(self, vector_id: int, vector=None, payload=None) -> bool:
        """Update a vector and its payload."""
        # Implement update logic
        return True

    def get(self, vector_id: int) -> Optional[OutputData]:
        """Retrieve a vector by ID."""
        # Implement retrieval logic
        return None

    def list_cols(self) -> List[str]:
        """List all collections."""
        # Implement list logic
        return []

    def delete_col(self, name=None) -> bool:
        """Delete a collection."""
        # Implement deletion logic
        return True

    def col_info(self) -> Dict[str, Any]:
        """Get information about a collection."""
        # Implement info retrieval
        return {}

    def list(self, filters=None, limit=None) -> List[OutputData]:
        """List all memories."""
        # Implement list logic
        return []

    def reset(self) -> bool:
        """Reset by deleting the collection and recreating it."""
        self.delete_col()
        self.create_col()
        return True
```
### 第 2 步：创建配置类 {#step-2-create-configuration-class}

在 `src/powermem/storage/config/your_provider.py` 中创建一个配置文件：
```python
"""
Configuration for YourProvider vector store
"""
from typing import Optional
from pydantic import Field

from powermem.storage.config.base import BaseVectorStoreConfig


class YourProviderConfig(BaseVectorStoreConfig):
    """Configuration for YourProvider vector store"""

    host: str = Field(description="Server host")
    port: int = Field(default=5432, description="Server port")
    # Add other provider-specific fields

    class Config:
        extra = "allow"
```
更新 `src/powermem/storage/configs.py` 以包含你的配置：
```python
from powermem.storage.config.your_provider import YourProviderConfig

class VectorStoreConfig(BaseModel):
    # ...
    _provider_configs: Dict[str, str] = {
        "oceanbase": "OceanBaseConfig",
        "pgvector": "PGVectorConfig",
        "sqlite": "SQLiteConfig",
        "your_provider": "YourProviderConfig",  # Add this
    }
```
### 第三步：在 Factory 中注册 {#step-3-register-in-factory}

更新文件 `src/powermem/storage/factory.py`：
```python
class VectorStoreFactory:
    provider_to_class = {
        "oceanbase": "powermem.storage.oceanbase.oceanbase.OceanBaseVectorStore",
        "sqlite": "powermem.storage.sqlite.sqlite_vector_store.SQLiteVectorStore",
        "pgvector": "powermem.storage.pgvector.pgvector.PGVectorStore",
        "postgres": "powermem.storage.pgvector.pgvector.PGVectorStore",
        "your_provider": "powermem.storage.your_provider.your_provider.YourProviderVectorStore",  # Add this
    }
```
### 第4步：添加测试 {#step-4-add-tests}

创建测试文件 `tests/integration/test_your_provider_vector_store.py`：
```python
import pytest
from powermem.storage.factory import VectorStoreFactory


def test_your_provider_create_col():
    """Test collection creation"""
    config = {
        "collection_name": "test_collection",
        "host": "localhost",
        "port": 5432,
    }
    store = VectorStoreFactory.create("your_provider", config)
    store.create_col("test_col", vector_size=128, distance="cosine")
    assert store.col_info() is not None


def test_your_provider_insert_and_search():
    """Test insertion and search"""
    config = {
        "collection_name": "test_collection",
        "host": "localhost",
        "port": 5432,
    }
    store = VectorStoreFactory.create("your_provider", config)
    store.create_col("test_col", vector_size=128, distance="cosine")

    vectors = [[0.1] * 128, [0.2] * 128]
    payloads = [{"text": "test1"}, {"text": "test2"}]
    ids = store.insert(vectors, payloads)

    assert len(ids) == 2

    results = store.search([0.1] * 128, limit=1)
    assert len(results) > 0
```
## 添加一个 LLM 提供商 {#adding-an-llm-provider}

要添加一个新的 LLM 提供商：

1. **创建 LLM 实现**
2. **创建配置类**
3. **在工厂中注册**

### 第一步：创建 LLM 实现 {#step-1-create-llm-implementation}

创建 `src/powermem/integrations/llm/your_provider.py`：
```python
"""
YourProvider LLM implementation
"""
from typing import Dict, List, Optional

from powermem.integrations.llm import LLMBase
from powermem.integrations.llm.config.base import BaseLLMConfig
from powermem.integrations.llm.config.your_provider import YourProviderConfig

# Import your provider's SDK
try:
    from your_provider_sdk import YourProviderClient
except ImportError:
    raise ImportError(
        "The 'your_provider_sdk' library is required. "
        "Please install it using 'pip install your_provider_sdk'."
    )


class YourProviderLLM(LLMBase):
    """YourProvider LLM implementation"""

    def __init__(self, config: Optional[YourProviderConfig] = None):
        if config is None:
            config = YourProviderConfig()
        elif isinstance(config, dict):
            config = YourProviderConfig(**config)

        super().__init__(config)

        # Initialize your provider client
        self.client = YourProviderClient(
            **{"api_key": self.config.api_key},
            base_url=getattr(self.config, 'base_url', None),
        )

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        **kwargs,
    ) -> str:
        """
        Generate a response based on the given messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional response format specification
            tools: Optional list of tools for function calling
            tool_choice: Tool choice strategy
            **kwargs: Additional parameters

        Returns:
            str: Generated response text
        """
        # Prepare parameters
        params = self._get_supported_params(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            **kwargs
        )

        # Add provider-specific parameters
        params.update({
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        })

        # Call your provider's API
        response = self.client.chat.completions.create(**params)

        # Parse and return response
        return self._parse_response(response, tools)

    def _parse_response(self, response, tools=None):
        """Parse the response from the provider"""
        if tools:
            # Handle tool calls if supported
            return {
                "content": response.choices[0].message.content,
                "tool_calls": getattr(response.choices[0].message, 'tool_calls', []),
            }
        else:
            return response.choices[0].message.content
```
### 第 2 步：创建配置类 {#step-2-create-configuration-class-1}

创建 `src/powermem/integrations/llm/config/your_provider.py`：
```python
"""
Configuration for YourProvider LLM
"""
from typing import Optional
from pydantic import Field

from powermem.integrations.llm.config.base import BaseLLMConfig


class YourProviderConfig(BaseLLMConfig):
    """Configuration for YourProvider LLM"""

    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for the API"
    )
    # Add provider-specific fields

    class Config:
        extra = "allow"
```
### 第三步：在 Factory 中注册 {#step-3-register-in-factory-1}

更新 `src/powermem/integrations/llm/factory.py`：
```python
from powermem.integrations.llm.config.your_provider import YourProviderConfig

class LLMFactory:
    provider_to_class = {
        # ... existing providers ...
        "your_provider": ("powermem.integrations.llm.your_provider.YourProviderLLM", YourProviderConfig),
    }
```
### 第四步：添加到依赖项 {#step-4-add-to-dependencies}

如果您的提供者需要新的依赖项，请将其添加到 `pyproject.toml`：
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "your_provider_sdk>=1.0.0",
]
```
## 添加 Embedding 提供商 {#adding-an-embedding-provider}

要添加一个新的 Embedding 提供商：

1. **创建 Embedding 实现**
2. **在工厂中注册**

### 第一步：创建 Embedding 实现 {#step-1-create-embedding-implementation}

创建 `src/powermem/integrations/embeddings/your_provider.py`：
```python
"""
YourProvider embedding implementation
"""
from typing import Literal, Optional, List

from powermem.integrations.embeddings import EmbeddingBase
from powermem.integrations.embeddings.config.base import BaseEmbedderConfig

# Import your provider's SDK
try:
    from your_provider_sdk import YourProviderEmbeddingClient
except ImportError:
    raise ImportError(
        "The 'your_provider_sdk' library is required. "
        "Please install it using 'pip install your_provider_sdk'."
    )


class YourProviderEmbedding(EmbeddingBase):
    """YourProvider embedding implementation"""

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)

        # Initialize your provider client
        self.client = YourProviderEmbeddingClient(
            **{"api_key": getattr(self.config, 'api_key', None)},
            model=self.config.model,
        )

    def embed(
        self,
        text: str,
        memory_action: Optional[Literal["add", "search", "update"]] = None
    ) -> List[float]:
        """
        Get the embedding for the given text.

        Args:
            text: The text to embed
            memory_action: The type of embedding to use (optional)

        Returns:
            List[float]: The embedding vector
        """
        # Some providers support different embedding models for different actions
        model = self.config.model
        if memory_action == "search" and hasattr(self.config, 'search_model'):
            model = self.config.search_model

        # Call your provider's API
        response = self.client.embed(text, model=model)

        return response.embedding
```
### 第2步：在 Factory 中注册 {#step-2-register-in-factory}

更新 `src/powermem/integrations/embeddings/factory.py`：
```python
class EmbedderFactory:
    provider_to_class = {
        # ... existing providers ...
        "your_provider": "powermem.integrations.embeddings.your_provider.YourProviderEmbedding",
    }
```
## 添加 Reranker 提供者 {#adding-a-reranker-provider}

Reranker 通过根据查询的相关性重新排序文档来改进搜索结果。要添加一个新的 Reranker 提供者：

1. **创建 Reranker 实现**
2. **在工厂中注册它**

### 第一步：创建 Reranker 实现 {#step-1-create-reranker-implementation}

创建 `src/powermem/integrations/rerank/your_provider.py`：
```python
"""
YourProvider reranker implementation
"""
import os
from typing import List, Optional, Tuple

from powermem.integrations.rerank.base import RerankBase
from powermem.integrations.rerank.config.base import BaseRerankConfig

# Import your provider's SDK
try:
    from your_provider_sdk import YourProviderRerankClient
except ImportError:
    raise ImportError(
        "The 'your_provider_sdk' library is required. "
        "Please install it using 'pip install your_provider_sdk'."
    )


class YourProviderRerank(RerankBase):
    """YourProvider reranker implementation"""

    def __init__(self, config: Optional[BaseRerankConfig] = None):
        super().__init__(config)

        # Set default model
        self.config.model = self.config.model or "your-rerank-model"

        # Initialize your provider client
        credential = self.config.api_key or os.getenv("YOUR_PROVIDER_API_KEY")
        if not credential:
            raise ValueError(
                "API key is required. Set YOUR_PROVIDER_API_KEY environment variable "
                "or pass api_key in config."
            )

        self.client = YourProviderRerankClient(**{"api_key": credential})

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents based on relevance to the query.

        Args:
            query: The search query
            documents: List of document texts to rerank
            top_n: Number of top results to return

        Returns:
            List[Tuple[int, float]]: List of (document_index, relevance_score) tuples,
                                     sorted by relevance score in descending order
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not documents or len(documents) == 0:
            raise ValueError("Documents list cannot be empty")

        # Use provided top_n or return all results
        effective_top_n = top_n if top_n is not None else len(documents)

        try:
            # Call your provider's rerank API
            response = self.client.rerank(
                query=query,
                documents=documents,
                model=self.config.model,
                top_n=effective_top_n,
            )

            # Parse results - format: [(index, score), ...]
            results = []
            for item in response.results:
                index = item.index
                score = item.relevance_score
                results.append((index, float(score)))

            # Sort by score descending (highest first)
            results.sort(key=lambda x: x[1], reverse=True)

            return results

        except Exception as e:
            raise Exception(f"Failed to rerank documents: {e}")
```
### 第2步：在 Factory 中注册 {#step-2-register-in-factory-1}

更新 `src/powermem/integrations/rerank/factory.py`：
```python
class RerankFactory:
    provider_to_class = {
        "qwen": "powermem.integrations.rerank.qwen.QwenRerank",
        "your_provider": "powermem.integrations.rerank.your_provider.YourProviderRerank",  # Add this
    }
```
### 第三步：配置 Reranker {#step-3-configure-reranker}

在您的配置中启用 reranker：
```python
from powermem import Memory

config = {
    "reranker": {
        "enabled": True,
        "provider": "your_provider",
        "config": {
            "model": "your-rerank-model",
            "api_key": "your-api-key",
        },
    },
    # ... other config
}

memory = Memory(config=config)
```
或者通过环境变量：
```bash
export RERANKER_ENABLED=true
export RERANKER_PROVIDER=your_provider
export RERANKER_MODEL=your-rerank-model
export RERANKER_API_KEY=your-api-key
```
## 测试 {#testing}

### 运行测试 {#running-tests}
```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run end-to-end tests
make test-e2e

# Run tests with coverage
make test-coverage
```
### 编写测试 {#writing-tests}

- **单元测试**: 独立测试各个函数和类
- **集成测试**: 测试组件之间的交互
- **端到端测试 (E2E tests)**: 测试完整的工作流程

将测试放置在以下目录：
- `tests/unit/` 用于单元测试
- `tests/integration/` 用于集成测试
- `tests/e2e/` 用于端到端测试

### 测试结构 {#test-structure}
```python
import pytest
from powermem import Memory


def test_feature_name():
    """Test description"""
    # Arrange
    memory = Memory()

    # Act
    result = memory.some_method()

    # Assert
    assert result is not None
```
## 代码风格和标准 {#code-style-and-standards}

### 格式化 {#formatting}

该项目使用 `black` 进行代码格式化，并使用 `isort` 进行导入排序：
```bash
# Format code
make format

# Check formatting without making changes
make format-check
```
### 代码检查 {#linting}

```bash
# Run linter
make lint
```
### 类型检查 {#type-checking}
```bash
# Run type checker
make type-check
```
### 代码风格指南 {#code-style-guidelines}

1. **遵循 PEP 8** 风格指南
2. **为函数参数和返回值使用类型提示**
3. **为所有类和公共方法编写文档字符串**
4. **保持函数专注** - 每个函数只负责一个职责
5. **使用有意义的变量名**
6. **适当处理错误** - 在需要的地方使用 try/except
7. **为重要操作添加日志**

### 示例代码风格 {#example-code-style}
```python
"""
Module docstring describing the purpose of this module.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExampleClass:
    """
    Class docstring describing what this class does.

    Args:
        param1: Description of param1
        param2: Description of param2
    """

    def __init__(self, param1: str, param2: Optional[int] = None):
        """Initialize the class."""
        self.param1 = param1
        self.param2 = param2
        logger.info(f"Initialized ExampleClass with param1={param1}")

    def example_method(self, input_data: Dict[str, str]) -> List[str]:
        """
        Method docstring describing what this method does.

        Args:
            input_data: Dictionary containing input data

        Returns:
            List of processed strings

        Raises:
            ValueError: If input_data is empty
        """
        if not input_data:
            raise ValueError("input_data cannot be empty")

        # Implementation here
        return []
```
## 发布到 PyPI {#publishing-to-pypi}

### 前置条件 {#prerequisites-1}

在发布到 PyPI 之前，请确保您已完成以下操作：

1. **PyPI 账户**：在 [pypi.org](https://pypi.org) 创建一个账户
2. **API tokens**：从您的 PyPI 账户设置中生成 API tokens
3. **配置凭据**：设置 `~/.pypirc` 或使用环境变量

### 发布流程 {#publishing-process}

1. 在 `pyproject.toml` 中**更新版本**：
```toml
[project]
version = "0.1.1"  # Increment version number
```
2. **更新变更日志**（如果您维护了一个）

3. **构建并检查包**：
```bash
make build-check
```
4. **本地测试**：
```bash
make install-local
# Test the installed package
python -c "import powermem; print(powermem.__version__)"
```
5. **先发布到 TestPyPI**（推荐）：
```bash
make publish-testpypi
```
6. **从 TestPyPI 测试安装**：
```bash
pip install --index-url https://test.pypi.org/simple/ powermem
```
7. **发布到 PyPI**：
```bash
make publish-pypi
```
### 版本管理 {#version-management}

遵循[语义化版本控制](https://semver.org/)：

- **主版本号** (1.0.0): 不兼容的 API 更改
- **次版本号** (0.1.0): 向后兼容的新功能
- **修订号** (0.0.1): 向后兼容的错误修复

### Git 标签 {#git-tagging}

发布后，创建一个 git 标签：
```bash
git tag -a v0.1.1 -m "Release version 0.1.1"
git push origin v0.1.1
```
## 调试 {#debugging}

### 启用调试日志 {#enable-debug-logging}

将日志级别设置为 DEBUG：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
或者设置环境变量：
```bash
export LOG_LEVEL=DEBUG
```
### 常见调试场景 {#common-debugging-scenarios}

1. **Vector Store 连接问题**：
```python
from powermem.storage.factory import VectorStoreFactory

# Test connection
config = {
    "collection_name": "test",
    "host": "localhost",
    "port": 2881,
    # ... other config
}
store = VectorStoreFactory.create("oceanbase", config)
print(store.col_info())  # Check if connection works
```
2. **LLM API 问题**：
```python
from powermem.integrations.llm.factory import LLMFactory

# Test LLM connection
config = {
    "model": "gpt-4",
    "api_key": "your-key",
}
llm = LLMFactory.create("openai", config)
response = llm.generate_response([{"role": "user", "content": "test"}])
print(response)
```
3. **Embedding 问题**:
```python
from powermem.integrations.embeddings.factory import EmbedderFactory

# Test embedding
config = {
    "model": "text-embedding-3-small",
    "api_key": "your-key",
}
embedder = EmbedderFactory.create("openai", config)
vector = embedder.embed("test text")
print(f"Vector dimension: {len(vector)}")
```
## 性能优化 {#performance-optimization}

### Vector Store 优化 {#vector-store-optimization}

1. **索引配置**：
```python
# For OceanBase
config = {
    "index_type": "HNSW",  # Use HNSW for better performance
    "vidx_metric_type": "l2",  # Choose appropriate metric
    # ... other config
}
```
2. **批量操作**：
```python
# Insert multiple vectors at once
vectors = [[0.1] * 1536 for _ in range(100)]
payloads = [{"text": f"text_{i}"} for i in range(100)]
ids = store.insert(vectors, payloads)  # Batch insert
```
3. **连接池**：
```python
# Use connection pooling for better performance
config = {
    "pool_size": 10,
    "max_overflow": 20,
    # ... other config
}
```
### 记忆优化 {#memory-optimization}

1. **使用异步操作**：
```python
from powermem import AsyncMemory

memory = AsyncMemory()
# Async operations are more efficient for I/O-bound tasks
await memory.add("text", user_id="user1")
```
2. **批量记忆操作**：
```python
# Add multiple memories efficiently
memories = [
    "User likes Python",
    "User works at tech company",
    "User prefers coffee over tea",
]
for mem in memories:
    memory.add(mem, user_id="user1")
```
## 常见问题及解决方案 {#common-issues-and-solutions}

### 问题：导入错误 {#issue-import-errors}

**问题**：在导入特定提供商模块时出现 `ModuleNotFoundError`

**解决方案**：安装所需的依赖项：
```bash
# For specific providers
pip install pyobvector  # For OceanBase
pip install pgvector    # For PostgreSQL
pip install dashscope    # For Qwen
```
### 问题：配置未加载 {#issue-configuration-not-loading}

**问题**：`.env` 文件中的配置未被加载

**解决方案**：确保文件路径正确：
```python
from powermem import create_memory

# Explicitly specify config file
memory = create_memory(config_file=".env")
```
### 问题：向量维度不匹配 {#issue-vector-dimension-mismatch}

**问题**：`ValueError: Vector dimension mismatch`

**解决方案**：确保嵌入模型的维度与向量存储配置相匹配：
```python
# Check embedding dimensions
embedder = EmbedderFactory.create("openai", {"model": "text-embedding-3-small"})
vector = embedder.embed("test")
print(f"Dimension: {len(vector)}")  # Should be 1536 for text-embedding-3-small

# Configure vector store with matching dimensions
store_config = {
    "embedding_model_dims": 1536,  # Must match embedding dimension
    # ... other config
}
```
### 问题：连接超时 {#issue-connection-timeout}

**问题**：连接到向量存储时出现超时错误

**解决方案**：增加超时时间并检查网络：
```python
config = {
    "host": "localhost",
    "port": 2881,
    "connect_timeout": 30,  # Increase timeout
    # ... other config
}
```
## 高级主题 {#advanced-topics}

### 自定义事实提取 {#custom-fact-extraction}

您可以自定义如何从消息中提取事实：
```python
from powermem import Memory

custom_prompt = """
Extract key facts from the following conversation.
Focus on: user preferences, important events, relationships.
"""

memory = Memory(
    config={
        "custom_fact_extraction_prompt": custom_prompt,
        # ... other config
    }
)
```
### 自定义记忆更新逻辑 {#custom-memory-update-logic}

自定义记忆的更新方式：
```python
custom_update_prompt = """
Update existing memories based on new information.
Merge similar memories and remove outdated ones.
"""

memory = Memory(
    config={
        "custom_update_memory_prompt": custom_update_prompt,
        # ... other config
    }
)
```
### 子存储配置 {#sub-stores-configuration}

配置子存储以更好地组织数据：
```python
config = {
    "storage_type": "oceanbase",
    "sub_stores": [
        {
            "name": "user_preferences",
            "filters": {"type": "preference"},
        },
        {
            "name": "events",
            "filters": {"type": "event"},
        },
    ],
    # ... other config
}
memory = Memory(config=config)
```
### 图存储集成 {#graph-store-integration}

启用图存储以支持基于关系的检索：
```python
config = {
    "graph_store": {
        "provider": "oceanbase",
        "config": {
            # Graph store configuration
        },
    },
    # ... other config
}
memory = Memory(config=config)
```
## 额外资源 {#additional-resources}

- **API 文档**: 请参阅 `docs/api/` 获取详细的 API 参考
- **示例**: 查看 `examples/` 目录中的使用示例
- **架构**: 请参阅 `docs/architecture/overview.md` 了解系统架构
- **问题**: 在 [GitHub Issues](https://github.com/oceanbase/powermem/issues) 上报告错误或提出功能请求

## 获取帮助 {#getting-help}

- **Discord**: 加入我们的 [Discord 社区](https://discord.com/invite/74cF8vbNEs)
- **GitHub Discussions**: 在 [GitHub Discussions](https://github.com/oceanbase/powermem/discussions) 中提问
- **文档**: 浏览 [文档](https://www.powermem.ai/docs)

---

祝编码愉快！🚀
