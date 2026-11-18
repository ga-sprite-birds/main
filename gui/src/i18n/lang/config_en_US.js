/**
 * 配置项 i18n（en_US）。
 *
 * 单一事实来源：ga_birds/Langues/en_US.json 中的 config 块。
 * 修改配置项文案时请先改后端 Langues 文件，再执行同步脚本覆盖本文件：
 *   python scripts/sync_config_i18n.py
 */
export default {
    config: {
        section: {
            language: "Language",
            llm: "LLM",
            tts: "Text-to-Speech",
            chapter: "Chapters",
            output: "Output",
            text_preprocessing: "Text Preprocessing",
            character_analysis: "Character Analysis"
        },
        item: {
            LANGUAGE: "Interface language",
            ENABLE_LLM: "Enable LLM",
            LLM_TEMPERATURE: "LLM temperature",
            LLM_MAX_TOKENS: "Maximum generated tokens",
            LLM_NUM_CTX: "Context window size",
            LLM_TIMEOUT: "LLM timeout (seconds)",
            TTS_ENGINE: "TTS engine",
            TTS_VOICE: "TTS voice",
            TTS_RATE: "Speech rate multiplier",
            TTS_VOLUME: "Volume multiplier",
            TTS_PITCH: "Pitch offset",
            TTS_CHUNK_MAX_CHARS: "Maximum characters per TTS chunk",
            TTS_CHUNK_TIMEOUT: "TTS chunk timeout (seconds)",
            TTS_PROSODY_MODE: "Pause and prosody mode",
            TTS_PROSODY_MAX_UNIT_CHARS: "Maximum characters per prosody unit",
            CHAPTER_INTRO_OUTRO: "Enable chapter intro and outro",
            CHAPTER_LEAD_IN_ENABLED: "Generate lead-in chapter",
            CHAPTER_INTRO_TEMPLATE: "Intro template",
            CHAPTER_OUTRO_TEMPLATE: "Outro template",
            CHAPTER_INTRO_OUTRO_PAUSE: "Intro/outro pause (seconds)",
            CHAPTER_REGEX_PATTERNS: "Chapter recognition regular expressions",
            CHAPTER_MIN_LENGTH: "Minimum chapter length",
            CHAPTER_KEEP_TITLE: "Keep chapter title",
            CHAPTER_NORMALIZE_ENABLED: "Normalize chapter headings",
            OUTPUT_BASE_PATH: "Output root directory",
            OUTPUT_STRATEGY: "Output directory strategy",
            OUTPUT_FORMAT: "Audio format",
            OUTPUT_BITRATE: "Audio bitrate (kbps)",
            OUTPUT_FILENAME_TEMPLATE: "Filename template",
            OUTPUT_FRONT_MATTER_MARKERS: "Front-matter title markers",
            OUTPUT_KEEP_TEMP_FILES: "Keep temporary files",
            OUTPUT_DUPLICATE_HANDLING: "Duplicate file handling",
            OUTPUT_SAVE_CHAPTER_TEXT: "Save chapter text",
            OUTPUT_CHAPTER_TEXT_ENCODING: "Chapter text encoding",
            TEXT_PREPROCESSING_ENABLED: "Enable text preprocessing",
            ENABLE_MULTI_VOICE: "Enable multi-character voice",
            CHARACTER_ANALYSIS_MODE: "Character analysis mode",
            CHARACTER_MAX_CONTENT_LENGTH: "Maximum character-analysis content length",
            DIALOGUE_CHUNK_SIZE: "Dialogue parsing chunk size",
            DIALOGUE_CHUNK_OVERLAP: "Dialogue parsing chunk overlap",
            SEGMENT_ENABLE_LANGUAGE_ANALYSIS: "Enable segment language analysis",
            SEGMENT_ENABLE_EMOTION_ANALYSIS: "Enable segment emotion analysis",
            SEGMENT_MAX_RATE_DELTA: "Maximum segment rate delta",
            SEGMENT_MAX_PITCH_DELTA: "Maximum segment pitch delta",
            SEGMENT_MAX_VOLUME_DELTA: "Maximum segment volume delta",
            VOICE_PREFER_REGION_MATCH: "Prefer region-matched voices"
        },
        desc: {
            TTS_PROSODY_MODE: "Controls text segmentation plus pause and intonation handling. Finer segmentation sounds more natural but needs many more synthesis requests and time.",
            TTS_PROSODY_MAX_UNIT_CHARS: "Maximum characters per speech unit; only used in pause / prosody mode. Over-long sentences are split again at commas and colons.",
            OUTPUT_STRATEGY: "How output sub-folders are organised: by role, by model, or by date.",
            OUTPUT_DUPLICATE_HANDLING: "What to do when the target file already exists.",
            CHARACTER_ANALYSIS_MODE: "How characters are analysed: auto relies on built-in rules, hybrid additionally uses an LLM for dialogue attribution.",
            CHAPTER_LEAD_IN_ENABLED: "When enabled: reuse the file's own front matter (导读/前言) if present; otherwise the LLM writes a lead-in sized to the content and it is emitted as chapter 000."
        },
        option: {
            LANGUAGE: {
                zh_CN: "Simplified Chinese",
                en_US: "English",
                ja_JP: "Japanese"
            },
            TTS_ENGINE: {
                edge: "Edge TTS"
            },
            TTS_PROSODY_MODE: {
                off: "Off",
                off_hint: "One request per paragraph, no extra pauses",
                pause: "Pauses only",
                pause_hint: "Synthesised sentence by sentence with punctuation-based pauses (comma 140ms, period 400ms, ?/! 450ms, ellipsis 700ms, +300ms per paragraph)",
                prosody: "Pauses + tone",
                prosody_hint: "Pauses of \"Pauses only\" plus small tone shifts: slower and higher for questions, faster and louder for exclamations, slower for ellipsis"
            },
            OUTPUT_STRATEGY: {
                by_role: "By role",
                by_role_hint: "One sub-folder per role",
                by_model: "By model",
                by_model_hint: "One sub-folder per model",
                by_date: "By date",
                by_date_hint: "One sub-folder per generation date"
            },
            OUTPUT_FORMAT: {
                mp3: "MP3",
                m4a: "M4A",
                wav: "WAV"
            },
            OUTPUT_DUPLICATE_HANDLING: {
                overwrite: "Overwrite",
                overwrite_hint: "Replace the existing file",
                rename: "Rename",
                rename_hint: "Append a sequence number and keep the old file",
                skip: "Skip",
                skip_hint: "Keep the existing file and generate nothing"
            },
            CHARACTER_ANALYSIS_MODE: {
                auto: "Auto",
                auto_hint: "Built-in rules only, no extra LLM calls",
                hybrid: "Hybrid",
                hybrid_hint: "Rules plus LLM assistance: more accurate, slower, uses tokens"
            }
        },
        error: {
            unknown_key: "Unknown configuration key",
            invalid_section: "Unknown configuration section",
            invalid_value: "Invalid configuration value",
            invalid_type: "Invalid configuration value type",
            out_of_range: "Configuration value is out of range",
            invalid_enum: "Configuration value is not an allowed option",
            invalid_voice: "TTS voice ShortName does not exist",
            invalid_length: "Configuration value length is invalid",
            invalid_path: "Invalid output path",
            invalid_regex: "Invalid chapter regular expression",
            invalid_template: "Template contains unsupported fields or formatting",
            llm_tokens_context: "LLM_MAX_TOKENS must be less than LLM_NUM_CTX",
            dialogue_overlap_size: "DIALOGUE_CHUNK_OVERLAP must be less than DIALOGUE_CHUNK_SIZE",
            invalid_default: "Invalid configuration default in the database",
            missing_default: "Configuration defaults are missing from the database",
            invalid_override_file: "Invalid user configuration override file",
            unknown_schema_type: "Unknown configuration schema type",
            override_write_failed: "Failed to write the user configuration override file",
            voice_preview_failed: "Failed to generate the voice preview. Check your network and try again."
        },
        warning: {
            tts_voices_unavailable: "Edge voices are unavailable; voice configuration was allowed offline",
            tts_voices_stale: "Failed to refresh Edge voices; using the expired cache"
        }
    },
};
