MCP 客户端由主机应用程序实例化，用于与特定 MCP 服务器通信。主机应用程序如 Claude.ai 或 IDE，负责整体用户体验并协调多个客户端。每个客户端与一台服务器直接通信一次。
理解这一区别很重要： _主机_ 是用户交互的**应用程序**，而 _客户端_ 是实现服务器连接的**协议级组件**。

# 核心客户端功能

除了利用服务器提供的上下文外，客户端还可以为服务器提供若干功能。这些客户端功能使服务器作者能够构建更丰富的交互。

| Feature              | Explanation                                           | Example                                     |
| -------------------- | ----------------------------------------------------- | ------------------------------------------- |
| **Sampling  采样**     | 采样允许服务器通过客户端请求 LLM 完成，实现代理式工作流。这种方法使客户端完全掌控用户权限和安全措施。 | 预订旅行服务器可能会向 LLM 发送航班列表，并请求 LLM 为用户选择最合适的航班。 |
| **Roots  根**         | 根节点允许客户端指定服务器应关注的目录，通过协调机制传达预期范围。                     | 预订差旅的服务器可能会被授权访问特定的目录，从中读取用户的日历。            |
| **Elicitation  启发式** | Elicitation使服务器能够在交互过程中向用户请求特定信息，为服务器按需收集信息提供了结构化的方式。 | 服务器可能会询问用户对飞机座位、房间类型或联系电话的偏好，以完成预订。         |

### Sampling

Sampling 允许服务器通过客户端请求语言模型完成，从而实现代理行为，同时保持安全性和用户控制。

#### 概述

Sampling 使服务器能够执行依赖于 AI 的任务，而无需直接与 AI 模型集成或为 AI 模型付费。相反，服务器可以请求已经拥有 AI 模型访问权限的客户端代表他们处理这些任务。这种方法使客户端可以完全控制用户权限和安全措施。由于采样请求发生在其他作（如分析数据的工具）的上下文中，并且作为单独的模型调用进行处理，因此它们在不同上下文之间保持清晰的边界，从而可以更有效地使用上下文窗口。

**Sampling flow:**

![[Pasted image 20251118111316.png]]

该流程通过多个人机交互检查点确保安全性。用户可以在初始请求返回服务器之前查看并修改生成的响应。

**请求参数示例：**

```
{
  messages: [
    {
      role: "user",
      content: "Analyze these flight options and recommend the best choice:\n" +
               "[47 flights with prices, times, airlines, and layovers]\n" +
               "User preferences: morning departure, max 1 layover"
    }
  ],
  modelPreferences: {
    hints: [{
      name: "claude-sonnet-4-20250514"  // Suggested model
    }],
    costPriority: 0.3,      // Less concerned about API cost
    speedPriority: 0.2,     // Can wait for thorough analysis
    intelligencePriority: 0.9  // Need complex trade-off evaluation
  },
  systemPrompt: "You are a travel expert helping users find the best flights based on their preferences",
  maxTokens: 1500
}
```

#### 示例：飞行分析工具

考虑一个旅行预订服务器，其中包含一个名为 `findBestFlight` 的工具，该工具使用 sampling 来分析可用航班并推荐最佳选择。当用户询问“为我预订下个月飞往巴塞罗那的最佳航班”时，该工具需要人工智能的帮助来评估复杂的权衡。

该工具查询航空公司 API 并收集 47 个航班选项。然后，它请求人工智能协助分析这些选项：“分析这些航班选项并推荐最佳选择：47 个航班，包括价格、时间、航空公司和中途停留。用户偏好：早上出发，最多 1 次中途停留。

客户发起采样请求，允许人工智能评估权衡，例如更便宜的东方航班与方便的早晨出发。该工具使用此分析来呈现前三个建议。

#### 用户交互模型

虽然不是必需的，但采样旨在实现人机交互控制。用户可以通过多种机制进行监督：
 
**审批控制：** 抽样请求可能需要用户明确同意。客户端可以显示服务器想要分析的内容和原因。用户可以批准、拒绝或修改请求。

**透明度功能** ：客户端可以显示准确的提示、模型选择和令牌限制，允许用户在返回服务器之前查看 AI 响应。

**配置选项** ：用户可以设置模型首选项，为可信作配置自动批准，或要求所有作都获得批准。客户可以提供编辑敏感信息的选项。

**安全注意事项** ：客户端和服务器在采样过程中都必须适当地处理敏感数据。客户端应实现速率限制并验证所有消息内容。人机交互设计确保服务器启动的人工智能交互不会在未经用户明确同意的情况下危及安全或访问敏感数据。


### Roots  

Roots 定义了服务器作的文件系统边界，允许客户端指定服务器应关注的目录。

#### 概述

Roots 是一种让客户端向服务器传递文件系统访问边界的机制。它们由文件 URI 组成，指示服务器可以运行的目录，帮助服务器了解可用文件和文件夹的范围。虽然根节点传达预期边界，但不强制执行安全限制。实际的安全必须在作系统层面通过文件权限和/或沙箱来强制执行。

**Root structure:**

```
{
  "uri": "file:///Users/agent/travel-planning",
  "name": "Travel Planning Workspace"
}
```

Roots 是专门的文件系统路径，并且始终使用 `file://` URI 方案。它们帮助服务器了解项目边界、工作区组织和可访问的目录。当用户使用不同的项目或文件夹时，根列表可以动态更新，当边界发生变化时，服务器会通过`roots/list_changed` 接收通知。

#### 示例：旅行规划工作区

处理多个客户差旅的旅行社受益于 root 来组织文件系统访问。考虑一个具有不同目录的工作区，用于旅行计划的各个方面。 

客户端向旅行计划服务器提供文件系统根：
- `file:///Users/agent/travel-planning` - 包含所有旅行文件的主工作区
- `file:///Users/agent/travel-templates` - 可重复使用的行程模板和资源
- `file:///Users/agent/client-documents` -  客户护照和旅行证件

当代理创建巴塞罗那行程时，行为良好的服务器会遵守这些边界 - 访问模板、保存新行程以及引用指定根目录中的客户端文档。服务器通常通过使用根目录中的相对路径或使用尊重根边界的文件搜索工具来访问根目录内的文件。

如果代理打开一个存档文件夹， `file:///Users/agent/archive/2023-trips` 例如 ，客户端将通过 `roots/list_changed` 更新根列表。

有关尊重根的服务器的完整实现，请参阅官方服务器存储库中的[文件系统服务器](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) 。

#### 设计理念

Roots 充当客户端和服务器之间的协调机制，而不是安全边界。该规范要求服务器“应该尊重根边界”，而不是“必须强制执行”它们，因为服务器运行客户端无法控制的代码。

当服务器受到信任或审查，用户了解其咨询性质，并且目标是防止事故而不是阻止恶意行为时，roots 的效果最佳。他们擅长上下文范围界定（告诉服务器关注的位置）、事故预防（帮助行为良好的服务器保持在范围内）和工作流组织（例如自动管理项目边界）。

#### 用户交互模型

Roots 通常由主机应用程序根据用户作自动管理，尽管某些应用程序可能会公开手动根管理：

**自动根检测** ：当用户打开文件夹时，客户端会自动将其公开为根。打开旅行工作区允许客户端将该目录公开为根目录，帮助服务器了解哪些行程和文档在当前工作的范围内。

**手动根配置** ：高级用户可以通过配置指定根。例如，为可重用资源添加 `/travel-templates` ，同时排除具有财务记录的目录。



### Elicitation

Elicitation 使服务器能够在交互中向用户请求特定信息，从而创建更动态且响应灵敏的工作流程。

#### 概述

Elicitation 为服务器提供了一种按需收集必要信息的结构化方式。服务器可以暂停作，以请求用户输入特定输入，而不是一开始就要求所有信息或失败。这创造了更灵活的交互，服务器能够适应用户需求，而非遵循僵化模式。

**Elicitation flow:**

![[Pasted image 20251118105949.png]]


该流程支持动态信息收集。服务器可以在需要时请求特定数据，用户通过适当的界面提供信息，服务器则继续处理新获得的上下文。

**Elicitation components example:**

```
{
  method: "elicitation/requestInput",
  params: {
    message: "Please confirm your Barcelona vacation booking details:",
    schema: {
      type: "object",
      properties: {
        confirmBooking: {
          type: "boolean",
          description: "Confirm the booking (Flights + Hotel = $3,000)"
        },
        seatPreference: {
          type: "string",
          enum: ["window", "aisle", "no preference"],
          description: "Preferred seat type for flights"
        },
        roomType: {
          type: "string",
          enum: ["sea view", "city view", "garden view"],
          description: "Preferred room type at hotel"
        },
        travelInsurance: {
          type: "boolean",
          default: false,
          description: "Add travel insurance ($150)"
        }
      },
      required: ["confirmBooking"]
    }
  }
}
```

#### 示例：假期预订批准

旅行预订服务器通过最终预订确认流程展示了Elicitation的强大功能。当用户选定理想的巴塞罗那度假套餐后，服务器需要收集最终批准和遗漏信息后才能继续。

服务器通过结构化请求触发预订确认，包含行程摘要（巴塞罗那航班6月15日至22日，海滨酒店，总计3000美元）以及其他偏好字段，如座位选择、房间类型或旅游保险选项。

随着预订进行，服务器会获取完成预订所需的联系信息。它可能会要求旅客预订信息、酒店特别请求或紧急联系方式。

#### 用户交互模型

Elicitation互动设计为清晰、情境性强，并尊重用户自主权：

**请求呈现** ：客户端以清晰的上下文显示引发请求，说明是哪台服务器在请求、为何需要这些信息以及如何使用。请求消息解释目的，而模式则提供结构和验证。

**响应选项** ：用户可以通过适当的界面控件（文本字段、下拉选单、复选框）提供所需信息，拒绝提供带有可选解释的信息，或取消整个作。客户端在返回服务器前会根据提供的模式验证响应。

**隐私考虑** ：Elicitation 绝不要求密码或 API 密钥。客户端会警告可疑请求，并允许用户在发送前查看数据。