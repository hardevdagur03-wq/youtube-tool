import type {
  AIActionRequest, AIActionResponse, DocumentStats,
  FindReplaceRequest, FindReplaceResult, HeadingInfo,
  TranslationRequest, TranslationResponse, ValidationResult,
  VersionDiff, VersionInfo,
} from '../types/editor';

const API_BASE = '/api/editor';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let errorMsg = `Server returned ${res.status}`;
    try { const body = await res.json(); errorMsg = body?.error || body?.message || errorMsg; } catch { const text = await res.text().catch(() => ''); errorMsg = text || errorMsg; }
    throw new Error(errorMsg);
  }
  const data = await res.json();
  if (!data.success && data.error) {
    throw new Error(data.error);
  }
  return data as T;
}

export const EditorAPI = {
  load(projectId: string) {
    return request<{
      project_id: string;
      content: string;
      title: string;
      statistics: DocumentStats;
      seo_score: number;
      headings: HeadingInfo[];
      versions: VersionInfo[];
    }>(`${API_BASE}/${projectId}`);
  },

  save(projectId: string, content: string, title?: string) {
    return request<{ success: boolean; saved_at: string }>(
      `${API_BASE}/${projectId}/save`,
      { method: 'POST', body: JSON.stringify({ content, title }) }
    );
  },

  getContent(projectId: string) {
    return request<{ content: string }>(`${API_BASE}/${projectId}/content`);
  },

  setContent(projectId: string, content: string) {
    return request<{ success: boolean }>(
      `${API_BASE}/${projectId}/content`,
      { method: 'POST', body: JSON.stringify({ content }) }
    );
  },

  getStats(projectId: string) {
    return request<{ statistics: DocumentStats; seo_score: number }>(
      `${API_BASE}/${projectId}/stats`
    );
  },

  validate(projectId: string) {
    return request<{ validations: ValidationResult[] }>(
      `${API_BASE}/${projectId}/validate`
    );
  },

  undo(projectId: string) {
    return request<{ content: string; can_undo: boolean; can_redo: boolean }>(
      `${API_BASE}/${projectId}/undo`,
      { method: 'POST' }
    );
  },

  redo(projectId: string) {
    return request<{ content: string; can_undo: boolean; can_redo: boolean }>(
      `${API_BASE}/${projectId}/redo`,
      { method: 'POST' }
    );
  },

  createVersion(projectId: string, label?: string, reason?: string) {
    return request<{ version: VersionInfo }>(
      `${API_BASE}/${projectId}/version`,
      { method: 'POST', body: JSON.stringify({ label, reason }) }
    );
  },

  getVersions(projectId: string) {
    return request<{ versions: VersionInfo[] }>(
      `${API_BASE}/${projectId}/versions`
    );
  },

  getVersionContent(projectId: string, versionNumber: number) {
    return request<{ content: string }>(
      `${API_BASE}/${projectId}/versions/${versionNumber}`
    );
  },

  getDiff(projectId: string, oldVersion: number, newVersion: number) {
    return request<{ diff: VersionDiff }>(
      `${API_BASE}/${projectId}/diff?old=${oldVersion}&new=${newVersion}`
    );
  },

  restoreVersion(projectId: string, versionNumber: number) {
    return request<{ content: string }>(
      `${API_BASE}/${projectId}/restore/${versionNumber}`,
      { method: 'POST' }
    );
  },

  find(projectId: string, req: FindReplaceRequest) {
    return request<{ result: FindReplaceResult }>(
      `${API_BASE}/${projectId}/find`,
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  replace(projectId: string, req: FindReplaceRequest) {
    return request<{ result: FindReplaceResult }>(
      `${API_BASE}/${projectId}/replace`,
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  executeAI(projectId: string, req: AIActionRequest) {
    return request<{ result: AIActionResponse }>(
      `${API_BASE}/${projectId}/ai`,
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  translate(projectId: string, req: TranslationRequest) {
    return request<{ result: TranslationResponse }>(
      `${API_BASE}/${projectId}/translate`,
      { method: 'POST', body: JSON.stringify(req) }
    );
  },

  getHeadings(projectId: string) {
    return request<{ headings: HeadingInfo[] }>(
      `${API_BASE}/${projectId}/headings`
    );
  },

  checkAutosave(projectId: string) {
    return request<{ has_recovery: boolean; content: string }>(
      `${API_BASE}/${projectId}/autosave`
    );
  },

  clearAutosave(projectId: string) {
    return request<{ success: boolean }>(
      `${API_BASE}/${projectId}/autosave/clear`,
      { method: 'POST' }
    );
  },

  getLanguages() {
    return request<{ languages: { code: string; name: string }[] }>(
      `${API_BASE}/supported-languages`
    );
  },
};

