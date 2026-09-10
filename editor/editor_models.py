from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ViewMode(str, Enum):
    EDIT = "edit"
    PREVIEW = "preview"
    SPLIT = "split"
    RICH_TEXT = "rich_text"
    SOURCE = "source"


class EditorEventType(str, Enum):
    DOCUMENT_LOADED = "document_loaded"
    DOCUMENT_CHANGED = "document_changed"
    DOCUMENT_SAVED = "document_saved"
    SELECTION_CHANGED = "selection_changed"
    CURSOR_MOVED = "cursor_moved"
    VIEW_MODE_CHANGED = "view_mode_changed"
    UNDO = "undo"
    REDO = "redo"
    VERSION_CREATED = "version_created"
    VERSION_RESTORED = "version_restored"
    AUTOSAVE_TRIGGERED = "autosave_triggered"
    AUTOSAVE_RECOVERED = "autosave_recovered"
    AI_ACTION_STARTED = "ai_action_started"
    AI_ACTION_COMPLETED = "ai_action_completed"
    AI_ACTION_FAILED = "ai_action_failed"
    TRANSLATION_STARTED = "translation_started"
    TRANSLATION_COMPLETED = "translation_completed"
    FIND_REPLACE_EXECUTED = "find_replace_executed"
    COMMENT_ADDED = "comment_added"
    COMMENT_RESOLVED = "comment_resolved"
    VALIDATION_FAILED = "validation_failed"
    ERROR = "error"


class EditorEvent(BaseModel):
    event_type: EditorEventType
    timestamp: str = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)
    project_id: str = ""


class CursorPosition(BaseModel):
    line: int = 0
    column: int = 0
    offset: int = 0


class ScrollPosition(BaseModel):
    top: float = 0.0
    left: float = 0.0


class SelectionRange(BaseModel):
    start: CursorPosition = Field(default_factory=CursorPosition)
    end: CursorPosition = Field(default_factory=CursorPosition)
    text: str = ""
    collapsed: bool = True


class DocumentModel(BaseModel):
    project_id: str = ""
    title: str = ""
    content: str = ""
    markdown: str = ""
    html: str = ""
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    heading_count: int = 0
    image_count: int = 0
    table_count: int = 0
    code_block_count: int = 0
    blockquote_count: int = 0
    list_count: int = 0
    link_count: int = 0
    reading_time_minutes: int = 0
    speaking_time_minutes: int = 0
    seo_title: str = ""
    meta_description: str = ""
    version: int = 1
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    checksum: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_checksum(self) -> str:
        import hashlib
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:32]

    def update_stats(self) -> None:
        self.word_count = len(self.content.split()) if self.content else 0
        self.character_count = len(self.content)
        self.paragraph_count = self.content.count("\n\n") + 1 if self.content else 0
        self.updated_at = utc_now()
        self.checksum = self.compute_checksum()


class EditorConfig(BaseModel):
    view_mode: ViewMode = ViewMode.SPLIT
    autosave_enabled: bool = True
    autosave_interval_seconds: int = 30
    autosave_on_focus_change: bool = True
    autosave_on_section_completion: bool = False
    autosave_before_close: bool = True
    autosave_on_refresh: bool = True
    version_history_enabled: bool = True
    version_interval_minutes: int = 5
    max_versions: int = 100
    max_history_size: int = 1000
    spellcheck_enabled: bool = True
    line_numbers: bool = True
    word_wrap: bool = True
    tab_size: int = 4
    font_size: int = 14
    font_family: str = "'SF Mono', 'Monaco', 'Consolas', monospace"
    theme: str = "system"
    show_heading_navigator: bool = True
    show_statistics: bool = True
    show_minimap: bool = False
    ai_suggestions_enabled: bool = True
    language: str = "en"


class EditorState(BaseModel):
    project_id: str = ""
    document: DocumentModel = Field(default_factory=DocumentModel)
    config: EditorConfig = Field(default_factory=EditorConfig)
    cursor: CursorPosition = Field(default_factory=CursorPosition)
    selection: SelectionRange = Field(default_factory=SelectionRange)
    scroll: ScrollPosition = Field(default_factory=ScrollPosition)
    is_dirty: bool = False
    is_saving: bool = False
    is_loading: bool = False
    last_saved_at: str = ""
    last_cursor_at: str = ""
    active_ai_action: str = ""
    active_translation: str = ""
    view_mode: ViewMode = ViewMode.SPLIT
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentStats(BaseModel):
    word_count: int = 0
    character_count: int = 0
    character_count_no_spaces: int = 0
    paragraph_count: int = 0
    sentence_count: int = 0
    heading_count: int = 0
    image_count: int = 0
    table_count: int = 0
    code_block_count: int = 0
    blockquote_count: int = 0
    list_count: int = 0
    link_count: int = 0
    reading_time_minutes: int = 0
    speaking_time_minutes: int = 0
    seo_score: float = 0.0
    readability_score: float = 0.0
    vocabulary_richness: float = 0.0
    avg_word_length: float = 0.0
    avg_sentence_length: float = 0.0
    flesch_reading_ease: float = 0.0
    syllable_count: int = 0
    difficult_word_count: int = 0


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult(BaseModel):
    severity: ValidationSeverity = ValidationSeverity.INFO
    message: str = ""
    line: int = 0
    column: int = 0
    rule: str = ""
    suggestion: str = ""


class CommentStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUGGESTION = "suggestion"


class Comment(BaseModel):
    comment_id: str = ""
    author: str = ""
    text: str = ""
    status: CommentStatus = CommentStatus.ACTIVE
    selection: SelectionRange = Field(default_factory=SelectionRange)
    created_at: str = Field(default_factory=utc_now)
    resolved_at: str = ""
    resolved_by: str = ""
    replies: list[Comment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HeadingInfo(BaseModel):
    text: str = ""
    tag: str = "h2"
    level: int = 2
    line: int = 0
    anchor_id: str = ""
    children: list[HeadingInfo] = Field(default_factory=list)


class TableOfContentsEntry(BaseModel):
    title: str = ""
    anchor_id: str = ""
    level: int = 2
    line: int = 0
    children: list[TableOfContentsEntry] = Field(default_factory=list)


class FindReplaceRequest(BaseModel):
    query: str = ""
    replacement: str = ""
    use_regex: bool = False
    case_sensitive: bool = False
    whole_word: bool = False
    scope: str = "document"


class FindReplaceMatch(BaseModel):
    line: int = 0
    column: int = 0
    start_offset: int = 0
    end_offset: int = 0
    text: str = ""
    context_before: str = ""
    context_after: str = ""


class FindReplaceResult(BaseModel):
    matches: list[FindReplaceMatch] = Field(default_factory=list)
    total_matches: int = 0
    replacements_made: int = 0
    replaced_text: str = ""
    error: str = ""


class FormattingCommand(str, Enum):
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    HIGHLIGHT = "highlight"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    HEADING_4 = "heading_4"
    BULLET_LIST = "bullet_list"
    ORDERED_LIST = "ordered_list"
    TASK_LIST = "task_list"
    BLOCKQUOTE = "blockquote"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    LINK = "link"
    IMAGE = "image"
    TABLE = "table"
    HORIZONTAL_RULE = "horizontal_rule"
    ALIGN_LEFT = "align_left"
    ALIGN_CENTER = "align_center"
    ALIGN_RIGHT = "align_right"
    UNDO = "undo"
    REDO = "redo"


class AIActionType(str, Enum):
    REWRITE = "rewrite"
    EXPAND = "expand"
    SIMPLIFY = "simplify"
    SHORTEN = "shorten"
    IMPROVE_TONE = "improve_tone"
    FIX_GRAMMAR = "fix_grammar"
    IMPROVE_SEO = "improve_seo"
    IMPROVE_READABILITY = "improve_readability"
    IMPROVE_CLARITY = "improve_clarity"
    CONTINUE_WRITING = "continue_writing"
    SUMMARIZE = "summarize"
    GENERATE_EXAMPLES = "generate_examples"
    EXPLAIN = "explain"
    TRANSLATE = "translate"
    CUSTOM = "custom"


class AIActionRequest(BaseModel):
    action_type: AIActionType = AIActionType.REWRITE
    text: str = ""
    context: str = ""
    instructions: str = ""
    tone: str = "professional"
    language: str = "en"
    temperature: float = 0.7
    max_tokens: int = 2048


class AIActionResponse(BaseModel):
    success: bool = False
    action_type: AIActionType = AIActionType.REWRITE
    original_text: str = ""
    modified_text: str = ""
    diff: str = ""
    suggestions: list[str] = Field(default_factory=list)
    explanation: str = ""
    error: str = ""
    processing_time_ms: float = 0.0
    tokens_used: int = 0


class TranslationRequest(BaseModel):
    text: str = ""
    source_language: str = "en"
    target_language: str = "es"
    preserve_formatting: bool = True
    scope: str = "selection"


class TranslationResponse(BaseModel):
    success: bool = False
    original_text: str = ""
    translated_text: str = ""
    source_language: str = ""
    target_language: str = ""
    detection_confidence: float = 0.0
    processing_time_ms: float = 0.0
    error: str = ""


class VersionInfo(BaseModel):
    version_number: int = 1
    label: str = ""
    created_at: str = Field(default_factory=utc_now)
    author: str = ""
    reason: str = ""
    checksum: str = ""
    word_count: int = 0
    character_count: int = 0
    is_automatic: bool = False
    is_checkpoint: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class VersionMetadata(BaseModel):
    project_id: str = ""
    versions: list[VersionInfo] = Field(default_factory=list)
    current_version: int = 1
    total_versions: int = 0
    last_version_at: str = ""


class DiffType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class DiffLine(BaseModel):
    type: DiffType = DiffType.UNCHANGED
    content: str = ""
    old_line_number: int = 0
    new_line_number: int = 0


class VersionDiff(BaseModel):
    old_version: int = 0
    new_version: int = 1
    old_content: str = ""
    new_content: str = ""
    lines: list[DiffLine] = Field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    modified_lines: int = 0
    unchanged_lines: int = 0
    change_percentage: float = 0.0


class AutosaveState(BaseModel):
    project_id: str = ""
    content: str = ""
    cursor: CursorPosition = Field(default_factory=CursorPosition)
    scroll: ScrollPosition = Field(default_factory=ScrollPosition)
    selection: SelectionRange = Field(default_factory=SelectionRange)
    view_mode: str = "split"
    saved_at: str = Field(default_factory=utc_now)
    checksum: str = ""
    is_recovery_point: bool = False


class AutosaveConfig(BaseModel):
    enabled: bool = True
    interval_seconds: int = 30
    on_focus_change: bool = True
    on_section_completion: bool = False
    before_close: bool = True
    on_refresh: bool = True
    max_recovery_points: int = 50
    recovery_ttl_hours: int = 168


class RecoveryPoint(BaseModel):
    point_id: str = ""
    timestamp: str = Field(default_factory=utc_now)
    content: str = ""
    cursor: CursorPosition = Field(default_factory=CursorPosition)
    scroll: ScrollPosition = Field(default_factory=ScrollPosition)
    reason: str = ""
    checksum: str = ""


class HistoryEntry(BaseModel):
    entry_id: str = ""
    timestamp: str = Field(default_factory=utc_now)
    action: str = ""
    previous_content: str = ""
    new_content: str = ""
    cursor_before: CursorPosition = Field(default_factory=CursorPosition)
    cursor_after: CursorPosition = Field(default_factory=CursorPosition)
    selection_before: SelectionRange = Field(default_factory=SelectionRange)
    selection_after: SelectionRange = Field(default_factory=SelectionRange)
    description: str = ""
    action_type: str = "edit"


class HistoryAction(BaseModel):
    entry_id: str = ""
    timestamp: str = Field(default_factory=utc_now)
    description: str = ""
    content_before: str = ""
    content_after: str = ""
    cursor_before: CursorPosition = Field(default_factory=CursorPosition)
    cursor_after: CursorPosition = Field(default_factory=CursorPosition)
    action_type: str = "edit"


class FormatChange(BaseModel):
    format_type: str = ""
    start_offset: int = 0
    end_offset: int = 0
    old_value: str = ""
    new_value: str = ""


class TableChange(BaseModel):
    row: int = 0
    column: int = 0
    old_value: str = ""
    new_value: str = ""


class ImageChange(BaseModel):
    image_url: str = ""
    old_alt: str = ""
    new_alt: str = ""
    action: str = "added"
