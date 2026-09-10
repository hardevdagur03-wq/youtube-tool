import { useMemo } from 'react';
import { useEditor } from '../../context/EditorContext';

function renderMarkdown(md: string): string {
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const langClass = lang ? `language-${lang}` : '';
    return `<pre class="bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-xl overflow-x-auto my-4 text-sm leading-relaxed"><code class="${langClass}">${code.trim()}</code></pre>`;
  });

  html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 dark:bg-gray-800 text-rose-600 dark:text-rose-400 px-1.5 py-0.5 rounded text-sm">$1</code>');

  html = html.replace(/^######\s+(.+)$/gm, '<h6 class="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-6 mb-2">$1</h6>');
  html = html.replace(/^#####\s+(.+)$/gm, '<h5 class="text-sm font-semibold text-gray-600 dark:text-gray-300 mt-6 mb-2">$1</h5>');
  html = html.replace(/^####\s+(.+)$/gm, '<h4 class="text-base font-bold text-gray-800 dark:text-gray-200 mt-6 mb-2">$1</h4>');
  html = html.replace(/^###\s+(.+)$/gm, '<h3 class="text-lg font-bold text-gray-900 dark:text-white mt-6 mb-2">$1</h3>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2 class="text-xl font-bold text-gray-900 dark:text-white mt-6 mb-2 border-b border-gray-100 dark:border-gray-800 pb-1">$1</h2>');
  html = html.replace(/^#\s+(.+)$/gm, '<h1 class="text-2xl font-bold text-gray-900 dark:text-white mt-6 mb-3">$1</h1>');

  html = html.replace(/^>\s+(.*)$/gm, '<blockquote class="border-l-4 border-gray-300 dark:border-gray-600 pl-4 py-1 my-3 text-gray-600 dark:text-gray-400 italic">$1</blockquote>');

  html = html.replace(/^(\s*[-*+]\s)(.*)$/gm, '<li class="ml-4 list-disc text-gray-700 dark:text-gray-300">$2</li>');
  html = html.replace(/^(\s*\d+\.\s)(.*)$/gm, '<li class="ml-4 list-decimal text-gray-700 dark:text-gray-300">$2</li>');

  html = html.replace(/^---\s*$/gm, '<hr class="my-6 border-gray-200 dark:border-gray-700" />');

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold text-gray-900 dark:text-white">$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong class="font-bold text-gray-900 dark:text-white">$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em class="italic">$1</em>');
  html = html.replace(/_(.+?)_/g, '<em class="italic">$1</em>');
  html = html.replace(/~~(.+?)~~/g, '<del class="line-through text-gray-400">$1</del>');

  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<figure class="my-4"><img src="$2" alt="$1" class="max-w-full rounded-xl shadow-md" loading="lazy" /><figcaption class="text-xs text-gray-400 mt-1 text-center">$1</figcaption></figure>');

  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline font-medium">$1</a>');

  html = html.replace(/^\|(.+)\|$/gm, (match) => {
    const cells = match.slice(1, -1).split('|').map(c => c.trim());
    if (cells.every(c => /^:?-+:?$/.test(c))) return '';
    return '<tr class="border-b border-gray-200 dark:border-gray-700">' + cells.map(c => `<td class="px-3 py-2 text-sm text-gray-700 dark:text-gray-300">${c}</td>`).join('') + '</tr>';
  });

  html = html.replace(/\n\n/g, '</p><p class="text-gray-700 dark:text-gray-300 leading-relaxed my-3">');
  html = html.replace(/^(?!<[houbpltpfdihr]|<li|<tr|<fig|<pre)(.+)$/gm, '$1');

  html = '<div class="prose dark:prose-invert max-w-none">' + html + '</div>';

  html = html.replace(/<p class="text-gray-700 dark:text-gray-300 leading-relaxed my-3"><\/p>/g, '<p class="text-gray-700 dark:text-gray-300 leading-relaxed my-3"><br></p>');

  return html;
}

export default function LivePreview() {
  const { state } = useEditor();

  const html = useMemo(() => renderMarkdown(state.content), [state.content]);

  return (
    <div className="h-full overflow-auto bg-white dark:bg-gray-900 p-6">
      <div
        className="prose-preview max-w-3xl mx-auto"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
