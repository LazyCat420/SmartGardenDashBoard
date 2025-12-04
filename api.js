const API_BASE_URL = 'http://localhost:5000/api';

async function loadBackendData() {
    try {
        console.log('Fetching data from backend...');
        const [plantsRes, productsRes, recipesRes, appsRes, journalRes] = await Promise.all([
            fetch(`${API_BASE_URL}/plants`),
            fetch(`${API_BASE_URL}/products`),
            fetch(`${API_BASE_URL}/recipes`),
            fetch(`${API_BASE_URL}/applications`),
            fetch(`${API_BASE_URL}/journal`)
        ]);
        if (!plantsRes.ok) throw new Error('Failed to fetch plants');
        if (!journalRes.ok) console.warn('Warning: failed to fetch journal');
        
        const plants = await plantsRes.json();
        const products = await productsRes.json();
        const recipes = await recipesRes.json();
        const apps = await appsRes.json();
        const journal = await journalRes.json();
        
        // Update appState
        appState.plants = plants;
        
        // Ensure we have a garden structure (since DB only has plants for now)
        if (appState.gardens.length === 0) {
             appState.gardens.push({
                id: 'garden_1',
                name: 'Home Garden',
                grids: [{ id: 'grid_1', name: 'Front Yard', prefix: 'A', rows: 3, cols: 3 }],
                plants: [] 
            });
        }
        
        // Link plants to the garden
        appState.gardens[0].plants = appState.plants;
        appState.currentGardenId = 'garden_1';
        // Populate products, recipes, applications and journal
        appState.products = products || [];
        appState.feedingRecipes = recipes || [];
        appState.feedingApplications = apps || [];
        // Parse amounts in feeding_applications
        appState.feedingApplications.forEach(a => { if (typeof a.amount === 'string') { try { a.amount = JSON.parse(a.amount); } catch (e) { } } });
        // Populate journal
        if (!appState.journal) appState.journal = [];
        appState.journal.length = 0;
        journal.forEach(j => {
                try {
                    if (typeof j.tags === 'string') j.tags = JSON.parse(j.tags);
                } catch (e) { j.tags = j.tags || []; }
            try {
                if (typeof j.relatedPlantIds === 'string') j.relatedPlantIds = JSON.parse(j.relatedPlantIds);
            } catch (e) { j.relatedPlantIds = j.relatedPlantIds || []; }
                try {
                    if (typeof j.processed_data === 'string') j.processed_data = JSON.parse(j.processed_data);
                } catch (e) { j.processed_data = j.processed_data || null; }
            appState.journal.push(j);
        });
        
        console.log('Backend data loaded:', plants.length, 'plants');
        
        // Mark that backend data is loaded
        appState.__backendLoaded = true;
        
        // Re-render the UI components that depend on data
        renderPlants();
        updateStats();
        updateDashboard();
        
    } catch (error) {
        console.error('Error loading backend data:', error);
        // Fallback to sample data if backend fails? 
        // For now, let's just log it.
    }
}

// Override the savePlant function to persist to backend
const originalSavePlant = window.savePlant;
window.savePlant = async function() {
    const id = document.getElementById('plant-id').value;
    const name = document.getElementById('plant-name').value;
    const type = document.getElementById('plant-type').value;
    const gridId = document.getElementById('plant-grid').value;
    const quadrant = document.getElementById('plant-quadrant').value;
    const dateAdded = document.getElementById('plant-date').value;
    const health = document.getElementById('plant-health').value;
    
    // Find existing plant to preserve arrays if editing
    const existingPlant = appState.plants.find(p => p.id === id) || {};
    
    const plantData = {
        name, type, gridId, quadrant, dateAdded, health,
        gardenId: appState.currentGardenId,
        // Preserve existing data or default to empty
        heightHistory: existingPlant.heightHistory || [],
        healthHistory: existingPlant.healthHistory || [],
        photos: existingPlant.photos || [],
        feedingRecipes: existingPlant.feedingRecipes || [],
        feedingApplications: existingPlant.feedingApplications || [],
        journalEntries: existingPlant.journalEntries || []
    };

    try {
        let response;
        if (id) {
            response = await fetch(`${API_BASE_URL}/plants/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(plantData)
            });
        } else {
            response = await fetch(`${API_BASE_URL}/plants`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(plantData)
            });
        }

        if (response.ok) {
            // Reload data to ensure UI is in sync with DB
            await loadBackendData();
            closePlantModal();
            // showToast is defined in index.html
            if (typeof showToast === 'function') showToast('Plant saved successfully');
        } else {
            console.error('Server returned error');
            if (typeof showToast === 'function') showToast('Error saving plant', true);
        }
    } catch (error) {
        console.error('Error saving plant:', error);
        if (typeof showToast === 'function') showToast('Error saving plant', true);
    }
};

// Override initialization
// We hook into the window load or just run this if the script is loaded at the end
// But since initApp is called at the end of index.html, we need to be careful.
// If we load this script AFTER index.html's main script, we can overwrite initApp.

// However, index.html calls initApp() immediately at the bottom.
// So we should probably just call loadBackendData() immediately if appState is available.

// Wait for DOMContentLoaded then attempt to load backend data (after main init ran)
document.addEventListener('DOMContentLoaded', () => {
    if (typeof appState !== 'undefined') {
        // Disable the sample data initialization for future calls (if any)
        window.initializeSampleData = function() {
            // Check if backend data is already loaded
            if (appState.__backendLoaded) {
                console.log('Backend data already loaded, skipping sample data initialization.');
                return;
            }
            console.log('Using backend data instead of sample data.');
            if (appState.gardens.length === 0) {
                appState.gardens = [{
                    id: 'garden_1',
                    name: 'Home Garden',
                    grids: [{ id: 'grid_1', name: 'Front Yard', prefix: 'A', rows: 3, cols: 3 }],
                    plants: []
                }];
                appState.currentGardenId = 'garden_1';
            }
        };
    }
    // Defer the load slightly to allow init to complete and UI elements to mount
    setTimeout(() => {
        loadBackendData();
    }, 50);
});

// Smart Process button handler
async function processSmartEntry() {
    const text = document.getElementById('journal-textarea').value.trim();
    if (!text) {
        if (typeof showToast === 'function') showToast('Please enter some notes first', true);
        return;
    }
    try {
        const payload = { date: new Date().toISOString().split('T')[0], content: text, processWithAI: true };
        const res = await fetch(`${API_BASE_URL}/journal`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        if (res.ok) {
            const result = await res.json();
            // Build detailed success message
            let msg = '✨ Journal processed!';
            const created = result.createdPlants || [];
            const linked = result.relatedPlantIds || [];
            if (created.length > 0) {
                msg += ` Created ${created.length} new plant(s).`;
            }
            if (linked.length > 0) {
                msg += ` Updated ${linked.length} plant(s).`;
            }
            if (typeof showToast === 'function') showToast(msg);
            document.getElementById('journal-textarea').value = '';
            await loadBackendData();
            renderJournal();
            renderPlants();
        } else {
            const err = await res.json();
            if (typeof showToast === 'function') showToast('Error: ' + (err.error || 'Unknown error'), true);
        }
    } catch (error) {
        console.error('Error processing journal:', error);
        if (typeof showToast === 'function') showToast('Error connecting to backend', true);
    }
}

// Attach event listener if button exists
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('smart-process-btn');
    if (btn) btn.addEventListener('click', processSmartEntry);
});
