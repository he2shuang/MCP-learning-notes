# Model Context Protocol (MCP) Architecture Overview

## Scope
The Model Context Protocol includes:
- **MCP Specification**: Implementation requirements for clients and servers
- **MCP SDKs**: Language-specific SDKs that implement MCP
- **MCP Development Tools**: Tools for developing MCP servers and clients (including MCP Inspector)
- **MCP Reference Server Implementations**: Reference implementations of MCP servers

MCP focuses solely on the protocol for context exchange—it does not dictate how AI applications use LLMs or manage the provided context.

## Concepts of MCP

### Participants
MCP follows a client-server architecture with three key participants:

1. **MCP Host**: The AI application that coordinates and manages one or multiple MCP clients (e.g., Visual Studio Code, Claude Desktop)
2. **MCP Client**: A component that maintains a connection to an MCP server and obtains context for the MCP host to use
3. **MCP Server**: A program that provides context to MCP clients

Each MCP client maintains a dedicated one-to-one connection with its corresponding MCP server. MCP servers can execute locally or remotely.

### Layers
MCP consists of two layers:

#### 1. Data Layer
- Defines the JSON-RPC based protocol for client-server communication
- Includes lifecycle management and core primitives (tools, resources, prompts, notifications)
- Components:
  - **Lifecycle management**: Connection initialization, capability negotiation, termination
  - **Server features**: Tools for AI actions, resources for context data, prompts for interaction templates
  - **Client features**: Sampling from host LLM, eliciting user input, logging messages
  - **Utility features**: Notifications for real-time updates, progress tracking

#### 2. Transport Layer
- Manages communication channels and authentication between clients and servers
- Handles connection establishment, message framing, and secure communication
- Supported transport mechanisms:
  - **Stdio transport**: Uses standard input/output streams for local process communication (optimal performance, no network overhead)
  - **Streamable HTTP transport**: Uses HTTP POST with optional Server-Sent Events for streaming capabilities (enables remote server communication)

### Data Layer Protocol
MCP uses JSON-RPC 2.0 as its underlying RPC protocol. Clients and servers send requests to each other and respond accordingly.

#### Primitives
MCP defines three core primitives that servers can expose:

1. **Tools**: Executable functions that AI applications can invoke to perform actions (e.g., file operations, API calls, database queries)
2. **Resources**: Data sources that provide contextual information to AI applications (e.g., file contents, database records, API responses)
3. **Prompts**: Reusable templates that help structure interactions with language models (e.g., system prompts, few-shot examples)

Each primitive type has associated methods for discovery (*/list), retrieval (*/get), and execution (tools/call).

#### Client Primitives
MCP also defines primitives that clients can expose:

1. **Sampling**: Allows servers to request language model completions from the client's AI application
2. **Elicitation**: Allows servers to request additional information from users
3. **Logging**: Enables servers to send log messages to clients for debugging and monitoring

#### Notifications
The protocol supports real-time notifications to enable dynamic updates between servers and clients. For example, when a server's available tools change, it can notify connected clients.

#### Tasks (Experimental)
Durable execution wrappers that enable deferred result retrieval and status tracking for MCP requests (e.g., expensive computations, workflow automation).

## How MCP Works in Practice

### Example Architecture
- An AI application (MCP Host) like Visual Studio Code connects to multiple MCP servers
- For each server connection, the host creates a dedicated MCP Client
- Each client maintains a one-to-one connection with its server
- Servers can be local (using Stdio transport) or remote (using HTTP transport)

### Key Benefits
- **Protocol abstraction**: Same JSON-RPC 2.0 message format across all transport mechanisms
- **Flexibility**: Supports both local and remote server deployments
- **Extensibility**: Primitives system allows for rich context exchange and interaction
- **Real-time updates**: Notification system enables dynamic changes

## Development Focus
Most developers will find the data layer—particularly the set of primitives—to be the most interesting part of MCP, as it defines how context can be shared from MCP servers to MCP clients.