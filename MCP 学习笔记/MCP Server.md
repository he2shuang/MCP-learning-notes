MCP 服务器是通过标准化协议接口向 AI 应用展示特定能力的程序。

常见的例子包括用于文档访问的文件系统服务器、用于数据查询的数据库服务器、用于代码管理的 GitHub 服务器、用于团队通信的 Slack 服务器以及用于排程的日历服务器。

# 核心服务器功能

服务器通过三个构建模块提供功能：

| 特征                | 解释                                                               | 例子                                                                | 谁来控制它       |
| ----------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------- | ----------- |
| **Tools  工具**     | 这些函数可以被你的 LLM 主动调用，并根据用户请求决定何时使用。工具可以写入数据库、调用外部 API、修改文件或触发其他逻辑。 | Search flights.<br>Send messages.<br>Create calendar events.      | Model       |
| **Resources  资源** | 被动数据源，提供仅读访问上下文信息，如文件内容、数据库模式或 API 文档。                           | Retrieve documents.<br>Access knowledge bases.<br>Read calendars. | Application |
| **Prompts  提示**   | 预建的指令模板，告诉模型使用特定工具和资源。                                           | Plan a vacation.<br>Summarize my meetings.<br>Draft an email.     | User        |
我们将用一个假设情景来展示这些特征的作用，并展示它们如何协同工作。

## Tools 
#### 工具的工作原理

工具是大语言模型可以调用的模式定义接口。MCP 使用 JSON 模式进行验证。每个工具执行一个作，输入和输出定义清晰。工具可能要求用户在执行前同意，帮助确保用户对模型作保持控制。

**Protocol operations:**

| Method       | Purpose | Returns    |
| ------------ | ------- | ---------- |
| `tools/list` | 发现可用工具  | 带模式的工具定义数组 |
| `tools/call` | 执行特定工具  | 工具执行结果     |

**示例工具定义：**
```
{
  name: "searchFlights",
  description: "Search for available flights",
  inputSchema: {
    type: "object",
    properties: {
      origin: { type: "string", description: "Departure city" },
      destination: { type: "string", description: "Arrival city" },
      date: { type: "string", format: "date", description: "Travel date" }
    },
    required: ["origin", "destination", "date"]
  }
}
```

####  示例：旅行预订

工具使人工智能应用能够代表用户执行作。在旅行规划场景中，人工智能应用可能会使用多种工具帮助预订假期：

**飞行搜索**
```
searchFlights(origin: "NYC", destination: "Barcelona", date: "2024-06-15")
```
查询多家航空公司并返回结构化航班选项。

**Calendar Blocking**
```
createCalendarEvent(title: "Barcelona Trip", startDate: "2024-06-15", endDate: "2024-06-22")
```
在用户日历中标记旅行日期。

**电子邮件通知**
```
sendEmail(to: "team@work.com", subject: "Out of Office", body: "...")
```
向同事发送自动的离职消息。

#### 用户交互模型

工具由模型控制，意味着 AI 模型可以自动发现并调用它们。然而，MCP 强调通过多种机制进行人工监督。

为了信任和安全，应用程序可以通过各种机制实现用户控制，例如：
- 在用户界面中显示可用工具，使用户能够定义该工具是否应在特定交互中开放
- 单个工具执行的审批对话框
- 预先批准某些安全作的权限设置
- 活动日志，显示所有工具执行及其结果

## Resources

资源为 AI 应用提供了结构化的信息访问，这些信息可以检索并作为上下文提供给模型。

#### 资源的工作原理

资源会从文件、API、数据库或 AI 理解上下文所需的其他来源中获取数据。应用程序可以直接访问这些信息并决定如何使用——无论是选择相关部分、用嵌入搜索，还是全部传递给模型。

每个资源都有独特的 URI（例如 `file:///path/to/document.md`），并声明其 MIME 类型以便适当处理内容。

资源支持两种发现模式：

- **直接资源** ——指向特定数据的固定 URI。示例：`calendar://events/2024`——返回 2024 年的日历可用性

- **资源模板** ——带有灵活查询参数的动态 URI。 例：
	- `travel://activities/{city}/{category}` - 按城市和类别统计活动
	- `travel://activities/barcelona/museums` - 返回巴塞罗那所有博物馆

资源模板包含标题、描述和预期 MIME 类型等元数据，使其可被发现并具备自我文档。

**Protocol operations:**

| Method                     | Purpose   | Returns   |
| -------------------------- | --------- | --------- |
| `resources/list`           | 列出可用的直接资源 | 资源描述符数组   |
| `resources/templates/list` | 发现资源模板    | 资源模板定义数组  |
| `resources/read`           | 检索资源内容    | 带元数据的资源数据 |
| `resources/subscribe`      | 监控资源变化    | 订阅确认      |

#### 示例：获取旅行规划背景
继续以旅行规划为例，资源为 AI 应用提供了相关信息的访问权限：
- **日历数据** （`calendar://events/2024`）——检查用户可用性
- **旅行证件** （ `file:///Documents/Travel/passport.pdf` ） - 访问重要文件
- **以往行程** （ `trips://history/barcelona-2023` ）- 参考、以往旅行及偏好
AI 应用程序检索这些资源并决定如何处理，无论是通过嵌入或关键词搜索选择部分数据，还是直接将原始数据传递给模型。

在这种情况下，它向模型提供日历数据、天气信息和出行偏好，使其能够检查可用性、查找天气模式，并参考过往的出行偏好。

**Resource Template Examples:**

```
{
  "uriTemplate": "weather://forecast/{city}/{date}",
  "name": "weather-forecast",
  "title": "Weather Forecast",
  "description": "Get weather forecast for any city and date",
  "mimeType": "application/json"
}

{
  "uriTemplate": "travel://flights/{origin}/{destination}",
  "name": "flight-search",
  "title": "Flight Search",
  "description": "Search available flights between cities",
  "mimeType": "application/json"
}
```

这些模板使查询变得灵活。对于天气数据，用户可以访问任意城市/日期组合的预报。对于航班，用户可以搜索任意两个机场之间的航线。当用户输入“NYC”作为`起飞`机场，开始输入“Bar”作为`目的地`机场时，系统可以建议“Barcelona （BCN）”或“Barbados （BGI）”。

#### 参数补全

动态资源支持参数补全。 例如：
- 输入“Par”作为`输入 weather://forecast/{city}` 可能会提示“Paris”或“Park City”
- 输入“JFK”作为 `flights://search/{airport}` 可能会显示“JFK - 约翰·F·肯尼迪国际”

该系统帮助发现有效数值，无需精确的格式知识。
#### 用户交互模型

资源是应用驱动的，赋予它们在检索、处理和呈现可用上下文的方式上具有灵活性。常见的交互模式包括：
- 用于熟悉文件夹式结构的资源浏览树状或列表视图
- 查找和筛选特定资源的界面
- 基于启发式或 AI 选择的自动上下文包含或智能建议
- 手动或批量选择界面，用于包含单个或多个资源

应用程序可以通过任何符合其需求的接口模式实现资源发现。该协议不强制要求特定的用户界面模式，允许具备预览功能的资源选择器、基于当前对话上下文的智能建议、批量选择以包含多个资源，或与现有文件浏览器和数据浏览器集成。
## Prompts

提示词提供可复用的模板。它们允许 MCP 服务器作者为域提供参数化提示，或展示如何最佳使用 MCP 服务器。

#### 提示工作原理

提示词是定义预期输入和交互模式的结构化模板。它们由用户控制，需要显式调用而非自动触发。提示词可以具备上下文感知功能，引用可用资源和工具，创建全面的工作流程。与资源类似，提示符支持参数补全，帮助用户发现有效的参数值。

**Protocol operations:**

| Method         | Purpose | Returns  返回 |
| -------------- | ------- | ----------- |
| `prompts/list` | 发现可用的提示 | 提示描述符数组     |
| `prompts/get`  | 检索提示详情  | 完整的提示词定义及参数 |

#### 示例：简化工作流程

提示为常见任务提供了结构化的模板。在旅行规划的背景下：

**“Plan a vacation” prompt:**
```
{
  "name": "plan-vacation",
  "title": "Plan a vacation",
  "description": "Guide through vacation planning process",
  "arguments": [
    { "name": "destination", "type": "string", "required": true },
    { "name": "duration", "type": "number", "description": "days" },
    { "name": "budget", "type": "number", "required": false },
    { "name": "interests", "type": "array", "items": { "type": "string" } }
  ]
}
```
提示系统支持以下功能，而非非结构化的自然语言输入：
1. “Plan a vacation”模板的选择
2. 结构化输入：巴塞罗那，7天，3000美元，[“海滩”、“建筑”、“食物”]
3. 基于模板的工作流程执行一致

#### 用户交互模型
提示由用户控制，需要显式调用。该协议赋予实现者设计界面的自由，使其在应用中感觉自然。关键原则包括：
- 轻松发现可用提示
- 清晰描述每个提示的作用
- 带验证的自然论元输入
- 提示词底层模板的透明显示

应用程序通常通过各种 UI 模式来暴露提示，例如：
- 斜杠命令（输入“/”查看可用提示，比如 /plan-vacation）
- 用于搜索访问的命令调色板
- 专门的 UI 按钮用于常用提示
- 提示相关提示的上下文菜单

## 服务器的整合

MCP 的真正优势在于多台服务器协同工作，通过统一接口结合各自的专业能力

#### 示例：多服务器旅行规划

考虑一个个性化的 AI 旅行规划应用，配备三台连接服务器：
- **旅行服务器** ——处理航班、酒店和行程
- **天气服务器** ——提供气候数据和预报
- **日历/邮件服务器** ——管理日程安排和沟通

#### 完整流程

1. **用户调用带有参数的提示：**

```
{
  "prompt": "plan-vacation",
  "arguments": {
    "destination": "Barcelona",
    "departure_date": "2024-06-15",
    "return_date": "2024-06-22",
    "budget": 3000,
    "travelers": 2
  }
}
```

2. **用户选择资源以包括：**
	- `calendar://my-calendar/June-2024` （摘自日历服务器）
	- `travel://preferences/europe`（来自旅游服务器）
	- `travel://past-trips/Spain-2023` （摘自旅行服务器）


3. **AI 通过以下工具处理请求：**
	AI 首先阅读所有选定的资源以获取背景信息——从日历中识别可用日期，从旅行偏好中学习偏好的航空公司和酒店类型，并发现过去旅行中曾经喜欢的地点。
	基于这些上下文，人工智能随后执行一系列工具：
	- `searchFlights（）` - 查询纽约飞往巴塞罗那航班的航空公司
	- `checkWeather（）` - 获取旅行日期的气候预报
	AI 随后利用这些信息创建预订，并按照步骤进行，必要时请求用户批准：
	- `bookHotel（）` - 在指定预算内查找酒店
	- `createCalendarEvent（）` - 将行程添加到用户的日历中
	- `sendEmail（）` - 发送包含行程详情的确认邮件

**结果如下：** 通过多个 MCP 服务器，用户根据自己的日程调研并预订了巴塞罗那的行程。“计划假期”提示引导 AI 将资源（日历可用性和旅行历史）与工具（搜索航班、预订酒店、更新日历）结合到不同服务器——收集上下文并执行预订。原本可能需要数小时的任务，在几分钟内通过 MCP 完成。