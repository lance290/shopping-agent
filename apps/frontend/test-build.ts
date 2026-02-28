const content = `
## The Cost-Benefit Thresholds

Evaluating private aviation options requires mapping your principal's exact flight profile against three distinct models. Making the wrong choice here can easily result in a six-figure annual inefficiency.

![Cabin Interior](https://images.unsplash.com/photo-1543226998-320c242f2b38?auto=format&fit=crop&w=1200&q=80)

### 1. On-Demand Charter (Under 25 hours/year)
`;

const parsedContent = content
  .split('\n\n')
  .map(block => {
    block = block.trim();
    if (!block) return '';
    if (block.startsWith('![')) {
      const altMatch = block.match(/!\[(.*?)\]/);
      const urlMatch = block.match(/\((.*?)\)/);
      if (altMatch && urlMatch) {
        return `<figure class="my-10"><img src="${urlMatch[1]}" alt="${altMatch[1]}" class="w-full rounded-2xl border border-white/10" /><figcaption class="text-center text-xs text-onyx-muted mt-3">${altMatch[1]}</figcaption></figure>`;
      }
    }
    return block;
  })
  .join('');
console.log(parsedContent);
