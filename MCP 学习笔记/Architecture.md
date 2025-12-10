# 组成部分

MCP 采用客户端-服务器架构，其中一个 MCP 主机——如 [Claude Code](https://www.anthropic.com/claude-code) 或 [Claude Desktop](https://www.claude.ai/download) 等 AI 应用程序——建立与一个或多个 MCP 服务器的连接。MCP 主机通过为每个 MCP 服务器创建一个 MCP 客户端来实现这一点。每个 MCP 客户端与其对应的 MCP 服务器保持专用的一对一连接。

![[Pasted image 20251117134008.png]]

MCP 架构的主要参与者有：
- **MCP Host**：协调和管理一个或多个 MCP 客户端的 AI 应用
- **MCP Client** ：一个组件，负责维护与 MCP 服务器的连接，并从该 MCP 服务器获取上下文供 MCP 主机使用
- **MCP Server** ：为 MCP 客户端提供上下文的程序

**例如** ：Visual Studio Code 作为 MCP 主机。当 Visual Studio Code 建立与 MCP 服务器（如 [Sentry MCP 服务器](https://docs.sentry.io/product/sentry-mcp/) ）的连接时，Visual Studio Code 运行时实例化一个 MCP 客户端对象，维护与 Sentry MCP 服务器的连接。当 Visual Studio Code 随后连接到另一个 MCP 服务器（如[本地文件系统服务器](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) ）时，Visual Studio Code 运行时实例化一个额外的 MCP 客户端对象以维持连接，从而维持 MCP 客户端与 MCP 服务器之间的一一对应关系。
![[Pasted image 20251117140155.png]]

注意，**MCP 服务器**指的是提供上下文数据的程序，无论其运行地点如何。MCP 服务器可以本地或远程执行。例如，当 Claude Desktop 启动[文件系统服务器](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)时， 服务器运行在同一台机器上，因为它使用了 STDIO 运输。 这通常被称为“本地”MCP 服务器。官方 [Sentry MCP 服务器](https://docs.sentry.io/product/sentry-mcp/)运行在 Sentry 平台上，使用可流式 HTTP 传输。这通常被称为“远程”MCP 服务器。

# Layers

MCP 由两层组成：

- **Data layer**：定义基于 JSON-RPC 的客户端-服务器通信协议，包括生命周期管理及核心原语，如工具、资源、提示和通知。
- **Transport layer**：定义支持客户端与服务器之间数据交换的通信机制和通道，包括传输专用连接建立、消息框架和授权。

从概念上讲，数据层是内层，而传输层是外层。

#### Data layer 

数据层实现了基于 [JSON-RPC 2.0](https://www.jsonrpc.org/) 的交换协议，定义了消息结构和语义。该层包括：

- **Lifecycle management**: 
    **生命周期管理** ：处理客户端与服务器之间的连接初始化、能力协商和连接终止
- **Server features**: 
    **服务器功能** ：使服务器能够提供核心功能，包括 AI 作工具、上下文数据资源，以及客户端交互模板的提示
- **Client features**: 
    **客户端功能** ：使服务器能够请求客户端从主机 LLM 采样，从用户那里获取输入，并向客户端记录消息
- **Utility features**: 
    **实用功能** ：支持实时更新通知和长期运行作的进度跟踪等额外功能

#### Transport layer 

传输层管理客户端和服务器之间的通信通道和身份验证。它处理 MCP 参与者之间的连接建立、消息成帧和安全通信。
MCP 支持两种传输机制：

- **Stdio transport**: 
    **标准传输** ：使用标准输入/输出流在同一台机器上的本地进程之间进行直接进程通信，提供最佳性能，没有网络开销。
- **Streamable HTTP transport**: 
    **可流式传输 HTTP 传输** ：将 HTTP POST 用于客户端到服务器消息，并使用可选的服务器发送事件来实现流式处理功能。此传输支持远程服务器通信，并支持标准 HTTP 身份验证方法，包括持有者令牌、API 密钥和自定义标头。MCP 建议使用 OAuth 获取身份验证令牌。
 
传输层从协议层抽象出通信细节，从而在所有传输机制中实现相同的 JSON-RPC 2.0 消息格式。