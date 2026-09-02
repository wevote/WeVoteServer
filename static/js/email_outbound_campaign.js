document.addEventListener('DOMContentLoaded', function() {
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');
  const searchInput = document.getElementById('search');
  const searchClear = document.getElementById('search-clear');

  // Tab switching — search text persists; all tabs are already filtered
  // (see filter() below) so switching just changes which one is visible.
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
    });
  });

  // Search — applied to every tab so each tab's count reflects the filter,
  // not just the one currently visible.
  searchInput.addEventListener('input', function(e) {
    filter(e.target.value.toLowerCase());
  });

  searchClear.addEventListener('click', () => {
    searchInput.value = '';
    filter('');
    searchInput.focus();
  });

  function filter(searchTerm) {
    const searchTerms = searchTerm.split(/\s+/).filter(term => term.length > 0);
    tabContents.forEach(content => {
      content.querySelectorAll('.campaign-row').forEach(row => {
        const name = row.dataset.name || '';
        const isMatch = searchTerms.every(term => name.includes(term));
        row.style.display = isMatch ? '' : 'none';
      });
    });
    updateTabCounts();
  }

  // Show each tab's row count in its label, e.g. "Sent (12)", and keep it
  // in sync with the currently visible (i.e. search-filtered) rows.
  function updateTabCounts() {
    tabButtons.forEach(button => {
      const content = document.querySelector('.tab-content[data-content="' + button.dataset.tab + '"]');
      const countEl = button.querySelector('.tab-count');
      if (!content || !countEl) return;
      const rows = content.querySelectorAll('.campaign-row');
      const visibleCount = Array.from(rows).filter(row => row.style.display !== 'none').length;
      countEl.textContent = '(' + visibleCount + ')';
    });
  }

  updateTabCounts();

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
