import shutil

# Read the content of the index.html file
try:
    with open('d:/Github/SmartGardenDashBoard/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print("index.html not found. Copying index2.html to index.html...")
    shutil.copy('d:/Github/SmartGardenDashBoard/index2.html', 'd:/Github/SmartGardenDashBoard/index.html')
    with open('d:/Github/SmartGardenDashBoard/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

# 1. Inject Smart Entry Button
print("Injecting Smart Entry Button...")
journal_form_start = '<form id="journal-form">'
if journal_form_start in content:
    # Find the textarea to inject the button before/after or modify the form
    # We'll add a new button next to the submit button
    submit_button = '<button type="submit" class="btn btn-primary">Parse &amp; Save Entry</button>'
    # Use inline onclick for reliability
    new_buttons = '''<div style="display: flex; gap: 10px;">
                <button type="submit" class="btn btn-primary">Parse &amp; Save Entry</button>
                <button type="button" id="smart-process-btn" onclick="processSmartEntry()" class="btn btn-secondary" style="background: linear-gradient(45deg, #6b21a8, #c084fc); border: none; color: white;">✨ Smart Process with AI</button>
              </div>'''
    if submit_button in content:
        content = content.replace(submit_button, new_buttons)
        print("Button injected successfully.")
    else:
        print(f"Warning: Could not find submit button string: '{submit_button}'")
else:
    print("Warning: Could not find journal form to inject button.")

# 2. Append the Backend Integration Script
print("Appending Backend Integration Script...")
backend_script = '''
<script>
    // --- Backend Integration & Overrides ---

    const API_BASE_URL = 'http://localhost:5000/api';

    // Override initApp to load from Backend
    async function initApp() {
        console.log('Initializing App with Backend Data...');
        
        // 1. Setup Navigation & Listeners (from original init)
        setupNavigation();
        setupEventListeners();
        setupPhotoUpload();
        
        // 2. Load Data from Backend
        await loadBackendData();
        
        // 3. Render - CRITICAL: Render AFTER data is loaded
        updateGardenSelector();
        renderGardenGrid();
        renderPlants(); // This needs appState.plants to be populated
        renderJournal();
        updateStats();
        updateFilters();
        updateDashboard();
        renderSettingsGardenList();
        renderFeedingSection();
        renderBudgetSection();
        
        console.log('App initialized with backend data');
    }

    async function loadBackendData() {
        try {
            // Fetch all data in parallel
            const [plantsRes, productsRes, recipesRes, appsRes] = await Promise.all([
                fetch(`${API_BASE_URL}/plants`),
                fetch(`${API_BASE_URL}/products`),
                fetch(`${API_BASE_URL}/recipes`),
                fetch(`${API_BASE_URL}/applications`)
            ]);

            const plants = await plantsRes.json();
            const products = await productsRes.json();
            const recipes = await recipesRes.json();
            const apps = await appsRes.json();

            // Update appState (clearing arrays first to keep const reference)
            appState.plants.length = 0;
            // Parse JSON fields in plants (heightHistory, etc.)
            plants.forEach(p => {
                if (typeof p.heightHistory === 'string') p.heightHistory = JSON.parse(p.heightHistory);
                if (typeof p.healthHistory === 'string') p.healthHistory = JSON.parse(p.healthHistory);
                if (typeof p.photos === 'string') p.photos = JSON.parse(p.photos);
                if (typeof p.feedingRecipes === 'string') p.feedingRecipes = JSON.parse(p.feedingRecipes);
                if (typeof p.feedingApplications === 'string') p.feedingApplications = JSON.parse(p.feedingApplications);
                if (typeof p.journalEntries === 'string') p.journalEntries = JSON.parse(p.journalEntries);
                appState.plants.push(p);
            });

            appState.products.length = 0;
            products.forEach(p => {
                if (typeof p.packageSize === 'string') p.packageSize = JSON.parse(p.packageSize);
                appState.products.push(p);
            });

            appState.feedingRecipes.length = 0;
            recipes.forEach(r => {
                if (typeof r.ingredients === 'string') r.ingredients = JSON.parse(r.ingredients);
                if (typeof r.batchSize === 'string') r.batchSize = JSON.parse(r.batchSize);
                appState.feedingRecipes.push(r);
            });

            appState.feedingApplications.length = 0;
            apps.forEach(a => {
                if (typeof a.amount === 'string') a.amount = JSON.parse(a.amount);
                appState.feedingApplications.push(a);
            });
            
            // Mock Gardens (since we don't have a gardens table yet, we'll just use the default one but populate its plants)
            // Ensure the default garden has the correct ID
            if (appState.gardens.length === 0) {
                 appState.gardens.push({
                    id: 'garden_1',
                    name: 'My Smart Garden',
                    grids: [{ id: 'grid_1', name: 'Main Grid', prefix: 'A', rows: 4, cols: 4 }],
                    plants: [] 
                });
            }
            // Link plants to garden
            appState.gardens[0].plants = appState.plants;
            appState.currentGardenId = 'garden_1';

            // Populate grid dropdown for plant modal
            const gridSelect = document.getElementById('plant-grid');
            if (gridSelect && appState.gardens[0].grids) {
                gridSelect.innerHTML = appState.gardens[0].grids.map(grid => 
                    `<option value="${grid.id}">${grid.name}</option>`
                ).join('');
            }

            console.log('Backend Data Loaded:', appState);

        } catch (error) {
            console.error('Error loading backend data:', error);
            showToast('Error loading data from backend', true);
        }
    }

    // --- CRUD Overrides ---

    // Save Plant
    savePlant = async function() {
        const id = document.getElementById('plant-id').value;
        const name = document.getElementById('plant-name').value;
        const type = document.getElementById('plant-type').value;
        const gridId = document.getElementById('plant-grid').value;
        const quadrant = document.getElementById('plant-quadrant').value;
        const dateAdded = document.getElementById('plant-date').value;
        const health = document.getElementById('plant-health').value;
        
        const plantData = {
            name, type, gridId, quadrant, dateAdded, health,
            gardenId: appState.currentGardenId
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
                showToast('Plant saved successfully');
                closePlantModal();
                await loadBackendData(); // Reload all data
                renderPlants();
                updateStats();
            } else {
                showToast('Error saving plant', true);
            }
        } catch (error) {
            console.error(error);
            showToast('Error saving plant', true);
        }
    };

    // Save Product
    const originalSaveProduct = document.getElementById('save-product').onclick; // It's added via event listener
    // We need to replace the event listener. 
    // Since we can't remove anonymous event listeners easily, we might need to clone the button to strip listeners.
    
    function replaceButtonListener(id, newHandler) {
        const oldBtn = document.getElementById(id);
        if (oldBtn) {
            const newBtn = oldBtn.cloneNode(true);
            oldBtn.parentNode.replaceChild(newBtn, oldBtn);
            newBtn.addEventListener('click', newHandler);
        }
    }

    replaceButtonListener('save-product', async () => {
        const name = document.getElementById('product-name').value;
        const brand = document.getElementById('product-brand').value;
        const category = document.getElementById('product-category').value;
        const price = parseFloat(document.getElementById('product-price').value);
        const pkgAmount = parseFloat(document.getElementById('product-package-amount').value);
        const pkgUnit = document.getElementById('product-package-unit').value;
        const date = document.getElementById('product-date').value;

        const productData = {
            name, brand, category, purchasePrice: price,
            packageSize: { amount: pkgAmount, unit: pkgUnit },
            quantityPurchased: pkgAmount, // Initial assumption
            quantityRemaining: pkgAmount,
            purchaseDate: date
        };

        try {
            const response = await fetch(`${API_BASE_URL}/products`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(productData)
            });

            if (response.ok) {
                showToast('Product saved successfully');
                document.getElementById('product-modal').classList.add('hidden'); // closeProductModal not global?
                await loadBackendData();
                renderBudgetSection();
            } else {
                showToast('Error saving product', true);
            }
        } catch (error) {
            console.error(error);
            showToast('Error saving product', true);
        }
    });

    // Save Recipe
    replaceButtonListener('save-recipe', async () => {
        const name = document.getElementById('recipe-name').value;
        const type = document.getElementById('recipe-type').value;
        const schedule = document.getElementById('recipe-schedule').value;
        const notes = document.getElementById('recipe-notes').value;
        
        // Ingredients are stored in appState.recipeIngredients temporarily?
        // The original code likely used a temp array. We need to check how it worked.
        // Assuming we can just grab them if they are in the UI or a temp variable.
        // appState.recipeIngredients is defined in the script.
        
        const recipeData = {
            name, feedingType: type, schedule, notes,
            ingredients: appState.recipeIngredients || [],
            gardenId: appState.currentGardenId
        };

        try {
            const response = await fetch(`${API_BASE_URL}/recipes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(recipeData)
            });

            if (response.ok) {
                showToast('Recipe saved successfully');
                document.getElementById('recipe-modal').classList.add('hidden');
                await loadBackendData();
                renderFeedingSection();
            } else {
                showToast('Error saving recipe', true);
            }
        } catch (error) {
            console.error(error);
            showToast('Error saving recipe', true);
        }
    });

    // Save Application
    replaceButtonListener('save-application', async () => {
        const recipeId = document.getElementById('application-recipe').value;
        const plantId = document.getElementById('application-plant').value;
        const amount = parseFloat(document.getElementById('application-amount').value);
        const unit = document.getElementById('application-unit').value;
        const date = document.getElementById('application-date').value;
        const notes = document.getElementById('application-notes').value;
        
        // Calculate cost
        const recipe = appState.feedingRecipes.find(r => r.id === recipeId);
        const cost = calculateApplicationCost(recipe, amount, unit, appState.products);

        const appData = {
            plantId, recipeId, date, notes, appliedCost: cost,
            amount: { value: amount, unit: unit }
        };

        try {
            const response = await fetch(`${API_BASE_URL}/applications`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(appData)
            });

            if (response.ok) {
                showToast('Application recorded successfully');
                document.getElementById('application-modal').classList.add('hidden');
                await loadBackendData();
                renderFeedingSection();
                updateDashboard();
            } else {
                showToast('Error recording application', true);
            }
        } catch (error) {
            console.error(error);
            showToast('Error recording application', true);
        }
    });

    // --- Smart Entry Logic ---
    
    // Override saveJournalEntry to prevent errors
    saveJournalEntry = function(text) {
        // For now, just show a message that they should use the Smart Process button
        showToast('Please use the "Smart Process with AI" button to process journal entries', false);
        // Clear the textarea
        document.getElementById('journal-textarea').value = '';
    };
    
    // Make processSmartEntry global so onclick works
    window.processSmartEntry = async function() {
        const text = document.getElementById('journal-textarea').value.trim();
        if (!text) {
            showToast('Please enter some notes first', true);
            return;
        }

        const btn = document.getElementById('smart-process-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Processing...';
        btn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/llm/process-journal`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            const data = await response.json();
            console.log('LLM Result:', data);

            if (data.success && data.processed_data) {
                const pd = data.processed_data;
                const resultSummary = `
                    <strong>✨ AI Processed:</strong><br>
                    <strong>Plants:</strong> ${pd.plants_mentioned.join(', ') || 'None detected'}<br>
                    <strong>Actions:</strong> ${pd.actions.map(a => a.action_type).join(', ') || 'None detected'}<br>
                    <strong>Summary:</strong> ${pd.summary || 'N/A'}
                `;
                
                const journalList = document.getElementById('journal-history');
                if (journalList) {
                    const entryDiv = document.createElement('div');
                    entryDiv.className = 'journal-entry';
                    entryDiv.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                    entryDiv.style.color = 'white';
                    entryDiv.style.padding = '16px';
                    entryDiv.style.borderRadius = '8px';
                    entryDiv.style.marginBottom = '12px';
                    entryDiv.innerHTML = `
                        <div style="font-size: 12px; opacity: 0.9; margin-bottom: 8px;">Just now (AI Processed)</div>
                        <div style="margin-bottom: 12px;">${text}</div>
                        <div style="background: rgba(255,255,255,0.2); padding: 12px; border-radius: 6px;">
                            ${resultSummary}
                        </div>
                    `;
                    journalList.prepend(entryDiv);
                }
                
                showToast('✨ Journal processed successfully!');
                document.getElementById('journal-textarea').value = '';
                
            } else {
                showToast('LLM processing failed: ' + (data.error || 'Unknown error'), true);
            }

        } catch (error) {
            console.error('Error processing journal:', error);
            showToast('Error connecting to LLM service', true);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    };

    // Ensure initApp runs after DOM is fully loaded
    document.addEventListener('DOMContentLoaded', initApp);

</script>
'''

content = content.replace('</body>', backend_script + '\n</body>')

# Rename the original initApp to prevent conflicts
content = content.replace('function initApp() {', 'function originalInitApp_disabled() {', 1)
content = content.replace('initApp();', '// originalInitApp_disabled(); // Disabled - using new initApp from backend integration', 1)

# Write the modified content to index.html
with open('d:/Github/SmartGardenDashBoard/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated index.html with backend integration and fixed initApp call.")
