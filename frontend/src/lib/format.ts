export function parseEmotionalText(text: string): string {
  let result = text;
  result = result.replace(/\*(.*?)\*/g, '<em class="text-ember">*$1*</em>');
  result = result.replace(/(""")/g, '<span class="text-pine italic">$1</span>');
  result = result.replace(/\.\.\./g, '<span class="text-slate/50">...</span>');
  return result;
}
