const CATEGORY_LABELS = {
    length: 'Длина',
    mass: 'Масса',
    volume: 'Объём',
    temperature: 'Температура',
};

const categoriesEl = document.getElementById('categories');
const fromEl = document.getElementById('from-unit');
const toEl = document.getElementById('to-unit');
const valueEl = document.getElementById('value');
const precisionEl = document.getElementById('precision');
const precisionLabel = document.getElementById('precision-label');
const resultEl = document.getElementById('result-value');
const resultUnitEl = document.getElementById('result-unit');
const convertBtn = document.getElementById('convert-btn');
const historyEl = document.getElementById('history');
const clearBtn = document.getElementById('clear-history');

let currentCategory = null;

async function api(path, opts) {
    const res = await fetch(path, opts);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
    }
    return res.json();
}

function fillSelect(select, items, getValue, getLabel) {
    select.innerHTML = '';
    for (const item of items) {
        const opt = document.createElement('option');
        opt.value = getValue(item);
        opt.textContent = getLabel(item);
        select.appendChild(opt);
    }
}

async function loadCategories() {
    const data = await api('/api/ucalc/categories');
    categoriesEl.innerHTML = '';
    for (const cat of data.categories) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.dataset.category = cat;
        btn.textContent = CATEGORY_LABELS[cat] || cat;
        btn.addEventListener('click', () => selectCategory(cat));
        categoriesEl.appendChild(btn);
    }
    if (data.categories.length > 0) {
        selectCategory(data.categories[0]);
    }
}

async function selectCategory(cat) {
    currentCategory = cat;
    for (const btn of categoriesEl.children) {
        btn.classList.toggle('active', btn.dataset.category === cat);
    }
    await loadUnits();
    await recalc();
}

async function loadUnits() {
    const data = await api(`/api/ucalc/units?category=${encodeURIComponent(currentCategory)}`);
    fillSelect(fromEl, data.units, u => u.code, u => `${u.name} (${u.code})`);
    fillSelect(toEl, data.units, u => u.code, u => `${u.name} (${u.code})`);
    if (data.units.length > 1) toEl.selectedIndex = 1;
}

async function recalc(save = false) {
    if (!currentCategory || !fromEl.value || !toEl.value) return;
    const payload = {
        category: currentCategory,
        from_code: fromEl.value,
        to_code: toEl.value,
        value: parseFloat(valueEl.value) || 0,
        precision: parseInt(precisionEl.value, 10),
        save: save,
    };
    try {
        const data = await api('/api/ucalc/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        resultEl.textContent = data.result.toFixed(data.precision);
        resultUnitEl.textContent = toEl.value;
        if (save) await loadHistory();
    } catch (e) {
        resultEl.textContent = 'ошибка';
        resultUnitEl.textContent = '';
        console.error(e);
    }
}

async function loadHistory() {
    const data = await api('/api/ucalc/history');
    historyEl.innerHTML = '';
    for (const h of data.history) {
        const li = document.createElement('li');
        const left = document.createElement('span');
        left.textContent =
            `${h.input_value} ${h.from_code} → ` +
            `${h.result_value.toFixed(h.precision)} ${h.to_code}`;
        const when = document.createElement('span');
        when.className = 'when';
        when.textContent = h.created_at.replace('T', ' ');
        li.appendChild(left);
        li.appendChild(when);
        historyEl.appendChild(li);
    }
}

precisionEl.addEventListener('input', () => {
    precisionLabel.textContent = precisionEl.value;
    recalc();
});

valueEl.addEventListener('input', () => recalc());
fromEl.addEventListener('change', () => recalc());
toEl.addEventListener('change', () => recalc());
convertBtn.addEventListener('click', () => recalc(true));

clearBtn.addEventListener('click', async () => {
    await api('/api/ucalc/history', { method: 'DELETE' });
    await loadHistory();
});

(async function init() {
    await loadCategories();
    await loadHistory();
})();