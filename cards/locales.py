"""Centralized localized strings and copywriting for Feishu interactive cards.

All user-facing copy, headers, action labels, and phase descriptions are
consolidated here for maintainability, high information density, and future i18n.
"""

APP_NAME = "Antigravity"
BRAND_FOOTER_PREFIX = "⚡ Powered by Antigravity"

# ----------------------------------------------------------------------
# 1. Dynamic Indicators & Thinking Phases
# ----------------------------------------------------------------------
INTENT_MODES = {
    "code": {
        "title": "💻 代码工程",
        "description": "正在分析代码上下文并构建工程方案..."
    },
    "search": {
        "title": "🔍 数据检索",
        "description": "正在跨域检索并归纳线索..."
    },
    "translate": {
        "title": "🌐 语言翻译",
        "description": "正在进行多语言精准转换..."
    },
    "summary": {
        "title": "📝 总结提炼",
        "description": "正在提炼核心要点与关键信息..."
    },
    "choice": {
        "title": "🎯 选项执行",
        "description": "已接收选项，正在执行相应操作..."
    },
    "voice": {
        "title": "🎙️ 语音合成",
        "description": "正在组织内容并合成语音输出..."
    },
    "default": {
        "title": "⚙️ 任务处理中",
        "description": "正在解析上下文并组织回复..."
    }
}

DYNAMIC_THINKING_PHRASES = [
    "正在深度分析上下文与逻辑依赖...",
    "正在检索项目结构与环境线索...",
    "正在规划多步骤行动路径...",
    "正在校验执行产物与数据结构...",
    "正在组织生成最终结构化回复..."
]

TOOL_ACTION_VERBS = [
    (r'^(?:Connecting to|Connect to|Connecting|Connect)\s+', '连接 '),
    (r'^(?:Downloading from|Downloading|Download)\s+', '下载 '),
    (r'^(?:Checking|Verifying|Validating|Check|Verify|Validate)\s+', '检查 '),
    (r'^(?:Inspecting|Analyzing|Inspect|Analyze)\s+', '分析 '),
    (r'^(?:Creating|Generating|Create|Generate)\s+', '生成 '),
    (r'^(?:Writing to|Writing|Write)\s+', '写入 '),
    (r'^(?:Executing|Running|Execute|Run)\s+', '执行 '),
    (r'^(?:Listing|Browsing|List|Browse)\s+', '查看 '),
    (r'^(?:Searching for|Searching|Grepping|Search|Grep|Find)\s+', '搜索 '),
    (r'^(?:Reading|Viewing|Read|View)\s+', '读取 '),
    (r'^(?:Editing|Modifying|Edit|Modify)\s+', '编辑 '),
    (r'^(?:Querying|Query)\s+', '查询 '),
    (r'^(?:Aggregating|Aggregate)\s+', '汇总 '),
    (r'^(?:Fetching|Fetch)\s+', '获取 '),
    (r'^(?:Uploading|Upload)\s+', '上传 '),
    (r'^(?:Sending|Send)\s+', '发送 '),
    (r'^(?:Formatting|Format)\s+', '整理 '),
]

COMMON_CLI_ACTIONS = [
    ("python", "执行 Python 脚本"),
    ("sqlite3", "查询本地数据库"),
    ("docker", "查询容器状态"),
    ("git", "执行 Git 操作"),
    ("grep", "检索代码内容"),
    ("ripgrep", "检索代码内容"),
    ("curl", "请求网络资源"),
    ("wget", "请求网络资源"),
]

# ----------------------------------------------------------------------
# 2. Stall & Timeout Governance
# ----------------------------------------------------------------------
STALL_WARNING = {
    "title": "⏱️ 深度推理等待中",
    "extend_button": "🟢 继续等待",
    "stop_button": "🛑 中止任务",
    "desc_template": "当前任务已持续运行 **{think_seconds} 秒**（静默等待 **{wait_desc}**）。\n\n*底层正在进行深度推理、复杂任务规划或多工具检索，守护进程正常，已自动延长超时时限。*"
}

STALL_ERROR = {
    "title": "⚠️ 任务无响应已终止",
    "desc_template": "任务已连续 **{stall_minutes} 分钟** 无任何计算、Token 或日志产出，已判定超时并安全终止。\n\n**建议操作**：",
    "retry_button": "🔄 重新发送请求",
    "switch_model_button": "⚙️ 切换快速模型",
    "clear_button": "🧹 清空上下文"
}

# ----------------------------------------------------------------------
# 3. System Welcome, Help & Status
# ----------------------------------------------------------------------
SYSTEM_WELCOME = {
    "title": "🎉 Antigravity 服务已上线",
    "content": (
        "您好，**Antigravity 智能开发助理** 已成功部署并与当前飞书会话绑定。\n\n"
        "**核心功能支持**：\n"
        "• **本地工作区操作**：受控读写项目代码、执行终端脚本与构建调试\n"
        "• **多模态文件解析**：原生支持 PDF、Word、代码、音视频与图片输入\n"
        "• **网络与知识检索**：支持跨网信息查询与网页内容结构化提炼\n\n"
        "点击下方常用功能或直接发送指令开始协作："
    ),
    "btn_project": "📁 工作区项目",
    "btn_model": "🤖 切换模型",
    "btn_help": "💡 查看帮助",
    "btn_clear": "🧹 清空上下文"
}

SYSTEM_SECURITY_BLOCKED = {
    "title": "⚠️ 安全策略拦截",
    "template": "🚨 **高风险系统命令已被安全策略拦截**\n\n检测到输入包含系统破坏性或高风险特征，已对该请求进行阻断截断。\n\n**特征指令**：\n> `{blocked_command}`\n\n*(如确有维护管理需求，请登录受控终端手动执行。)*"
}

# ----------------------------------------------------------------------
# 4. Auth & RBAC
# ----------------------------------------------------------------------
AUTH_STRINGS = {
    "unauthorized_title": "🔒 当前会话未授权",
    "unauthorized_content": "当前飞书会话尚未获得本服务的使用授权。\n\n如需使用，请发送 **`/auth`** 向管理员申请授权。",
    "admin_welcome_title": "👑 管理员权限已绑定",
    "admin_welcome_content": (
        "首次部署绑定成功，本会话已自动确认为**最高管理员**。\n\n"
        "• 其他会话发送的 `/auth` 申请将在此处接收审批卡片\n"
        "• 使用 **`/user`** 查看与管理授权会话\n"
        "• 本会话不受常规权限与限流限制"
    ),
    "tiers": {
        "basic": "基础权限",
        "dev": "开发权限",
        "full": "完全权限"
    },
    "tier_descriptions": {
        "basic": "对话、文档与图片解析、笔记与偏好",
        "dev": "基础权限 + 项目切换、代码读写与文件回传",
        "full": "开发权限 + 终端 Shell 执行、查看配额与系统运维"
    }
}

# ----------------------------------------------------------------------
# 5. Scheduled Tasks (Cron)
# ----------------------------------------------------------------------
CRON_STRINGS = {
    "panel_title": "⏱️ 计划任务管理中心 (Cron Center)",
    "tab_user": "👤 用户任务",
    "tab_system": "⚙️ 系统任务",
    "btn_create": "➕ 新建任务",
    "badge_reminder": "💬【消息提醒】",
    "badge_shell": "🖥️【Shell脚本】",
    "badge_ai_agent": "🧠【AI巡检】",
    "badge_webhook": "🌐【Webhook通知】"
}
