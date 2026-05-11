// search.js - 簡單的客戶端搜尋
(function() {
    const input = document.getElementById('search-input');
    const results = document.getElementById('search-results');
    if (!input || !results) return;

    let searchData = null;

    fetch('search.json')
        .then(r => r.json())
        .then(d => { searchData = d; })
        .catch(e => console.error('Failed to load search data:', e));

    function normalize(s) {
        return (s || '').toLowerCase().trim();
    }

    function search(q) {
        if (!searchData || !q || q.length < 1) return [];
        const nq = normalize(q);
        return searchData
            .filter(item =>
                normalize(item.name_jp).includes(nq) ||
                normalize(item.name_zhtw).includes(nq) ||
                normalize(item.brewery).includes(nq) ||
                normalize(item.area).includes(nq)
            )
            .slice(0, 20);
    }

    function render(items) {
        if (!items.length) {
            results.hidden = true;
            return;
        }
        results.innerHTML = items.map(item => `
            <a href="${item.url}">
                <strong>${item.name_zhtw || item.name_jp}</strong>
                <div class="search-result-meta">${item.brewery} · ${item.area}</div>
            </a>
        `).join('');
        results.hidden = false;
    }

    let timer;
    input.addEventListener('input', (e) => {
        clearTimeout(timer);
        const q = e.target.value;
        timer = setTimeout(() => {
            render(search(q));
        }, 150);
    });

    // 點擊外面關閉結果
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !results.contains(e.target)) {
            results.hidden = true;
        }
    });

    // Esc 關閉
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            results.hidden = true;
            input.blur();
        }
    });
})();
