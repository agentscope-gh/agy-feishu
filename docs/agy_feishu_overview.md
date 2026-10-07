---
template: sheet
theme: blueprint
title: Antigravity Feishu Bot 全景架构与项目介绍
subtitle: 企业级飞书智能研发助手 · 双向长连接 · 微内核插件系统 · 宿主机引擎闭环
cols: 3
mode: auto
---

## 核心定位与技术底座 {span=1}

```callout ok 项目核心定位
基于飞书原生 WebSocket 与宿主机 agy 核心引擎。面向开发者提供免公网暴露的安全研发协同。
```

```kv cols=1
* 核心引擎: Google Antigravity (agy)
通信架构: 飞书原生 WebSocket 双向长连接 (免公网IP/免内网穿透)
后台守护: PM2 / Docker / WSL / Kubernetes Pod 全平台通用
扩展机制: 微内核解耦插件架构 (Plugin Ecosystem)
持久存储: SQLite WAL 模式高并发本地数据库
权限防护: 多级角色鉴权 (Admin / User / Guest) + 审批流
```

## 系统分层与通信拓扑 {span=2}

```flow LR
(用户端 飞书APP) -> [飞书开放平台网关]: 消息/事件帧
[飞书开放平台网关] -> *[WebSocket Client]: 双向安全长连接
*[WebSocket Client] -> [事件路由器 Dispatcher]
[事件路由器 Dispatcher] -> [Pipeline 串行处理队列] & [卡片回调 Card Actions]
[Pipeline 串行处理队列] -> *[SessionPool 预热池]
*[SessionPool 预热池] -> [(Antigravity agy 引擎)]: 终端/代码执行
[事件路由器 Dispatcher] -> [微内核 Plugin Manager]
[微内核 Plugin Manager] -> [CronEngine 任务调度] & [AI Memory 记忆引擎] & [Server Health 巡检]
[(Antigravity agy 引擎)] -> [CardBuilder 卡片引擎]
[CardBuilder 卡片引擎] -> [Lark REST API]: 异步消息投递
[Lark REST API] --> (用户端 飞书APP): 富文本卡片交互

group 飞书平台层: 飞书开放平台网关, Lark REST API
group 接入与路由层: WebSocket Client, 事件路由器 Dispatcher, Pipeline 串行处理队列
group 核心算力与插件层: SessionPool 预热池, Antigravity agy 引擎, 微内核 Plugin Manager
```

## 消息处理与交互生命周期 {span=2}

```sequence num
participants: 用户, 飞书网关, 接入层, agy引擎, 宿主机环境
用户 -> 飞书网关: 发送自然语言指令 / 斜杠命令
飞书网关 -> 接入层: WebSocket 实时推送 P2IM 消息帧
接入层 -> 接入层: 鉴权校验 & 命令解析
接入层 -> 飞书网关: 立即返回「思考中🤔」动态流转表情
接入层 -> agy引擎: 派发至 SessionPool 预热实例
agy引擎 -> 宿主机环境: 执行本地代码审查 / 终端命令 / 文件操作
宿主机环境 --> agy引擎: 返回实时终端标准输出与状态码
agy引擎 --> 接入层: 汇聚结构化结果并完成上下文更新
接入层 -> 接入层: 自动清理动态表情 & 构建富文本交互卡片
接入层 -> 飞书网关: 通过官方 REST API 异步更新卡片
飞书网关 --> 用户: 最终结果呈现并附带一键交互操作
```

## 核心功能矩阵与模块解耦 {span=1}

| 功能模块 | 对应指令 | 实现机制 | 运行状态 |
| :--- | :--- | :--- | :--- |
| **快捷菜单** | `/menu` | 卡片聚合交互 | ok 场景化一键执行 |
| **会话接管** | `/continue` | 宿主机进程绑定 | ok 跨端继承上下文 |
| **模型热切** | `/model` | 动态多模型调度 | ok 实时切模型免重启 |
| **定时调度** | `/cron` | Standalone 引擎 | ok 支持秒级与熔断 |
| **配额看板** | `/quota` | LSP探针+云端回退 | ok 实时查询 Token 水位 |
| **上线防抖** | 开机自启 | 指数退避静默引擎 | ok 彻底免疫崩溃风暴 |

## 版本演进历程与里程碑 {span=2}

```timeline h
2026-06 | v1.1.0 基础重构 | 纯异步解耦架构，动态 Emoji 状态轮播，PM2 持久化常驻
2026-07 | v1.2.0 工程规范 | 交付生产级 Dockerfile，统一参数解析，代码模块解耦
2026-08 | v2.0.0 微内核架构 | 插件系统完全解耦，引入双向 AI Hook 与全动态指令
2026-09 | v3.0.0 稳定性跃迁 | 定时调度升级 CronEngine v3.0，状态巡检与超时熔断
*2026-10 | v3.1.0 全平台部署 | 全平台自适应安装脚本，开机通知与指数退避防抖，/menu快捷中心
```

## 运行指标与工程特性 {span=1}

```limits
长连接保活率 | 99.9 / 100 | %
卡片生成耗时 | 15 / 50 | ms
进程内存基线 | 195 / 500 | MB
崩溃退避上限 | 1800 / 1800 | s
单测全绿率 | 100 / 100 | %
```

```callout info 架构设计哲学
坚持极简主义与深度工程化。零公网暴露杜绝隐患，双向退避防止雪崩，提供最稳定的本地 AI 生产力。
```
