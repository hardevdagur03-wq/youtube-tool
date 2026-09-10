import { describe, it, expect, beforeEach } from 'vitest';
import { transcriptService } from '../services/TranscriptService';
import { getLanguageLabel } from '../types';

describe('TranscriptService', () => {
  beforeEach(() => {
    transcriptService.clearCache();
  });

  it('should clear cache', () => {
    transcriptService.clearCache();
    const trans = transcriptService.getCachedTranslation('test1234567', 'hi');
    expect(trans).toBeUndefined();
  });

  it('should have empty cache initially', () => {
    const trans = transcriptService.getCachedTranslation('test1234567', 'hi');
    expect(trans).toBeUndefined();
  });
});

describe('getLanguageLabel', () => {
  it('should return English for en', () => {
    expect(getLanguageLabel('en')).toBe('English');
  });

  it('should return Hindi for hi', () => {
    expect(getLanguageLabel('hi')).toBe('Hindi');
  });

  it('should return Spanish for es', () => {
    expect(getLanguageLabel('es')).toBe('Spanish');
  });

  it('should return French for fr', () => {
    expect(getLanguageLabel('fr')).toBe('French');
  });

  it('should return German for de', () => {
    expect(getLanguageLabel('de')).toBe('German');
  });

  it('should uppercase unknown codes', () => {
    expect(getLanguageLabel('xyz')).toBe('XYZ');
  });

  it('should support dynamically added languages via uppercase fallback', () => {
    expect(getLanguageLabel('sw')).toBe('SW');
  });
});
