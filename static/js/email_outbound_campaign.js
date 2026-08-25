document.addEventListener('DOMContentLoaded', function() {
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');
  const searchInput = document.getElementById('search');

  // Tab switching — search text persists, filter re-applied to new tab
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetTab = button.dataset.tab;

      tabButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');

      tabContents.forEach(content => {
        if (content.dataset.content === targetTab) {
          content.classList.add('active');
        } else {
          content.classList.remove('active');
        }
      });

      // Re-apply current search to the newly visible tab
      filter(searchInput.value.toLowerCase());
    });
  });

  // Search — scoped to opened tab only
  searchInput.addEventListener('input', function(e) {
    filter(e.target.value.toLowerCase());
  });

  function filter(searchTerm) {
    const activeTab = document.querySelector('.tab-content.active');
    if (!activeTab) return;
    const searchTerms = searchTerm.split(/\s+/).filter(term => term.length > 0);
    activeTab.querySelectorAll('.campaign-row').forEach(row => {
      const name = row.dataset.name || '';
      const isMatch = searchTerms.length === 0 || searchTerms.some(term => name.includes(term));
      row.style.display = isMatch ? '' : 'none';
    });
  }

  // Dropdown (kebab menu on each row)
  document.querySelectorAll('.js-dd').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const wrap = btn.closest('.wv-dropdown');
      document.querySelectorAll('.wv-dropdown').forEach(d => {
        if (d !== wrap) d.classList.remove('open');
      });
      wrap.classList.toggle('open');
    });
  });

  document.addEventListener('click', () => {
    document.querySelectorAll('.wv-dropdown').forEach(d => d.classList.remove('open'));
  });
});
