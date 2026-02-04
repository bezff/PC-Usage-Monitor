let isRunning = false;
let updateInterval = null;

const colors = ['#6366f1', '#22c55e', '#eab308', '#f97316', '#ef4444', '#a855f7', '#06b6d4', '#ec4899'];

Chart.defaults.color = '#71717a';
Chart.defaults.borderColor = '#2a2a32';

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    updateClock();
    setInterval(updateClock, 1000);
    
    checkStatus();
    loadOverviewData();
    checkAutostart();
    
    document.querySelectorAll('input[name="period"]').forEach(radio => {
        radio.addEventListener('change', loadAppsData);
    });
});

function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
            
            if (tab.dataset.tab === 'apps') loadAppsData();
            if (tab.dataset.tab === 'stats') loadStatsData();
        });
    });
}

function updateClock() {
    const now = new Date();
    document.getElementById('currentTime').textContent = now.toLocaleTimeString('ru-RU');
}

async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        isRunning = data.running;
        updateUI(data);
        
        if (isRunning && !updateInterval) {
            updateInterval = setInterval(fetchStatus, 1000);
        }
    } catch (e) {
        console.error(e);
    }
}

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        updateUI(data);
    } catch (e) {
        console.error(e);
    }
}

function updateUI(data) {
    const btn = document.getElementById('toggleBtn');
    const badge = document.getElementById('statusBadge');
    
    if (data.running) {
        btn.textContent = '⏹ Остановить';
        btn.classList.add('stop');
        badge.textContent = 'Активен';
        badge.classList.add('active');
    } else {
        btn.textContent = '▶ Начать';
        btn.classList.remove('stop');
        badge.textContent = 'Остановлен';
        badge.classList.remove('active');
    }
    
    document.getElementById('totalTime').textContent = data.total_time_fmt || '0с';
    document.getElementById('activeTime').textContent = data.active_time_fmt || '0с';
    document.getElementById('idleTime').textContent = data.idle_time_fmt || '0с';
    document.getElementById('appsCount').textContent = data.apps_count || 0;
    
    const appText = data.current_app || '—';
    document.getElementById('currentApp').textContent = data.is_idle ? `${appText} (простой)` : appText;
    
    const total = data.total_time || 1;
    const active = data.active_time || 0;
    const productivity = Math.round((active / total) * 100);
    
    document.getElementById('productivityValue').textContent = productivity + '%';
    drawProductivityRing(productivity);
}

async function toggleMonitoring() {
    const endpoint = isRunning ? '/api/stop' : '/api/start';
    
    try {
        await fetch(endpoint, { method: 'POST' });
        isRunning = !isRunning;
        
        if (isRunning) {
            updateInterval = setInterval(fetchStatus, 1000);
        } else {
            clearInterval(updateInterval);
            updateInterval = null;
        }
        
        checkStatus();
    } catch (e) {
        console.error(e);
    }
}

function drawProductivityRing(percent) {
    const canvas = document.getElementById('productivityRing');
    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 55;
    const lineWidth = 12;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#2a2a32';
    ctx.lineWidth = lineWidth;
    ctx.stroke();
    
    const color = percent >= 70 ? '#22c55e' : percent >= 40 ? '#eab308' : '#ef4444';
    const endAngle = (percent / 100) * 2 * Math.PI - Math.PI / 2;
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
}

async function loadOverviewData() {
    await loadHourlyChart();
    await loadTopApps();
}

async function loadHourlyChart() {
    try {
        const res = await fetch('/api/hourly');
        const data = await res.json();
        
        const labels = data.map(d => d.hour.toString().padStart(2, '0'));
        const values = data.map(d => Math.round(d.seconds / 60));
        
        const ctx = document.getElementById('hourlyChart').getContext('2d');
        
        if (window.hourlyChartInstance) {
            window.hourlyChartInstance.destroy();
        }
        
        window.hourlyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: values.map(v => {
                        const max = Math.max(...values) || 1;
                        const intensity = v / max;
                        if (intensity > 0.7) return '#22c55e';
                        if (intensity > 0.3) return '#6366f1';
                        return '#2a2a32';
                    }),
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'мин' }
                    }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadTopApps() {
    try {
        const res = await fetch('/api/apps?limit=5');
        const data = await res.json();
        
        const container = document.getElementById('topAppsList');
        container.innerHTML = '';
        
        if (!data.length) {
            container.innerHTML = '<p style="color: var(--text-muted)">Нет данных</p>';
            return;
        }
        
        data.forEach((app, i) => {
            container.innerHTML += `
                <div class="app-item">
                    <span class="app-rank">${i + 1}.</span>
                    <span class="app-name">${app.name}</span>
                    <span class="app-time">${app.duration_fmt}</span>
                    <span class="app-percent">${app.percent}%</span>
                    <span class="app-category">${app.category_name}</span>
                </div>
            `;
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadAppsData() {
    const period = document.querySelector('input[name="period"]:checked').value;
    
    try {
        const [appsRes, catsRes] = await Promise.all([
            fetch(`/api/apps?period=${period}&limit=20`),
            fetch(`/api/categories?period=${period}`)
        ]);
        
        const apps = await appsRes.json();
        const categories = await catsRes.json();
        
        const container = document.getElementById('fullAppsList');
        container.innerHTML = '';
        
        if (!apps.length) {
            container.innerHTML = '<p style="color: var(--text-muted)">Нет данных за выбранный период</p>';
        } else {
            apps.forEach((app, i) => {
                container.innerHTML += `
                    <div class="app-item">
                        <span class="app-rank">${i + 1}.</span>
                        <span class="app-name">${app.name}</span>
                        <span class="app-time">${app.duration_fmt}</span>
                        <span class="app-percent">${app.percent}%</span>
                        <span class="app-category">${app.category_name}</span>
                    </div>
                `;
            });
        }
        
        drawCategoriesChart(categories);
    } catch (e) {
        console.error(e);
    }
}

function drawCategoriesChart(categories) {
    const ctx = document.getElementById('categoriesChart').getContext('2d');
    
    if (window.categoriesChartInstance) {
        window.categoriesChartInstance.destroy();
    }
    
    if (!categories.length) {
        return;
    }
    
    window.categoriesChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: categories.map(c => c.name),
            datasets: [{
                data: categories.map(c => c.seconds),
                backgroundColor: colors.slice(0, categories.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            cutout: '60%'
        }
    });
    
    const legend = document.getElementById('categoriesLegend');
    legend.innerHTML = '';
    
    categories.forEach((cat, i) => {
        legend.innerHTML += `
            <div class="legend-item">
                <span class="legend-color" style="background: ${colors[i % colors.length]}"></span>
                <span>${cat.name}: ${cat.formatted}</span>
            </div>
        `;
    });
}

async function loadStatsData() {
    await Promise.all([
        loadWeekComparison(),
        loadTrendChart(),
        loadWeekSummary()
    ]);
}

async function loadWeekComparison() {
    try {
        const res = await fetch('/api/week-comparison');
        const data = await res.json();
        
        const ctx = document.getElementById('weekComparisonChart').getContext('2d');
        
        if (window.weekComparisonInstance) {
            window.weekComparisonInstance.destroy();
        }
        
        window.weekComparisonInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.day),
                datasets: [{
                    label: 'Часы активности',
                    data: data.map(d => d.hours),
                    backgroundColor: '#6366f1',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'часы' }
                    }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadTrendChart() {
    try {
        const res = await fetch('/api/trend');
        const data = await res.json();
        
        const ctx = document.getElementById('trendChart').getContext('2d');
        
        if (window.trendInstance) {
            window.trendInstance.destroy();
        }
        
        window.trendInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date.slice(5)),
                datasets: [{
                    label: 'Продуктивность %',
                    data: data.map(d => d.productivity),
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointBackgroundColor: '#6366f1'
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: '%' }
                    }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadWeekSummary() {
    try {
        const res = await fetch('/api/stats/week');
        const data = await res.json();
        
        const formatTime = (sec) => {
            if (sec < 60) return sec + 'с';
            if (sec < 3600) return Math.floor(sec / 60) + 'м';
            const h = Math.floor(sec / 3600);
            const m = Math.floor((sec % 3600) / 60);
            return `${h}ч ${m}м`;
        };
        
        const container = document.getElementById('weekSummary');
        container.innerHTML = `
            <div class="summary-item">
                <span class="summary-label">Период</span>
                <span class="summary-value">${data.period}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Общее время</span>
                <span class="summary-value">${formatTime(data.total_seconds)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Активное время</span>
                <span class="summary-value">${formatTime(data.active_seconds)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Среднее в день</span>
                <span class="summary-value">${formatTime(data.avg_daily)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Дней с данными</span>
                <span class="summary-value">${data.days_count}</span>
            </div>
        `;
    } catch (e) {
        console.error(e);
    }
}

async function checkAutostart() {
    try {
        const res = await fetch('/api/autostart');
        const data = await res.json();
        
        const toggle = document.getElementById('autostartToggle');
        const status = document.getElementById('autostartStatus');
        
        toggle.checked = data.enabled;
        status.textContent = data.enabled ? 'Включён' : 'Выключен';
        status.className = data.enabled ? 'status-on' : 'status-off';
    } catch (e) {
        console.error(e);
    }
}

async function toggleAutostart() {
    const toggle = document.getElementById('autostartToggle');
    const status = document.getElementById('autostartStatus');
    const endpoint = toggle.checked ? '/api/autostart/enable' : '/api/autostart/disable';
    
    status.textContent = 'Сохранение...';
    
    try {
        const res = await fetch(endpoint, { method: 'POST' });
        const data = await res.json();
        
        if (toggle.checked && data.enabled) {
            status.textContent = 'Включён';
            status.className = 'status-on';
        } else if (!toggle.checked && data.disabled) {
            status.textContent = 'Выключен';
            status.className = 'status-off';
        } else {
            toggle.checked = !toggle.checked;
            status.textContent = 'Ошибка';
        }
    } catch (e) {
        console.error(e);
        toggle.checked = !toggle.checked;
        status.textContent = 'Ошибка';
    }
}
