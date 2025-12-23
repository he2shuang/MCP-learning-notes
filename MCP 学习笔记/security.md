https://modelcontextprotocol.io/docs/tutorials/security/authorization


## Keycloak

为了开始一个实用的实现，我们将使用托管在 Docker 容器中的 [Keycloak](https://www.keycloak.org/) 授权服务器。Keycloak 是一个开源授权服务器，可以轻松部署到本地进行测试和实验。

运行docker镜像
```
docker run -p 127.0.0.1:8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak start-dev
```

在本地打开`http://localhost:8080`，用户名`admin`，密码`admin`

```
# 停止，删除

docker stop <容器ID>
docker rm <容器ID>
```

## 流程详解

#### 第一阶段：获取授权码 (用户登录与授权)

这个阶段主要发生在你的**浏览器**和**Keycloak**之间，由VS Code扩展发起。

**步骤 1: 客户端发起认证请求**

- **动作**: 你在VS Code中触发了一个需要认证的操作（比如调用一个API工具）。
- **幕后**: VS Code扩展发现自己没有访问令牌，于是它在后台准备发起认证。它先生成一个秘密的`code_verifier`，然后用`S256`算法计算出`code_challenge`。
- **结果**: 扩展构建一个长长的URL，并用你的默认浏览器打开它。
    - **URL**: `http://localhost:8080/.../auth?client_id=vscode-mcp-client&...&code_challenge=...&redirect_uri=...`
    - **意图**: “你好Keycloak，我是`vscode-mcp-client`，我想让用户登录，并请求一些权限。这是我的挑战码（`code_challenge`），你验证完用户后请把他们送回这个地址（`redirect_uri`）。”

**步骤 2: 用户认证与授权**

- **动作**: 浏览器显示出Keycloak的登录页面。你输入用户名和密码。
- **幕后**: 登录成功后，Keycloak可能会显示一个“同意授权”页面，询问你是否允许`vscode-mcp-client`访问你的`mcp:tools`权限。你点击“同意”。
- **结果**: Keycloak确认了你的身份和你的许可。

**步骤 3: Keycloak返回授权码**

- **动作**: Keycloak将你的浏览器重定向到VS Code扩展指定的`redirect_uri`（比如`http://127.0.0.1:33418/`）。
- **幕后**: 在重定向的URL中，Keycloak附上了一个一次性的**授权码 (Authorization Code)** 和之前收到的`state`参数。
- **结果**: 浏览器跳转，VS Code扩展的本地服务器捕获了这个带有授权码的请求。
    - **URL**: `http://127.0.0.1:33418/?code=...&state=...`

#### 第二阶段：交换令牌与访问资源

这个阶段主要发生在**VS Code扩展的后台**和你的**Python服务器**之间，用户无感知。

**步骤 4: 客户端用授权码交换访问令牌**

- **动作**: VS Code扩展的后台进程，向Keycloak的**令牌端点 (Token Endpoint)** 发送一个`POST`请求。
- **幕后**: 这个请求是后台发出的，浏览器看不到。请求中包含了：
    - 刚刚收到的`authorization_code`
    - 自己的`client_id` (`vscode-mcp-client`)
    - 最初生成的秘密`code_verifier` (这就是PKCE安全机制的关键，用来证明自己就是发起请求的那个客户端)
- **结果**: Keycloak验证`code_verifier`和之前的`code_challenge`是否匹配。匹配成功后，返回一个包含**访问令牌 (Access Token)** 的JSON。

**步骤 5: 客户端携带令牌访问资源服务器**

- **动作**: VS Code扩展现在手握`Access Token`，终于可以去访问你的Python API了。它向`http://localhost:3000/`发送API请求（比如调用`add_numbers`）。
- **幕后**: 在请求的`Authorization`头中，它会附上令牌。
    - **Header**: `Authorization: Bearer eyJhbGciOiJSUzI1...`
- **结果**: 你的Python服务器收到了这个请求。

#### 第三阶段：资源服务器验证令牌

这个阶段发生在你的**Python服务器**和**Keycloak**之间。

**步骤 6: 资源服务器进行令牌自省 (Introspection)**

- **动作**: 你的Python服务器（`IntrospectionTokenVerifier`）收到了令牌，但它不信任这个令牌。它需要去Keycloak那里确认令牌的真伪。
- **幕后**: 你的服务器向Keycloak的**自省端点 (Introspection Endpoint)** 发送一个`POST`请求。这个请求中包含了：
    - 要验证的`token`
    - **自己的身份凭证**：`client_id=mcp-first-client` 和 `client_secret=...` (这就是为什么你需要一个`confidential`客户端和它的密码)
- **结果**: Keycloak验证`mcp-first-client`的凭证，并检查其服务账户是否有`read-token`等权限。

**步骤 7: Keycloak返回自省结果**

- **动作**: Keycloak在验证令牌后，向你的Python服务器返回一个JSON响应。
- **幕后**: 如果令牌有效，且`mcp-first-client`有权自省，Keycloak会返回`HTTP 200 OK`，响应正文是`{"active": true, ...}`。
- **结果**: 你的Python服务器收到了`{"active": true}`。

**步骤 8: 资源服务器返回受保护的资源**

- **动作**: 你的Python服务器确认令牌有效，于是执行`add_numbers`的逻辑。
- **幕后**: 计算结果，并将其打包成一个JSON响应。
- **结果**: 你的服务器向VS Code扩展返回`HTTP 200 OK`和计算结果。最终，你在VS Code的UI上看到了API调用的成功结果。


## MCP 服务器设置

在编写实际服务器之前，我们需要先在 `config.py` 中设置配置——内容完全基于你的本地服务器设置：

```
"""Configuration settings for the MCP auth server."""
  
import os
from typing import Optional
  
  
class Config:
    """Configuration class that loads from environment variables with sensible defaults."""
  
    # Server settings
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "3000"))
  
    # Auth server settings
    AUTH_HOST: str = os.getenv("AUTH_HOST", "localhost")
    AUTH_PORT: int = int(os.getenv("AUTH_PORT", "8080"))
    AUTH_REALM: str = os.getenv("AUTH_REALM", "master")
  
    # OAuth client settings
    OAUTH_CLIENT_ID: str = os.getenv("OAUTH_CLIENT_ID", "mcp-first-client")
    OAUTH_CLIENT_SECRET: str = os.getenv("OAUTH_CLIENT_SECRET", "OxZDlvEqeJkludCd3zMEACgzM4LXIayE")
  
    # Server settings
    MCP_SCOPE: str = os.getenv("MCP_SCOPE", "mcp:tools")
    OAUTH_STRICT: bool = os.getenv("OAUTH_STRICT", "false").lower() in ("true", "1", "yes")
    TRANSPORT: str = os.getenv("TRANSPORT", "streamable-http")
  
    @property
    def server_url(self) -> str:
        """Build the server URL."""
        return f"http://{self.HOST}:{self.PORT}"
  
    @property
    def auth_base_url(self) -> str:
        """Build the auth server base URL."""
        return f"http://{self.AUTH_HOST}:{self.AUTH_PORT}/realms/{self.AUTH_REALM}/"
  
    def validate(self) -> None:
        """Validate configuration."""
        if self.TRANSPORT not in ["sse", "streamable-http"]:
            raise ValueError(f"Invalid transport: {self.TRANSPORT}. Must be 'sse' or 'streamable-http'")
  
  
# Global configuration instance
config = Config()
```


服务器实现如下：

```
import datetime
import logging
from typing import Any
  
from pydantic import AnyHttpUrl
  
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp.server import FastMCP
  
from config import config
from token_verifier import IntrospectionTokenVerifier
  
logger = logging.getLogger(__name__)
  
  
def create_oauth_urls() -> dict[str, str]:
    """Create OAuth URLs based on configuration (Keycloak-style)."""
    from urllib.parse import urljoin
  
    auth_base_url = config.auth_base_url
  
    return {
        "issuer": auth_base_url,
        "introspection_endpoint": urljoin(auth_base_url, "protocol/openid-connect/token/introspect"),
        "authorization_endpoint": urljoin(auth_base_url, "protocol/openid-connect/auth"),
        "token_endpoint": urljoin(auth_base_url, "protocol/openid-connect/token"),
    }
  
  
def create_server() -> FastMCP:
    """Create and configure the FastMCP server."""
  
    config.validate()
  
    oauth_urls = create_oauth_urls()
  
    token_verifier = IntrospectionTokenVerifier(
        introspection_endpoint=oauth_urls["introspection_endpoint"],
        server_url=config.server_url,
        client_id=config.OAUTH_CLIENT_ID,
        client_secret=config.OAUTH_CLIENT_SECRET,
    )
  
    app = FastMCP(
        name="MCP Resource Server",
        instructions="Resource Server that validates tokens via Authorization Server introspection",
        host=config.HOST,
        port=config.PORT,
        debug=True,
        streamable_http_path="/",
        token_verifier=token_verifier,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(oauth_urls["issuer"]),
            required_scopes=[config.MCP_SCOPE],
            resource_server_url=AnyHttpUrl(config.server_url),
            client_id=config.OAUTH_CLIENT_ID,
        ),
    )
  
    @app.tool()
    async def add_numbers(a: float, b: float) -> dict[str, Any]:
        """
        Add two numbers together.
        This tool demonstrates basic arithmetic operations with OAuth authentication.
  
        Args:
            a: The first number to add
            b: The second number to add
        """
        result = a + b
        return {
            "operation": "addition",
            "operand_a": a,
            "operand_b": b,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        }
  
    @app.tool()
    async def multiply_numbers(x: float, y: float) -> dict[str, Any]:
        """
        Multiply two numbers together.
        This tool demonstrates basic arithmetic operations with OAuth authentication.
  
        Args:
            x: The first number to multiply
            y: The second number to multiply
        """
        result = x * y
        return {
            "operation": "multiplication",
            "operand_x": x,
            "operand_y": y,
            "result": result,
            "timestamp": datetime.datetime.now().isoformat()
        }
  
    return app
  
  
def main() -> int:
    """
    Run the MCP Resource Server.
  
    This server:
    - Provides RFC 9728 Protected Resource Metadata
    - Validates tokens via Authorization Server introspection
    - Serves MCP tools requiring authentication
  
    Configuration is loaded from config.py and environment variables.
    """
    logging.basicConfig(level=logging.INFO)
  
    try:
        config.validate()
        oauth_urls = create_oauth_urls()

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        return 1
  
    try:
        mcp_server = create_server()
  
        logger.info("Starting MCP Server on %s:%s", config.HOST, config.PORT)
        logger.info("Authorization Server: %s", oauth_urls["issuer"])
        logger.info("Transport: %s", config.TRANSPORT)
  
        mcp_server.run(transport=config.TRANSPORT)
        return 0
  
    except Exception:
        logger.exception("Server error")
        return 1
  
  
if __name__ == "__main__":
    exit(main())
```

最后，令牌验证逻辑完全委托给 `token_verifier.py`，确保我们能利用 Keycloak 的内省端点验证任何凭据伪造物的有效性

```
"""Token verifier implementation using OAuth 2.0 Token Introspection (RFC 7662)."""
  
import logging
from typing import Any
  
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.shared.auth_utils import check_resource_allowed, resource_url_from_server_url
  
logger = logging.getLogger(__name__)
  
  
class IntrospectionTokenVerifier(TokenVerifier):
    """Token verifier that uses OAuth 2.0 Token Introspection (RFC 7662).
    """
  
    def __init__(
        self,
        introspection_endpoint: str,
        server_url: str,
        client_id: str,
        client_secret: str,
    ):
        self.introspection_endpoint = introspection_endpoint
        self.server_url = server_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.resource_url = resource_url_from_server_url(server_url)
  
    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token via introspection endpoint."""
        import httpx
  
        # --- 新增的打印点 1: 打印传入的原始令牌 ---
        # print("--- RAW TOKEN RECEIVED BY VERIFIER ---")
        # print(token)
        # print("------------------------------------")
        if not self.introspection_endpoint.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            return None

  
        timeout = httpx.Timeout(10.0, connect=5.0)
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
  
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            verify=True,
        ) as client:
            try:
                form_data = {
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
  
                # --- 你已有的打印点: 打印将要发送的请求 ---
                # print("--- DEBUG: Introspection Request ---")
                # print(f"URL: {self.introspection_endpoint}")
                # print(f"Headers: {headers}")
                # print(f"Data: {form_data}")
                # print("------------------------------------")
  
                response = await client.post(
                    self.introspection_endpoint,
                    data=form_data,
                    headers=headers,
                )
                # --- 新增的打印点 2: 打印收到的原始响应 ---
                # print("--- DEBUG: Introspection Response ---")
                # print(f"Status Code: {response.status_code}")
                # try:
                #     # 尝试解析为JSON并打印
                #     response_data = response.json()
                #     print(f"Response JSON: {response_data}")
                # except Exception as json_error:
                #     # 如果不是JSON，打印原始文本
                #     print(f"Response Text: {response.text}")
                #     print(f"JSON Parsing Error: {json_error}")
                # print("-------------------------------------")
  
                if response.status_code != 200:
                    print("DEBUG: Introspection failed due to non-200 status code.")
                    return None
  
                data = response.json()
                if not data.get("active", False):
                    print("DEBUG: Introspection successful, but token is NOT active.")
                    return None
  
                if not self._validate_resource(data):
                    print("DEBUG: Token is active, but resource/audience validation failed.")
                    return None
  
                # 如果一切正常，也会打印一条成功日志
                print("DEBUG: Token is active and resource validation successful. Proceeding.")
                return AccessToken(
                    token=token,
                    client_id=data.get("client_id", "unknown"),
                    scopes=data.get("scope", "").split() if data.get("scope") else [],
                    expires_at=data.get("exp"),
                    # resource=data.get("aud"),  # Include resource in token
                    resource=self.resource_url, # <--- 直接使用我们自己的resource_url
                )
  
            except Exception as e:
                print(f"DEBUG: An exception occurred during token verification: {e}")
                return None
  
    def _validate_resource(self, token_data: dict[str, Any]) -> bool:
        """Validate token was issued for this resource server.
  
        Rules:
        - Reject if 'aud' missing.
        - Accept if any audience entry matches the derived resource URL.
        - Supports string or list forms per JWT spec.
        """
        if not self.server_url or not self.resource_url:
            return False
  
        aud: list[str] | str | None = token_data.get("aud")
        if isinstance(aud, list):
            return any(self._is_valid_resource(a) for a in aud)
        if isinstance(aud, str):
            return self._is_valid_resource(aud)
        return False
  
    def _is_valid_resource(self, resource: str) -> bool:
        """Check if the given resource matches our server."""
        return check_resource_allowed(self.resource_url, resource)
```


### 注意事项

除了要按照`https://modelcontextprotocol.io/docs/tutorials/security/authorization#implementation-example`中类似的创建用于令牌内省的客户端，还需要创建一个公共客户端，用于VSCode进行身份认证时填入Client ID，并且要保证这个客户端要根据VSCode插件的要求，设置对应的`Valid Redirect URIs`
![[Pasted image 20251223143640.png]]

![[Pasted image 20251223143802.png]]