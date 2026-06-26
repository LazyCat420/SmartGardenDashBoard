const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const indexHtml = fs.readFileSync(path.resolve(__dirname, '..', 'frontend', 'index.html'), 'utf8');
const appJs = fs.readFileSync(path.resolve(__dirname, '..', 'frontend', 'app.js'), 'utf8');

(async function() {
    // Prevent the real <script src='app.js'> from being loaded by jsdom — we inject the script content manually
    const sanitizedHtml = indexHtml.replace(/<script\s+src="app\.js"\s*><\/script>/i, '');
    const dom = new JSDOM(sanitizedHtml, { runScripts: 'dangerously', resources: 'usable', url: 'http://localhost:5000' });
    const { window } = dom;
    global.window = window; // so scripts that look for global
    global.document = window.document;

    // Stub Chart (basic) to avoid Chart.js errors
    window.Chart = function(ctx, config) {
        this.ctx = ctx;
        this.config = config;
        this.destroy = () => {};
        this.update = () => {};
    };

    // Stub HTML5 QR + others used by app
    window.Html5Qrcode = function() { this.start = () => {}; this.stop = () => {}; };

    // Minimal dataset for /api/plants
    const samplePlants = [
        { id: 'p1', name: 'Tomato', display_name: 'Tomato 1', status: 'active', growth_logs: [{ date: '2025-12-01', height_cm: 12, health_rating: 8 }], waterings: [{ date: '2025-12-06' }] },
        { id: 'p2', name: 'Basil', display_name: 'Basil 1', status: 'active', growth_logs: [{ date: '2025-12-02', height_cm: 4, health_rating: 7 }], waterings: [{ date: '2025-12-05' }, { date: '2025-12-06' }] }
    ];

    // Stub fetch used by the app to avoid network
    window.fetch = async function(url, opts) {
        const uri = url.toString();
        if (uri.includes('/api/plants')) {
            return { ok: true, json: async () => samplePlants };
        }
        if (uri.includes('/api/leaderboard')) {
            return { ok: true, json: async () => ({ rankings: [] }) };
        }
        return { ok: true, json: async () => ({}) };
        };

        // Ensure console logs appear
        window.console = console;

        // Inject app.js into the DOM
        const scriptEl = dom.window.document.createElement('script');
        scriptEl.textContent = appJs;
        dom.window.document.body.appendChild(scriptEl);

        // wait for scripts to initialize and complete any async loading
        await new Promise(res => setTimeout(res, 500));

        // If initApp is available (it may not be called automatically in jsdom when injecting), call it so setup functions attach
        if (typeof dom.window.initApp === 'function') {
            console.log('Calling initApp() to ensure event listeners are attached');
            await dom.window.initApp();
            await new Promise(res => setTimeout(res, 100));
        }

        // Query buttons just like browser
        const gridBtn = dom.window.document.querySelector('.view-btn[data-view="grid"]');
        const tableBtn = dom.window.document.querySelector('.view-btn[data-view="table"]');
        const chartsBtn = dom.window.document.querySelector('.view-btn[data-view="charts"]');

        console.log('Found Grid:', !!gridBtn, 'Table:', !!tableBtn, 'Charts:', !!chartsBtn);
        console.log('gridBtn outerHTML:', gridBtn ? gridBtn.outerHTML : 'none');
        console.log('tableBtn outerHTML:', tableBtn ? tableBtn.outerHTML : 'none');
        console.log('chartsBtn outerHTML:', chartsBtn ? chartsBtn.outerHTML : 'none');

        function inspect() {
            const list = dom.window.document.getElementById('plantsList');
            const table = dom.window.document.getElementById('plantsTable');
            const charts = dom.window.document.getElementById('plantsCharts');
            return {
                listHidden: list.classList.contains('hidden'),
                tableHidden: table.classList.contains('hidden'),
                chartsHidden: charts.classList.contains('hidden')
            };
        }

        console.log('Initial view states:', inspect());
    
        // Simulate table click
        console.log('Click table button');
        tableBtn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }));
        // Also call switchPlantsView directly to see if it works
        if (typeof dom.window.switchPlantsView === 'function') {
            console.log('Calling switchPlantsView("table") directly');
            dom.window.switchPlantsView('table');
        }
        await new Promise(res => setTimeout(res, 50));
        const afterTable = inspect();
        console.log('After table click:', afterTable);
        console.assert(afterTable.listHidden === false && afterTable.tableHidden === false && afterTable.chartsHidden === true, 'Table toggle failed');

        // Simulate charts click
        console.log('Click charts button');
        chartsBtn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }));
        if (typeof dom.window.switchPlantsView === 'function') {
            console.log('Calling switchPlantsView("charts") directly');
            dom.window.switchPlantsView('charts');
        }
        await new Promise(res => setTimeout(res, 50));
        const afterCharts = inspect();
        console.log('After charts click:', afterCharts);
        console.assert(afterCharts.listHidden === false && afterCharts.tableHidden === false && afterCharts.chartsHidden === false, 'Charts toggle failed');

        // Simulate grid click
        console.log('Click grid button');
        gridBtn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }));
        if (typeof dom.window.switchPlantsView === 'function') {
            console.log('Calling switchPlantsView("grid") directly');
            dom.window.switchPlantsView('grid');
        }
        await new Promise(res => setTimeout(res, 50));
        const afterGrid = inspect();
        console.log('After grid click:', afterGrid);
        console.assert(afterGrid.listHidden === true && afterGrid.tableHidden === false && afterGrid.chartsHidden === false, 'Grid toggle failed');

        process.exit(0);
    })();