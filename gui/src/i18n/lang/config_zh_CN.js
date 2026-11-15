/**
 * 配置项 i18n（zh_CN）。
 *
 * 单一事实来源：ga_birds/Langues/zh_CN.json 中的 config 块。
 * 修改配置项文案时请先改后端 Langues 文件，再执行同步脚本覆盖本文件：
 *   python scripts/sync_config_i18n.py
 */
export default {
    config: {
        section: {
            language: "多语言",
            llm: "LLM 配置",
            tts: "语音合成",
            chapter: "章节配置",
            output: "输出配置",
            text_preprocessing: "文本预处理",
            character_analysis: "角色分析"
        },
        item: {
            LANGUAGE: "界面语言",
            ENABLE_LLM: "启用 LLM",
            LLM_TEMPERATURE: "LLM 温度",
            LLM_MAX_TOKENS: "最大生成 Token 数",
            LLM_NUM_CTX: "上下文窗口大小",
            LLM_TIMEOUT: "LLM 超时时间（秒）",
            TTS_ENGINE: "TTS 引擎",
            TTS_VOICE: "TTS 音色",
            TTS_RATE: "语速倍率",
            TTS_VOLUME: "音量倍率",
            TTS_PITCH: "音高偏移",
            TTS_CHUNK_MAX_CHARS: "单个 TTS 分块最大字符数",
            TTS_CHUNK_TIMEOUT: "TTS 分块超时时间（秒）",
            TTS_PROSODY_MODE: "停顿与语气模式",
            TTS_PROSODY_MAX_UNIT_CHARS: "语气单元最大字符数",
            CHAPTER_INTRO_OUTRO: "启用章节片头片尾",
            CHAPTER_INTRO_TEMPLATE: "片头模板",
            CHAPTER_OUTRO_TEMPLATE: "片尾模板",
            CHAPTER_INTRO_OUTRO_PAUSE: "片头片尾停顿时长（秒）",
            CHAPTER_REGEX_PATTERNS: "章节识别正则表达式",
            CHAPTER_MIN_LENGTH: "章节最小长度",
            CHAPTER_KEEP_TITLE: "保留章节标题",
            CHAPTER_NORMALIZE_ENABLED: "规范化章节标题",
            OUTPUT_BASE_PATH: "输出根目录",
            OUTPUT_STRATEGY: "输出目录策略",
            OUTPUT_FORMAT: "音频格式",
            OUTPUT_BITRATE: "音频码率（kbps）",
            OUTPUT_FILENAME_TEMPLATE: "文件名模板",
            OUTPUT_FRONT_MATTER_MARKERS: "前置内容标题标记",
            OUTPUT_KEEP_TEMP_FILES: "保留临时文件",
            OUTPUT_DUPLICATE_HANDLING: "重复文件处理方式",
            OUTPUT_SAVE_CHAPTER_TEXT: "保存章节文本",
            OUTPUT_CHAPTER_TEXT_ENCODING: "章节文本编码",
            TEXT_PREPROCESSING_ENABLED: "启用文本预处理",
            ENABLE_MULTI_VOICE: "启用多角色配音",
            CHARACTER_ANALYSIS_MODE: "角色分析模式",
            CHARACTER_MAX_CONTENT_LENGTH: "角色分析最大内容长度",
            DIALOGUE_CHUNK_SIZE: "对话解析分块大小",
            DIALOGUE_CHUNK_OVERLAP: "对话解析分块重叠长度",
            SEGMENT_ENABLE_LANGUAGE_ANALYSIS: "启用片段语言分析",
            SEGMENT_ENABLE_EMOTION_ANALYSIS: "启用片段情绪分析",
            SEGMENT_MAX_RATE_DELTA: "片段最大语速偏差",
            SEGMENT_MAX_PITCH_DELTA: "片段最大音高偏差",
            SEGMENT_MAX_VOLUME_DELTA: "片段最大音量偏差",
            VOICE_PREFER_REGION_MATCH: "音色优先匹配地区"
        },
        desc: {
            TTS_PROSODY_MODE: "控制合成的切分粒度与停顿、语调处理。切得越细听感越自然，但合成请求数和总耗时会明显增加。",
            TTS_PROSODY_MAX_UNIT_CHARS: "单个语音单元的最大字符数，只在「仅停顿」「停顿 + 语气」模式下生效；句子过长时会优先在逗号、顿号、冒号处再切分。",
            OUTPUT_STRATEGY: "输出子目录的划分方式：按角色、按模型或按日期建目录。",
            OUTPUT_DUPLICATE_HANDLING: "目标文件已存在时的处理方式。",
            CHARACTER_ANALYSIS_MODE: "角色分析的执行方式：自动按内置规则判断，混合模式额外借助 LLM 识别对白归属。"
        },
        option: {
            LANGUAGE: {
                zh_CN: "简体中文",
                en_US: "English",
                ja_JP: "日本語"
            },
            TTS_ENGINE: {
                edge: "Edge TTS"
            },
            TTS_PROSODY_MODE: {
                off: "关闭",
                off_hint: "整段一次合成，不额外插入停顿",
                pause: "仅停顿",
                pause_hint: "按句子逐句合成，按标点插入停顿（逗号 140ms、句号 400ms、问号/感叹号 450ms、省略号 700ms，段落再加 300ms）",
                prosody: "停顿 + 语气",
                prosody_hint: "在「仅停顿」基础上按句末标点微调语调：疑问句降速升调、感叹句提速升调并加大音量、省略号降速"
            },
            OUTPUT_STRATEGY: {
                by_role: "按角色",
                by_role_hint: "每个角色一个子目录",
                by_model: "按模型",
                by_model_hint: "按所用模型分目录",
                by_date: "按日期",
                by_date_hint: "按生成日期分目录"
            },
            OUTPUT_FORMAT: {
                mp3: "MP3",
                m4a: "M4A",
                wav: "WAV"
            },
            OUTPUT_DUPLICATE_HANDLING: {
                overwrite: "覆盖",
                overwrite_hint: "同名文件直接覆盖",
                rename: "重命名保留",
                rename_hint: "自动追加序号，旧文件保留",
                skip: "跳过",
                skip_hint: "已存在则不生成，复用旧文件"
            },
            CHARACTER_ANALYSIS_MODE: {
                auto: "自动",
                auto_hint: "按内置规则判断，不额外调用 LLM",
                hybrid: "混合",
                hybrid_hint: "规则 + LLM 辅助，更准但更慢、消耗 token"
            }
        },
        error: {
            unknown_key: "未知配置项",
            invalid_section: "未知配置分组",
            invalid_value: "配置值无效",
            invalid_type: "配置值类型无效",
            out_of_range: "配置值超出允许范围",
            invalid_enum: "配置值不在可选范围内",
            invalid_voice: "TTS 音色 ShortName 不存在",
            invalid_length: "配置值长度不足",
            invalid_path: "输出路径无效",
            invalid_regex: "章节正则表达式无效",
            invalid_template: "模板包含不支持的字段或格式",
            llm_tokens_context: "LLM_MAX_TOKENS 必须小于 LLM_NUM_CTX",
            dialogue_overlap_size: "DIALOGUE_CHUNK_OVERLAP 必须小于 DIALOGUE_CHUNK_SIZE",
            invalid_default: "数据库中的配置默认值无效",
            missing_default: "数据库缺少配置默认值",
            invalid_override_file: "用户配置覆盖文件无效",
            unknown_schema_type: "配置 schema 类型未知",
            override_write_failed: "写入用户配置覆盖文件失败",
            voice_preview_failed: "音色试听生成失败，请检查网络后重试"
        },
        warning: {
            tts_voices_unavailable: "无法获取 Edge 音色表，已离线放行音色配置",
            tts_voices_stale: "Edge 音色表获取失败，本次使用过期缓存"
        }
    },
};
