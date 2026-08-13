package dev.carbonpanel.ui.components

import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.Text as MaterialText
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.TextUnit
import java.util.Locale

/**
 * Single text boundary for the Compose UI.
 *
 * Server-provided names, paths and command output pass through unchanged.
 * Known application copy is translated when Android is using a Chinese locale.
 */
@Composable
fun LocalizedText(
    text: String,
    modifier: Modifier = Modifier,
    color: Color = Color.Unspecified,
    fontSize: TextUnit = TextUnit.Unspecified,
    fontStyle: FontStyle? = null,
    fontWeight: FontWeight? = null,
    fontFamily: FontFamily? = null,
    letterSpacing: TextUnit = TextUnit.Unspecified,
    textDecoration: TextDecoration? = null,
    textAlign: TextAlign? = null,
    lineHeight: TextUnit = TextUnit.Unspecified,
    overflow: TextOverflow = TextOverflow.Clip,
    softWrap: Boolean = true,
    maxLines: Int = Int.MAX_VALUE,
    minLines: Int = 1,
    onTextLayout: ((TextLayoutResult) -> Unit)? = null,
    style: TextStyle = LocalTextStyle.current,
) {
    MaterialText(
        text = localizeUiText(text),
        modifier = modifier,
        color = color,
        fontSize = fontSize,
        fontStyle = fontStyle,
        fontWeight = fontWeight,
        fontFamily = fontFamily,
        letterSpacing = letterSpacing,
        textDecoration = textDecoration,
        textAlign = textAlign,
        lineHeight = lineHeight,
        overflow = overflow,
        softWrap = softWrap,
        maxLines = maxLines,
        minLines = minLines,
        onTextLayout = onTextLayout,
        style = style,
    )
}

fun localizeUiText(text: String): String {
    if (Locale.getDefault().language != "zh") return text
    ZH_TEXT[text]?.let { return it }

    return when {
        text.startsWith("Since ") -> "自 ${text.removePrefix("Since ")}"
        text.startsWith("Up ") -> "运行 ${text.removePrefix("Up ")}"
        text.startsWith("Read ") -> text.replace("Read ", "读取 ").replace(" · write ", " · 写入 ")
        text.startsWith("Also at ") -> "同时挂载于 ${text.removePrefix("Also at ")}"
        text.startsWith("Detected as ") -> "检测为 ${text.removePrefix("Detected as ")}"
        text.startsWith("LABEL PORT ") -> "标记端口 ${text.removePrefix("LABEL PORT ")}"
        text.startsWith("peak ") -> "峰值 ${text.removePrefix("peak ")}"
        text.startsWith("No unit matches ") -> "没有匹配的服务：${text.removePrefix("No unit matches ")}"
        text.endsWith(" accent") -> "${localizeUiText(text.removeSuffix(" accent"))}强调色"
        text.startsWith("Remove ") -> "移除 ${text.removePrefix("Remove ")}"
        text.startsWith("Delete ") -> "删除 ${text.removePrefix("Delete ")}"
        else -> text
    }
}

private val ZH_TEXT = mapOf(
    "Status" to "状态",
    "Services" to "服务",
    "Storage" to "存储",
    "More" to "更多",
    "Sites" to "站点",
    "Ports" to "端口",
    "Processes" to "进程",
    "Shell sessions" to "终端会话",
    "Bookmarks" to "书签",
    "Webhooks" to "Webhook",
    "Update logs" to "更新日志",
    "Settings" to "设置",
    "Site" to "站点",
    "Back" to "返回",
    "Clear" to "清除",
    "Star" to "收藏",
    "Unstar" to "取消收藏",
    "Carbon" to "碳绿",
    "Material You" to "Material You",
    "Emerald" to "祖母绿",
    "Cyan" to "青色",
    "Blue" to "蓝色",
    "Violet" to "紫罗兰",
    "Magenta" to "洋红",
    "Amber" to "琥珀",
    "Crimson" to "绯红",
    "Loading…" to "加载中…",
    "Connecting…" to "连接中…",
    "Cancel" to "取消",
    "Save" to "保存",
    "Saving…" to "保存中…",
    "Add" to "添加",
    "Edit" to "编辑",
    "Delete" to "删除",
    "Remove" to "移除",
    "Start" to "启动",
    "Stop" to "停止",
    "Restart" to "重启",
    "Details" to "详情",
    "Refresh" to "刷新",
    "Refresh now" to "立即刷新",
    "Reconnect" to "重新连接",
    "Test" to "测试",
    "Test all" to "全部测试",
    "Move up" to "上移",
    "Revoke" to "撤销",
    "Enabled" to "已启用",
    "Disabled" to "已禁用",
    "Unknown" to "未知",
    "Unavailable" to "不可用",
    "active" to "活跃",
    "reachable" to "可访问",
    "no reply" to "无响应",
    "Pair this phone with your server" to "将此手机与服务器配对",
    "Open the web panel" to "打开网页面板",
    "On a computer, signed in as admin" to "在电脑上以管理员身份登录",
    "Go to Settings" to "前往设置",
    "Find the Paired Devices section" to "找到“已配对设备”部分",
    "Scan the code" to "扫描二维码",
    "Tap the button below and point your camera" to "点击下方按钮并将相机对准二维码",
    "Contacting server…" to "正在连接服务器…",
    "Camera access is required to scan a pairing code." to "扫描配对二维码需要相机权限。",
    "Open app settings" to "打开应用设置",
    "Scan pairing code" to "扫描配对二维码",
    "Hide manual entry" to "隐藏手动输入",
    "Enter code manually" to "手动输入配对码",
    "Server address" to "服务器地址",
    "Pairing code" to "配对码",
    "Pair" to "配对",
    "For a publicly trusted HTTPS server. Self-signed certificates must be paired by scanning the QR so the certificate pin is included." to
        "适用于具有受信任 HTTPS 证书的服务器。自签名证书必须扫描二维码配对，以包含证书指纹。",
    "No password or 2FA code is typed on this phone. Pairing grants a token you can revoke from the panel at any time." to
        "无需在手机上输入密码或双重验证码。配对会授予一个可随时在面板中撤销的令牌。",
    "No disks reported" to "未报告磁盘",
    "Physical disks" to "物理磁盘",
    "Rescan SMART" to "重新扫描 SMART",
    "Hide" to "隐藏",
    "Show" to "显示",
    "Unmount" to "卸载",
    "Model" to "型号",
    "Temperature" to "温度",
    "Power on" to "通电时间",
    "No active shell sessions" to "没有活跃终端会话",
    "Nobody is logged in over SSH or a local TTY right now." to "当前没有人通过 SSH 或本地终端登录。",
    "Shell sessions" to "终端会话",
    "New bookmark" to "新建书签",
    "Title" to "标题",
    "URL" to "网址",
    "Delete bookmark" to "删除书签",
    "No bookmarks" to "没有书签",
    "New webhook" to "新建 Webhook",
    "Label" to "标签",
    "Events can be configured from the web panel." to "可在网页面板中配置事件。",
    "Delete webhook" to "删除 Webhook",
    "No webhooks" to "没有 Webhook",
    "Webhooks fire when a metric crosses its alert threshold." to "指标越过告警阈值时会触发 Webhook。",
    "No log output" to "没有日志输出",
    "journalctl returned nothing for the update services." to "journalctl 未返回更新服务的日志。",
    "Update service logs" to "更新服务日志",
    "Custom label" to "自定义标签",
    "Leave blank to clear" to "留空以清除",
    "Kill process" to "终止进程",
    "Kill" to "终止",
    "Nothing listening" to "没有监听端口",
    "Listening ports" to "监听端口",
    "No processes" to "没有进程",
    "Top processes" to "进程排行",
    "No sites" to "没有站点",
    "Add sites from the web panel — they can be imported from nginx." to "请从网页面板添加站点，也可以从 nginx 导入。",
    "Type" to "类型",
    "Service" to "服务",
    "Manager" to "管理器",
    "Config" to "配置",
    "Logs" to "日志",
    "Traffic — last hour" to "流量 — 最近一小时",
    "Top paths" to "热门路径",
    "Top clients" to "主要客户端",
    "Everything else" to "其他功能",
    "nginx sites, config and traffic" to "nginx 站点、配置与流量",
    "Scheduled jobs, managed and system" to "计划任务（面板与系统）",
    "What's listening, and on which port" to "查看监听进程与端口",
    "Top processes by CPU or memory" to "按 CPU 或内存查看进程排行",
    "Who's logged in over SSH" to "查看 SSH 登录用户",
    "Your saved links" to "已保存的链接",
    "Alert delivery endpoints" to "告警投递端点",
    "journalctl for the update services" to "更新服务的 journalctl 日志",
    "Server addresses, theme, account" to "服务器地址、主题与账户",
    "Server" to "服务器",
    "Panel" to "面板",
    "Signed in as" to "登录用户",
    "Connected via" to "连接地址",
    "Server addresses" to "服务器地址",
    "Appearance" to "外观",
    "Theme" to "主题",
    "Accent" to "强调色",
    "Material You — colours follow your wallpaper" to "Material You — 颜色跟随壁纸",
    "Panel background" to "面板背景",
    "Use the background image configured on the server" to "使用服务器上配置的背景图片",
    "How often the dashboard polls while it's on screen." to "仪表盘显示时的轮询频率。",
    "Polling stops entirely when the app is in the background." to "应用进入后台后会完全停止轮询。",
    "Home screen widget" to "桌面小组件",
    "Disk ring" to "磁盘环",
    "Open Storage once so the app knows your disks." to "请先打开一次“存储”，让应用获取磁盘列表。",
    "Network interface" to "网络接口",
    "Open Status once so the app knows your interfaces." to "请先打开一次“状态”，让应用获取接口列表。",
    "Throughput unit" to "吞吐量单位",
    "Refresh every" to "刷新间隔",
    "Account" to "账户",
    "Username" to "用户名",
    "Two-factor" to "双重验证",
    "Change your password or 2FA from the web panel." to "请在网页面板中修改密码或双重验证。",
    "Sessions & devices" to "会话与设备",
    "No active sessions." to "没有活跃会话。",
    "Version" to "版本",
    "Installed" to "已安装",
    "Latest" to "最新版本",
    "Checked" to "检查时间",
    "Update in progress…" to "正在更新…",
    "Update available" to "有可用更新",
    "Check for updates" to "检查更新",
    "Installing updates is done from the web panel." to "请在网页面板中安装更新。",
    "This device" to "此设备",
    "Unpair this device" to "取消配对此设备",
    "New job" to "新建任务",
    "Delete job" to "删除任务",
    "No managed jobs" to "没有面板管理的任务",
    "Managed by carbonpanel" to "由 CarbonPanel 管理",
    "System crontab · read-only" to "系统 crontab · 只读",
    "New cron job" to "新建计划任务",
    "Edit job" to "编辑任务",
    "Schedule" to "计划",
    "Command" to "命令",
    "No matches" to "没有匹配项",
    "Nothing to show" to "没有可显示内容",
    "Search units…" to "搜索服务…",
    "Show starred" to "仅显示收藏",
    "Show all" to "显示全部",
    "Timer" to "定时器",
    "Autostart on boot" to "开机自动启动",
    "Not paired with a server" to "尚未与服务器配对",
    "Phone" to "手机",
    "Network" to "网络",
    "No active interfaces" to "没有活跃网络接口",
)
