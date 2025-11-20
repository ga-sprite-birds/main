"""
GA Sprite Birds - 配置管理
使用环境变量 + 默认值的简单配置方式

版本: v2.0
开发团队: Tiger
"""

import os
from dotenv import load_dotenv

# 自动加载 .env 文件
load_dotenv()

# ========== LLM 配置 ==========

# ENABLE_LLM：是否启用 LLM 口语化处理
# 作用：控制是否对文本进行 LLM 口语化处理
# 可选值：'true'(启用), 'false'(禁用)
# 影响：禁用后直接使用原文生成音频，跳过 LLM 处理
# 建议：有声书项目建议启用，快速测试可禁用
ENABLE_LLM = os.getenv('ENABLE_LLM', 'true').lower() in ('true', '1', 'yes')

# LLM_MODE：LLM 运行模式
# 作用：选择使用本地模型还是 API 服务
# 可选值：'local'(本地 Ollama), 'api'(OpenAI API)
# 影响：决定使用哪套 LLM 配置
# 建议：本地开发用 local，生产环境可用 api
LLM_MODE = os.getenv('LLM_MODE', 'local')

# LLM_LOCAL_HOST：本地 Ollama 服务地址
# 作用：指定 Ollama 服务的 HTTP 地址
# 格式：http://host:port
# 建议：默认 http://localhost:11434
LLM_LOCAL_HOST = os.getenv('LLM_LOCAL_HOST', 'http://localhost:11434')

# LLM_LOCAL_MODEL：本地 LLM 模型名称
# 作用：指定使用的 Ollama 模型
# 可选值：deepseek-r1:7b, llama2:7b, qwen:7b 等
# 影响：直接影响文本口语化质量和速度
# 建议：中文场景推荐 deepseek-r1:7b
LLM_LOCAL_MODEL = os.getenv('LLM_LOCAL_MODEL', 'deepseek-r1:7b')

# LLM_TEMPERATURE：采样温度
# 作用：控制生成文本的随机性和创造性
# 取值范围：0.0-2.0
# 影响：0.0-0.3(保守), 0.5-0.7(平衡), 0.8-1.0(创造性)
# 建议：口语化场景推荐 0.7
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))

# LLM_MAX_TOKENS：单次生成最大 Token 数
# 作用：限制 LLM 单次输出的最大长度
# 影响：越大输出越详细但耗时增加
# 建议：2000-8192，根据章节长度调整
# 注意：DeepSeek R1 7B 建议不超过 8192
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2000'))

# LLM_NUM_CTX：上下文窗口大小
# 作用：限制模型处理的总上下文长度（输入+输出）
# 影响：越大可处理更长文本但消耗更多资源
# 建议：DeepSeek R1 7B 最大支持 8192
LLM_NUM_CTX = int(os.getenv('LLM_NUM_CTX', '8192'))

# LLM_TIMEOUT：LLM 请求超时时间
# 作用：限制单次 LLM 请求的最大等待时间（秒）
# 影响：超时后会抛出异常，使用原始文本
# 建议：600（10分钟），DeepSeek R1 思考时间较长
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '600'))

# LLM_API_TYPE：API 类型
# 作用：指定 API 服务类型
# 可选值：openai, azure, custom
LLM_API_TYPE = os.getenv('LLM_API_TYPE', 'openai')

# LLM_API_ENDPOINT：API 端点
# 作用：API 服务的 URL 地址
LLM_API_ENDPOINT = os.getenv('LLM_API_ENDPOINT', 'https://api.openai.com/v1')

# LLM_API_KEY：API 密钥
# 作用：访问 API 服务的认证密钥
# 建议：敏感信息，必须在 .env 中配置
LLM_API_KEY = os.getenv('LLM_API_KEY')

# LLM_API_MODEL：API 模型名称
# 作用：指定使用的 API 模型
# 可选值：gpt-4, gpt-3.5-turbo 等
LLM_API_MODEL = os.getenv('LLM_API_MODEL', 'gpt-4')

# LLM_SYSTEM_PROMPT：自定义系统提示词
# 作用：自定义 LLM 的行为指令
# 建议：留空使用默认口语化提示词
LLM_SYSTEM_PROMPT = os.getenv('LLM_SYSTEM_PROMPT', '')

# ========== 模型缓存配置 ==========

# MODEL_CACHE_DIR：模型缓存目录
# 作用：存储下载的模型文件
# 建议：使用默认路径 ./models
MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', './models')

# ========== TTS 配置 ==========

# TTS_MODE：TTS 运行模式
# 作用：选择使用本地模型还是 API 服务
# 可选值：'api'(API 服务), 'local'(本地模型)
# 影响：决定使用哪套 TTS 配置
# 建议：快速测试用 api，高质量用 local
TTS_MODE = os.getenv('TTS_MODE', 'api')

# TTS_ENGINE：TTS 引擎类型
# 作用：指定使用的 TTS 引擎
# 可选值：edge
TTS_ENGINE = os.getenv('TTS_ENGINE', 'edge')

# TTS_VOICE：音色/说话人
# 作用：指定使用的音色或说话人
# 格式：zh-CN-YunxiNeural(男), zh-CN-XiaoxiaoNeural(女) 等
TTS_VOICE = os.getenv('TTS_VOICE', 'zh-CN-YunxiNeural')

# TTS_RATE：语速倍数
# 作用：控制语音播放速度
# 取值范围：0.5-2.0，1.0 为正常速度
# 影响：越大越快，越小越慢
# 建议：0.9-1.2，可通过命令行 --rate 覆盖
# 注意：所有引擎统一使用倍数格式
TTS_RATE = float(os.getenv('TTS_RATE', '1.0'))

# TTS_VOLUME：音量倍数
# 作用：控制音频音量
# 取值范围：0.0-2.0，1.0 为正常音量
# 影响：越大越响，越小越轻
# 建议：0.8-1.2
# 注意：所有引擎统一使用倍数格式
TTS_VOLUME = float(os.getenv('TTS_VOLUME', '1.0'))

# TTS_PITCH：音调偏移
# 作用：控制音频音调高低
# 取值范围：-20 到 +20（Hz）
# 影响：正数提高音调，负数降低音调，0 为正常
# 建议：-10 到 +10
# 注意：所有引擎统一使用 Hz 偏移格式
TTS_PITCH = int(os.getenv('TTS_PITCH', '0'))

# ========== 章节配置 ==========

# CHAPTER_REGEX_PATTERNS：章节识别正则表达式
# 作用：用于识别章节标题的正则模式列表
# 格式：逗号分隔的正则表达式字符串
CHAPTER_REGEX_PATTERNS = os.getenv(
    'CHAPTER_REGEX_PATTERNS',
    '^第[零一二三四五六七八九十百千万0-9]+章,^第[零一二三四五六七八九十百千万0-9]+卷'
).split(',')

# CHAPTER_MIN_LENGTH：最小章节长度
# 作用：过滤掉太短的章节，避免误识别
# 单位：字符数
# 建议：100-200
CHAPTER_MIN_LENGTH = int(os.getenv('CHAPTER_MIN_LENGTH', '100'))

# CHAPTER_KEEP_TITLE：是否保留章节标题
# 作用：控制生成的音频是否包含章节标题
CHAPTER_KEEP_TITLE = os.getenv('CHAPTER_KEEP_TITLE', 'true').lower() == 'true'

# CHAPTER_INTRO_OUTRO：是否启用片头片尾
# 作用：控制是否在章节开头和结尾添加提示语
CHAPTER_INTRO_OUTRO = os.getenv('CHAPTER_INTRO_OUTRO', 'true').lower() == 'true'

# CHAPTER_INTRO_TEMPLATE：片头模板
# 作用：章节开始时的提示语，支持 {index}, {title} 变量
CHAPTER_INTRO_TEMPLATE = os.getenv('CHAPTER_INTRO_TEMPLATE', '第{index}章开始')

# CHAPTER_OUTRO_TEMPLATE：片尾模板
# 作用：章节结束时的提示语
CHAPTER_OUTRO_TEMPLATE = os.getenv('CHAPTER_OUTRO_TEMPLATE', '本章播讲完毕')

# CHAPTER_INTRO_OUTRO_PAUSE：片头片尾停顿时间
# 作用：片头片尾前后的停顿时长
# 实现：通过省略号模拟停顿（每个省略号约 0.3 秒）
# 注意：Edge TTS 不支持 SSML break 标签，所以使用省略号代替
# 单位：秒
# 建议：0.5-2.0
CHAPTER_INTRO_OUTRO_PAUSE = float(os.getenv('CHAPTER_INTRO_OUTRO_PAUSE', '1.0'))

# ========== 文本预处理配置 ==========

# TEXT_PREPROCESSING_ENABLED：是否启用文本预处理
# 作用：控制是否对输入文本进行清洗和规范化
TEXT_PREPROCESSING_ENABLED = os.getenv('TEXT_PREPROCESSING_ENABLED', 'true').lower() == 'true'

# ========== 输出配置 ==========

# OUTPUT_BASE_PATH：输出基础路径
# 作用：音频文件的输出目录
OUTPUT_BASE_PATH = os.getenv('OUTPUT_BASE_PATH', './output')

# OUTPUT_STRATEGY：输出策略
# 作用：控制输出目录的组织方式
# 可选值：by_role(按角色), by_model(按模型), by_date(按日期)
OUTPUT_STRATEGY = os.getenv('OUTPUT_STRATEGY', 'by_role')

# OUTPUT_FORMAT：音频格式
# 作用：输出音频的文件格式
# 可选值：mp3, m4a, wav
OUTPUT_FORMAT = os.getenv('OUTPUT_FORMAT', 'mp3')

# OUTPUT_BITRATE：音频比特率
# 作用：控制音频质量和文件大小
# 单位：kbps
# 建议：128(标准), 192(高质量), 320(极高质量)
OUTPUT_BITRATE = int(os.getenv('OUTPUT_BITRATE', '128'))

# OUTPUT_FILENAME_TEMPLATE：文件名模板
# 作用：控制输出文件的命名格式
# 支持变量：{index}, {title}, {role}, {date}, {format}
OUTPUT_FILENAME_TEMPLATE = os.getenv('OUTPUT_FILENAME_TEMPLATE', '{index:03d}-{title}.{format}')

# OUTPUT_KEEP_TEMP_FILES：保留临时文件
# 作用：是否保留生成过程中的临时文件
OUTPUT_KEEP_TEMP_FILES = os.getenv('OUTPUT_KEEP_TEMP_FILES', 'false').lower() == 'true'

# OUTPUT_DUPLICATE_HANDLING：文件重复处理
# 作用：文件已存在时的处理方式
# 可选值：overwrite(覆盖), rename(重命名), skip(跳过)
OUTPUT_DUPLICATE_HANDLING = os.getenv('OUTPUT_DUPLICATE_HANDLING', 'rename')

# OUTPUT_SAVE_CHAPTER_TEXT：保存章节文本
# 作用：是否保存章节文本用于校稿
OUTPUT_SAVE_CHAPTER_TEXT = os.getenv('OUTPUT_SAVE_CHAPTER_TEXT', 'true').lower() == 'true'

# OUTPUT_CHAPTER_TEXT_ENCODING：章节文本编码
# 作用：保存章节文本时使用的编码
OUTPUT_CHAPTER_TEXT_ENCODING = os.getenv('OUTPUT_CHAPTER_TEXT_ENCODING', 'utf-8')

# ========== 日志配置 ==========

# LOG_LEVEL：日志级别
# 作用：控制日志输出的详细程度
# 可选值：DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# LOG_FORMAT：日志格式
# 作用：定义日志输出的格式
LOG_FORMAT = os.getenv('LOG_FORMAT', '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}')

# LOG_FILE：日志文件路径
# 作用：指定日志文件的保存位置
LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')

# LOG_MAX_FILE_SIZE：日志文件最大大小
# 作用：单个日志文件的最大大小（MB）
LOG_MAX_FILE_SIZE = int(os.getenv('LOG_MAX_FILE_SIZE', '10'))

# LOG_BACKUP_COUNT：日志备份数量
# 作用：保留的日志文件备份数量
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

# LOG_CONSOLE：是否输出到控制台
# 作用：控制是否同时在控制台输出日志
LOG_CONSOLE = os.getenv('LOG_CONSOLE', 'true').lower() == 'true'

# ========== API 服务配置 ==========

# API_HOST：API 服务监听地址
# 作用：指定 FastAPI 服务监听的 IP 地址
# 建议：开发环境用 127.0.0.1，生产环境用 0.0.0.0
API_HOST = os.getenv('API_HOST', '0.0.0.0')

# API_PORT：API 服务端口
# 作用：指定 FastAPI 服务监听的端口
API_PORT = int(os.getenv('API_PORT', '8000'))

# API_DEBUG：调试模式
# 作用：是否启用 FastAPI 调试模式
API_DEBUG = os.getenv('API_DEBUG', 'true').lower() == 'true'

# API_CORS_ENABLED：是否启用 CORS
# 作用：控制是否允许跨域请求
API_CORS_ENABLED = os.getenv('API_CORS_ENABLED', 'true').lower() == 'true'

# API_CORS_ORIGINS：允许的跨域来源
# 作用：指定允许跨域访问的来源列表
# 格式：逗号分隔的 URL 列表，* 表示允许所有来源
API_CORS_ORIGINS = os.getenv('API_CORS_ORIGINS', '*').split(',')

# API_MAX_UPLOAD_SIZE：最大上传文件大小
# 作用：限制上传文件的最大大小（MB）
API_MAX_UPLOAD_SIZE = int(os.getenv('API_MAX_UPLOAD_SIZE', '100'))

# ========== 任务配置 ==========

# TASK_QUEUE_TYPE：任务队列类型
# 作用：指定任务队列的实现方式
# 可选值：memory(内存队列), redis(Redis队列)
# 建议：开发环境用 memory，生产环境用 redis
TASK_QUEUE_TYPE = os.getenv('TASK_QUEUE_TYPE', 'memory')

# TASK_MAX_CONCURRENT：最大并发任务数
# 作用：限制同时执行的任务数量
TASK_MAX_CONCURRENT = int(os.getenv('TASK_MAX_CONCURRENT', '3'))

# TASK_TIMEOUT：任务超时时间
# 作用：单个任务的最大执行时间（秒）
TASK_TIMEOUT = int(os.getenv('TASK_TIMEOUT', '3600'))

# TASK_RESULT_TTL：任务结果保留时间
# 作用：任务结果在系统中保留的时间（秒）
TASK_RESULT_TTL = int(os.getenv('TASK_RESULT_TTL', '86400'))

# ========== Redis 配置 ==========

# REDIS_HOST：Redis 服务器地址
# 作用：指定 Redis 服务器的 IP 地址
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')

# REDIS_PORT：Redis 服务器端口
# 作用：指定 Redis 服务器的端口
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

# REDIS_DB：Redis 数据库编号
# 作用：指定使用的 Redis 数据库编号
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# REDIS_PASSWORD：Redis 密码
# 作用：Redis 服务器的认证密码
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# ========== 角色分析配置 ==========

# ENABLE_MULTI_VOICE：是否启用多角色配音
# 作用：控制是否使用 LLM 分析角色并为每个角色分配不同音色
# 可选值：'true'(启用多角色), 'false'(单一音色)
# 影响：启用后会自动分析角色并分配音色，禁用则使用 TTS_VOICE
# 建议：有声书项目建议启用，快速测试可禁用
# 默认：false（单角色模式）
ENABLE_MULTI_VOICE = os.getenv('ENABLE_MULTI_VOICE', 'false').lower() in ('true', '1', 'yes')

# CHARACTER_ANALYSIS_MODE：角色分析模式
# 作用：控制角色分析的方式
# 可选值：
#   - 'auto'：智能分析模式，LLM 自动发现所有角色
#   - 'hybrid'：混合模式，用户指定角色列表，LLM 分析别名和性格
# 影响：
#   - auto 模式：可能出现重复角色，需要后期合并
#   - hybrid 模式：精度更高，但需要用户提供角色列表
# 建议：首次使用 auto 模式，后续使用 hybrid 模式优化
# 默认：auto
CHARACTER_ANALYSIS_MODE = os.getenv('CHARACTER_ANALYSIS_MODE', 'auto').lower()

# CHARACTER_CACHE_DIR：角色数据缓存目录
# 作用：存储角色分析结果的 JSON 文件
# 建议：使用默认路径 ./cache/role
CHARACTER_CACHE_DIR = os.getenv('CHARACTER_CACHE_DIR', './cache/role')

# CHARACTER_MAX_CONTENT_LENGTH：角色分析最大内容长度
# 作用：限制发送给 LLM 的章节内容长度（字符数）
# 影响：越大分析越准确但耗时增加
# 建议：3000-5000
CHARACTER_MAX_CONTENT_LENGTH = int(os.getenv('CHARACTER_MAX_CONTENT_LENGTH', '3000'))

# PERSONALITY_TAGS：性格标签库
# 作用：预定义的角色性格标签，用于 LLM 分析角色性格时参考
# 用途：未来用于情绪化配音，根据角色性格调整 TTS 参数
PERSONALITY_TAGS = {
    # 性格特征
    "性格": [
        "热血", "冷静", "冲动", "理智", "善良", "邪恶",
        "勇敢", "胆小", "自信", "自卑", "乐观", "悲观",
        "开朗", "内向", "外向", "孤僻", "温柔", "暴躁"
    ],

    # 说话风格
    "说话": [
        "直接", "委婉", "大声", "轻声", "快速", "缓慢",
        "幽默", "严肃", "啰嗦", "简洁", "粗鲁", "礼貌",
        "尖锐", "温和"
    ],

    # 情绪倾向
    "情绪": [
        "激动", "平静", "易怒", "温和", "焦虑", "淡定",
        "热情", "冷漠", "敏感", "迟钝", "多愁善感", "豁达"
    ],

    # 社会角色
    "角色": [
        "长辈", "晚辈", "领导", "下属", "老师", "学生",
        "严父", "慈母", "智者", "愚者", "导师", "学徒"
    ],

    # 其他特征
    "其他": [
        "传统", "现代", "固执", "灵活", "狡猾", "单纯",
        "圆滑", "耿直", "势利", "正直", "慈祥", "严厉",
        "谨慎", "鲁莽", "细心", "粗心"
    ]
}

# ========== FFmpeg 配置 ==========

# FFMPEG_PATH：FFmpeg 可执行文件目录
# 作用：指定 ffmpeg 和 ffprobe 所在的目录路径
# 说明：如果为空，则使用系统 PATH 中的 ffmpeg
# 建议：Windows 用户建议配置此路径，避免环境变量问题
# 示例：F:/soft/ffmpeg/bin
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '')

# ========== 项目配置 ==========

# CORE_DIR：核心模块目录名称
# 作用：指定项目核心模块的目录名称
# 默认值：ga_birds
# 说明：如果您修改了核心目录名称，需要同步修改此配置
CORE_DIR = os.getenv('CORE_DIR', 'ga_birds')
