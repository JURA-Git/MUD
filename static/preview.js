document.addEventListener('DOMContentLoaded', function() {
  const tooltip = document.createElement('div');
  tooltip.style.pointerEvents = 'none';

  tooltip.style.position = 'absolute';
  tooltip.style.padding = '5px';
  tooltip.style.border = '1px solid #aaa';
  tooltip.style.background = '#fff';
  tooltip.style.display = 'none';
  document.body.appendChild(tooltip);

  document.querySelectorAll('.preview').forEach(el => {
    el.addEventListener('mouseover', e => {
      tooltip.textContent = el.dataset.fulltext;
      tooltip.style.left = e.pageX + 'px';
      tooltip.style.top  = e.pageY + 'px';
      tooltip.style.display = 'block';
    });
    el.addEventListener('mousemove', e => {
      tooltip.style.left = e.pageX + 'px';
      tooltip.style.top  = e.pageY + 'px';
    });
    el.addEventListener('mouseout', () => {
      tooltip.style.display = 'none';
    });
  });
});
