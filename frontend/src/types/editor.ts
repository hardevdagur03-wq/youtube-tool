export type ViewMode = 'edit' | 'preview' | 'split' | 'rich_text' | 'source';

export interface CursorPosition {
  line: number;
  column: number;
  offset: number;
}

export interface ScrollPosition {
  top: number;
  left: number;
}

export interface SelectionRange {
  start: CursorPosition;
  end: CursorPosition;
  text: string;
  collapsed: boolean;
}

export interface DocumentModel {
  project_id: string;
  title: string;
  content: string;
  markdown: string;
  html: string;
  word_count: number;
  character_count: number;
  paragraph_count: number;
  heading_count: number;
  image_count: number;
  table_count: number;
  code_block_count: number;
  blockquote_count: number;
  list_count: number;
  link_count: number;
  reading_time_minutes: number;
  speaking_time_minutes: number;
  seo_title: string;
  meta_description: string;
  version: number;
  created_at: string;
  updated_at: string;
  checksum: string;
}

export interface EditorState {
  project_id: string;
  document: DocumentModel;
  cursor: CursorPosition;
  selection: SelectionRange;
  scroll: ScrollPosition;
  is_dirty: boolean;
  is_saving: boolean;
  is_loading: boolean;
  last_saved_at: string;
  view_mode: ViewMode;
  errors: string[];
  warnings: string[];
}

export interface DocumentStats {
  word_count: number;
  character_count: number;
  character_count_no_spaces: number;
  paragraph_count: number;
  sentence_count: number;
  heading_count: number;
  image_count: number;
  table_count: number;
  code_block_count: number;
  blockquote_count: number;
  list_count: number;
  link_count: number;
  reading_time_minutes: number;
  speaking_time_minutes: number;
  seo_score: number;
  readability_score: number;
  vocabulary_richness: number;
  avg_word_length: number;
  avg_sentence_length: number;
  flesch_reading_ease: number;
  syllable_count: number;
  difficult_word_count: number;
}

export interface HeadingInfo {
  text: string;
  tag: string;
  level: number;
  line: number;
  anchor_id: string;
  children?: HeadingInfo[];
}

export interface VersionInfo {
  version_number: number;
  label: string;
  created_at: string;
  author: string;
  reason: string;
  checksum: string;
  word_count: number;
  character_count: number;
  is_automatic: boolean;
  is_checkpoint: boolean;
}

export interface DiffLine {
  type: 'added' | 'removed' | 'modified' | 'unchanged';
  content: string;
  old_line_number: number;
  new_line_number: number;
}

export interface VersionDiff {
  old_version: number;
  new_version: number;
  old_content: string;
  new_content: string;
  lines: DiffLine[];
  added_lines: number;
  removed_lines: number;
  modified_lines: number;
  unchanged_lines: number;
  change_percentage: number;
}

export type AIActionType =
  | 'rewrite' | 'expand' | 'simplify' | 'shorten'
  | 'improve_tone' | 'fix_grammar' | 'improve_seo'
  | 'improve_readability' | 'improve_clarity'
  | 'continue_writing' | 'summarize'
  | 'generate_examples' | 'explain' | 'translate';

export interface AIActionRequest {
  action_type: AIActionType;
  text: string;
  context?: string;
  instructions?: string;
  tone?: string;
  language?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface AIActionResponse {
  success: boolean;
  action_type: AIActionType;
  original_text: string;
  modified_text: string;
  diff: string;
  suggestions: string[];
  explanation: string;
  error: string;
  processing_time_ms: number;
  tokens_used: number;
}

export interface TranslationRequest {
  text: string;
  source_language: string;
  target_language: string;
  preserve_formatting: boolean;
  scope: 'selection' | 'document';
}

export interface TranslationResponse {
  success: boolean;
  original_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  detection_confidence: number;
  processing_time_ms: number;
  error: string;
}

export interface FindReplaceRequest {
  query: string;
  replacement: string;
  use_regex: boolean;
  case_sensitive: boolean;
  whole_word: boolean;
  scope: string;
}

export interface FindReplaceMatch {
  line: number;
  column: number;
  start_offset: number;
  end_offset: number;
  text: string;
  context_before: string;
  context_after: string;
}

export interface FindReplaceResult {
  matches: FindReplaceMatch[];
  total_matches: number;
  replacements_made: number;
  replaced_text: string;
  error: string;
}

export interface ValidationResult {
  severity: 'error' | 'warning' | 'info';
  message: string;
  line: number;
  column: number;
  rule: string;
  suggestion: string;
}

export type FormattingCommand =
  | 'bold' | 'italic' | 'underline' | 'strikethrough'
  | 'highlight' | 'heading_1' | 'heading_2' | 'heading_3'
  | 'heading_4' | 'bullet_list' | 'ordered_list' | 'task_list'
  | 'blockquote' | 'code_block' | 'inline_code' | 'link'
  | 'image' | 'table' | 'horizontal_rule'
  | 'align_left' | 'align_center' | 'align_right'
  | 'undo' | 'redo';
