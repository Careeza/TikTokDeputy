// State
let deputies = [];
let filteredDeputies = [];
let currentDeputy = null;
let currentAccount = null;
let autoRefreshInterval = null;
let lastUpdateTime = new Date();

// Custom Confirm Dialog
function showConfirm(message, title = 'Confirmation') {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const titleEl = document.getElementById('confirmTitle');
        const messageEl = document.getElementById('confirmMessage');
        const okBtn = document.getElementById('confirmOk');
        const cancelBtn = document.getElementById('confirmCancel');
        
        titleEl.textContent = title;
        messageEl.textContent = message;
        modal.style.display = 'block';
        
        const handleOk = () => {
            modal.style.display = 'none';
            cleanup();
            resolve(true);
        };
        
        const handleCancel = () => {
            modal.style.display = 'none';
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            okBtn.removeEventListener('click', handleOk);
            cancelBtn.removeEventListener('click', handleCancel);
        };
        
        okBtn.addEventListener('click', handleOk);
        cancelBtn.addEventListener('click', handleCancel);
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadDeputies();
    setupEventListeners();
    startAutoRefresh();
    updateLastRefreshTime();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('filterVerified').addEventListener('change', applyFilters);
    document.getElementById('filterLegislature').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', applyFilters);
    document.getElementById('searchName').addEventListener('input', applyFilters);

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('modal');
        if (e.target === modal) {
            closeModal();
        }
    });
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        document.getElementById('totalCount').textContent = stats.total;
        document.getElementById('verifiedCount').textContent = stats.verified;
        document.getElementById('unverifiedCount').textContent = stats.unverified;
        document.getElementById('withTikTokCount').textContent = stats.with_tiktok;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load deputies
async function loadDeputies(silent = false) {
    try {
        const response = await fetch('/api/deputies');
        deputies = await response.json();
        
        // Apply current filters and sort instead of directly rendering
        applyFilters();
        
        if (!silent) {
            lastUpdateTime = new Date();
            updateLastRefreshTime();
        }
    } catch (error) {
        console.error('Error loading deputies:', error);
        if (!silent) {
            document.getElementById('deputiesContainer').innerHTML = 
                '<p style="color: white; text-align: center;">Erreur de chargement des données</p>';
        }
    }
}

// Apply filters
function applyFilters() {
    const verifiedFilter = document.getElementById('filterVerified').value;
    const legislatureFilter = document.getElementById('filterLegislature').value;
    const sortBy = document.getElementById('sortBy').value || 'confidence-desc';  // Default to confidence-desc
    const searchTerm = document.getElementById('searchName').value.toLowerCase();

    filteredDeputies = deputies.filter(deputy => {
        if (verifiedFilter !== '') {
            if (verifiedFilter === 'no_account') {
                // Filter for deputies marked as having no TikTok account
                if (!deputy.no_tiktok_account) return false;
            } else {
                const isVerified = verifiedFilter === 'true';
                if (deputy.verified_by_human !== isVerified) return false;
            }
        }

        // Check if legislatures array includes the filtered legislature
        if (legislatureFilter && (!deputy.legislatures || !deputy.legislatures.includes(legislatureFilter))) {
            return false;
        }

        if (searchTerm && !deputy.name.toLowerCase().includes(searchTerm)) {
            return false;
        }

        return true;
    });

    // Apply sorting
    filteredDeputies.sort((a, b) => {
        switch(sortBy) {
            case 'confidence-desc':
                // Sort by confidence (high to low)
                const confA = a.best_match_confidence || 0;
                const confB = b.best_match_confidence || 0;
                return confB - confA;
            
            case 'confidence-asc':
                // Sort by confidence (low to high)
                const confA2 = a.best_match_confidence || 0;
                const confB2 = b.best_match_confidence || 0;
                return confA2 - confB2;
            
            case 'legislature':
                // Sort by legislature (using first legislature in array)
                const legA = a.legislatures && a.legislatures.length > 0 ? a.legislatures[0] : '';
                const legB = b.legislatures && b.legislatures.length > 0 ? b.legislatures[0] : '';
                return legA.localeCompare(legB);
            
            case 'name':
            default:
                // Sort by name (alphabetically)
                return a.name.localeCompare(b.name);
        }
    });

    renderDeputies();
}

// Render deputies
function renderDeputies() {
    const container = document.getElementById('deputiesContainer');
    
    if (filteredDeputies.length === 0) {
        container.innerHTML = '<p style="color: white; text-align: center; grid-column: 1/-1;">Aucun député trouvé</p>';
        return;
    }

    container.innerHTML = filteredDeputies.map(deputy => createDeputyCard(deputy)).join('');
}

// Create deputy card HTML
function createDeputyCard(deputy) {
    const verifiedClass = deputy.verified_by_human ? 'verified' : 'not-verified';
    const verifiedIcon = deputy.verified_by_human ? 
        '<svg class="icon-small"><use href="#icon-check"/></svg>' : 
        '<svg class="icon-small"><use href="#icon-close"/></svg>';
    const verifiedText = deputy.verified_by_human ? 'Vérifié' : 'Non vérifié';
    
    let content = '';
    
    if (deputy.no_tiktok_account) {
        // Show "no account" state
        content = `
            <div class="no-account-display">
                <svg class="icon-small"><use href="#icon-close"/></svg>
                Aucun compte TikTok
            </div>
        `;
    } else if (deputy.verified_by_human && deputy.human_verified_username) {
        // Show verified account
        content = `
            <div class="verified-account-display">
                <div class="username">
                    <svg class="icon-small"><use href="#icon-verified"/></svg>
                    @${deputy.human_verified_username}
                </div>
                <a href="https://www.tiktok.com/@${deputy.human_verified_username}" 
                   target="_blank" 
                   onclick="event.stopPropagation();"
                   style="color: #065f46; text-decoration: none; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 4px;">
                    <svg class="icon-small"><use href="#icon-link"/></svg>
                    Voir le profil TikTok
                </a>
            </div>
        `;
    } else {
        // Show account summary
        const accountCount = deputy.top_3_matches ? deputy.top_3_matches.length : 0;
        if (accountCount > 0) {
            content = `
                <div class="accounts-summary">
                    <strong>${accountCount}</strong> compte${accountCount > 1 ? 's' : ''} possible${accountCount > 1 ? 's' : ''}
                </div>
            `;
        } else {
            content = '<div class="no-tiktok">Aucun compte trouvé</div>';
        }
    }
    
    // Add search buttons for unverified deputies
    const searchButtons = !deputy.verified_by_human && !deputy.no_tiktok_account ? `
        <button class="search-tiktok-btn" onclick="event.stopPropagation(); searchTikTok('${deputy.name.replace(/'/g, "\\'")}')">
            <svg class="icon-small"><use href="#icon-search"/></svg>
            Rechercher sur Google
        </button>
        <button class="search-tiktok-btn" onclick="event.stopPropagation(); searchTikTokDirect('${deputy.name.replace(/'/g, "\\'")}')">
            <svg class="icon-small"><use href="#icon-search"/></svg>
            Rechercher sur TikTok
        </button>
    ` : '';
    
    return `
        <div class="deputy-card ${verifiedClass}" onclick="openDeputyDetails(${deputy.id})">
            <div class="verified-badge ${verifiedClass}">
                ${verifiedIcon}
                ${verifiedText}
            </div>
            
            <div class="deputy-header">
                <div class="deputy-name">${deputy.name}</div>
                <div class="deputy-legislatures">
                    ${(deputy.legislatures || []).map(leg => `<span class="deputy-legislature">Législature ${leg}</span>`).join('')}
                </div>
            </div>
            
            ${content}
            ${searchButtons}
        </div>
    `;
}

// Open deputy details modal
async function openDeputyDetails(deputyId) {
    try {
        const response = await fetch(`/api/deputies/${deputyId}`);
        const deputy = await response.json();
        currentDeputy = deputy;
        
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = createModalContent(deputy);
        
        document.getElementById('modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading deputy details:', error);
    }
}

// Create modal content
function createModalContent(deputy) {
    const verifiedStatus = deputy.verified_by_human ? 
        '<span style="color: #10b981; font-weight: bold;"><svg class="icon-small"><use href="#icon-check"/></svg> Vérifié</span>' : 
        '<span style="color: #ef4444; font-weight: bold;"><svg class="icon-small"><use href="#icon-close"/></svg> Non vérifié</span>';
    
    let mainContent = '';
    
    // If verified with no account
    if (deputy.no_tiktok_account) {
        mainContent = `
            <div class="no-account-section">
                <h3>
                    <svg class="icon"><use href="#icon-close"/></svg>
                    Aucun compte TikTok
                </h3>
                <p style="color: #6b7280; margin: 15px 0;">
                    Ce député n'a pas de compte TikTok officiel.
                </p>
                <div class="action-buttons">
                    <button class="btn btn-secondary" onclick="unverifyNoAccount(${deputy.id})">
                        <svg class="icon-small"><use href="#icon-close"/></svg>
                        Annuler cette confirmation
                    </button>
                </div>
            </div>
        `;
    } else if (deputy.verified_by_human && deputy.human_verified_username) {
        // If verified, show only verified account
        mainContent = `
            <div class="verified-section">
                <h3>
                    <svg class="icon"><use href="#icon-verified"/></svg>
                    Compte TikTok Vérifié
                </h3>
                <div class="username">
                    @${deputy.human_verified_username}
                </div>
                <a href="https://www.tiktok.com/@${deputy.human_verified_username}" 
                   target="_blank" 
                   class="account-link">
                    <svg class="icon-small"><use href="#icon-link"/></svg>
                    Ouvrir sur TikTok
                </a>
                <div class="action-buttons">
                    <button class="btn btn-danger" onclick="unverifyAccount(${deputy.id})">
                        <svg class="icon-small"><use href="#icon-close"/></svg>
                        Annuler la vérification
                    </button>
                </div>
            </div>
        `;
    } else {
        // Show possible accounts
        const accounts = deputy.top_3_matches || [];
        
        if (accounts.length === 1) {
            // If only one account, show it directly
            mainContent = createSingleAccountView(accounts[0], deputy);
        } else if (accounts.length > 1) {
            // If multiple accounts, show list with check buttons
            mainContent = `
                <div class="possible-accounts">
                    <h3>Comptes TikTok possibles (${accounts.length})</h3>
                    <p style="color: #6b7280; margin-bottom: 15px; font-size: 0.95rem;">
                        Cliquez sur "Vérifier ce compte" pour voir les détails de chaque compte.
                    </p>
                    ${accounts.map((account, index) => createAccountListItem(account, index, deputy)).join('')}
                </div>
            `;
        } else {
            mainContent = '<p style="color: #9ca3af; text-align: center; padding: 20px;">Aucun compte TikTok trouvé</p>';
        }
        
        // Add manual add section and no account option
        mainContent += `
            <div class="manual-add-section">
                <h3>
                    <svg class="icon"><use href="#icon-add"/></svg>
                    Ajouter manuellement un compte
                </h3>
                <p style="color: #6b7280; margin-bottom: 10px; font-size: 0.9rem;">
                    Entrez l'URL ou le nom d'utilisateur TikTok
                </p>
                <div class="input-group">
                    <input type="text" 
                           id="manualAccountInput" 
                           placeholder="https://www.tiktok.com/@username ou @username"
                           onkeypress="if(event.key==='Enter') addManualAccount(${deputy.id})">
                    <button class="btn btn-primary" onclick="addManualAccount(${deputy.id})">
                        <svg><use href="#icon-add"/></svg>
                        Ajouter
                    </button>
                </div>
            </div>
            
            <div class="no-account-option">
                <p style="color: #6b7280; margin-bottom: 10px; font-size: 0.9rem; text-align: center;">
                    ou
                </p>
                <button class="btn btn-secondary" style="width: 100%;" onclick="markAsNoAccount(${deputy.id})">
                    <svg class="icon-small"><use href="#icon-close"/></svg>
                    Confirmer qu'il n'y a pas de compte TikTok
                </button>
            </div>
        `;
    }
    
    // Add Google and TikTok search buttons (always visible except when verified with account)
    const searchButtons = !(deputy.verified_by_human && deputy.human_verified_username) ? `
        <div class="google-search-section" style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            <button class="btn btn-secondary" style="width: 100%; margin-bottom: 10px;" onclick="searchTikTok('${deputy.name.replace(/'/g, "\\'")}')">
                <svg class="icon-small"><use href="#icon-search"/></svg>
                Rechercher sur Google
            </button>
            <button class="btn btn-secondary" style="width: 100%;" onclick="searchTikTokDirect('${deputy.name.replace(/'/g, "\\'")}')">
                <svg class="icon-small"><use href="#icon-search"/></svg>
                Rechercher sur TikTok
            </button>
        </div>
    ` : '';
    
    return `
        <div class="modal-header">
            <h2>${deputy.name}</h2>
            <p>Législature${deputy.legislatures && deputy.legislatures.length > 1 ? 's' : ''}: ${(deputy.legislatures || []).join(', ')} | Statut: ${verifiedStatus}</p>
        </div>
        ${mainContent}
        ${searchButtons}
    `;
}

// Create single account view (when only one account)
function createSingleAccountView(account, deputy) {
    return `
        <div class="account-detail">
            <h3>Compte TikTok trouvé</h3>
            ${createAccountDetailHTML(account)}
            <div class="action-buttons">
                <button class="btn btn-success" onclick="verifyUsername(${deputy.id}, '${account.username}')">
                    <svg><use href="#icon-check"/></svg>
                    Valider ce compte
                </button>
            </div>
        </div>
    `;
}

// Create account list item (for multiple accounts)
function createAccountListItem(account, index, deputy) {
    const isManual = account.sources && account.sources.includes('manual');
    const manualBadge = isManual ? '<span class="badge badge-manual">Ajouté manuellement</span>' : '';
    
    return `
        <div class="account-item">
            <div class="account-item-info">
                <div class="username">@${account.username}</div>
                <div class="meta">
                    Abonnés: ${formatNumber(account.subscribers || 0)} | 
                    Confiance: ${((account.confidence || 0) * 100).toFixed(0)}% | 
                    Sources: ${account.num_sources || 0}
                    ${manualBadge}
                </div>
            </div>
            <button class="btn btn-primary" onclick="showAccountDetail(${deputy.id}, ${index})">
                <svg><use href="#icon-link"/></svg>
                Vérifier ce compte
            </button>
        </div>
    `;
}

// Show account detail in modal
async function showAccountDetail(deputyId, accountIndex) {
    try {
        const response = await fetch(`/api/deputies/${deputyId}`);
        const deputy = await response.json();
        const account = deputy.top_3_matches[accountIndex];
        
        currentAccount = account;
        
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <div class="modal-header">
                <h2>${deputy.name}</h2>
                <button class="btn btn-outline" onclick="openDeputyDetails(${deputyId})" 
                        style="position: absolute; right: 50px; top: 30px;">
                    Retour à la liste
                </button>
            </div>
            <div class="account-detail">
                <h3>Détails du compte TikTok</h3>
                ${createAccountDetailHTML(account)}
                <div class="action-buttons">
                    <button class="btn btn-success" onclick="verifyUsername(${deputy.id}, '${account.username}')">
                        <svg><use href="#icon-check"/></svg>
                        Valider ce compte
                    </button>
                    <button class="btn btn-secondary" onclick="openDeputyDetails(${deputy.id})">
                        Annuler
                    </button>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading account details:', error);
    }
}

// Create account detail HTML
function createAccountDetailHTML(account) {
    const verifiedIcon = account.verified ? '<svg class="icon-small"><use href="#icon-verified"/></svg>' : '';
    const isManual = account.sources && account.sources.includes('manual');
    
    // Prepare mentions badges - show positive mentions prominently, then negatives
    let mentionsHTML = '';
    const positiveMentions = [];
    const negativeMentions = [];
    
    if (!isManual) {
        if (account.mentions_depute) {
            positiveMentions.push({
                label: 'Député',
                type: 'success',
                icon: 'check'
            });
        } else {
            negativeMentions.push({
                label: 'Pas de mention "Député"',
                type: 'warning',
                icon: 'close'
            });
        }
        
        if (account.mentions_assemblee) {
            positiveMentions.push({
                label: 'Assemblée',
                type: 'success',
                icon: 'check'
            });
        } else {
            negativeMentions.push({
                label: 'Pas de mention "Assemblée"',
                type: 'warning',
                icon: 'close'
            });
        }
        
        if (account.mentions_party) {
            positiveMentions.push({
                label: 'Mention de parti',
                type: 'info',
                icon: 'check'
            });
        }
        
        if (account.party_name) {
            positiveMentions.push({
                label: account.party_name,
                type: 'info',
                icon: null
            });
        }
    }
    
    // Combine positive mentions first, then negative
    const allMentions = [...positiveMentions, ...negativeMentions];
    
    if (allMentions.length > 0) {
        mentionsHTML = `
            <div class="badges-section">
                <h4>Mentions dans la bio</h4>
                <div class="badges">
                    ${allMentions.map(m => `
                        <span class="badge badge-${m.type}">
                            ${m.icon ? `<svg class="icon-small"><use href="#icon-${m.icon}"/></svg>` : ''}
                            ${m.label}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    return `
        <div class="username">
            @${account.username}
            ${verifiedIcon}
        </div>
        <a href="https://www.tiktok.com/@${account.username}" 
           target="_blank" 
           class="account-link">
            <svg class="icon-small"><use href="#icon-link"/></svg>
            https://www.tiktok.com/@${account.username}
        </a>
        
        ${!isManual ? `
            <div class="account-stats">
                <div class="stat">
                    <span class="stat-title">Abonnés</span>
                    <span class="stat-number">${formatNumber(account.subscribers || 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-title">Confiance</span>
                    <span class="stat-number">${((account.confidence || 0) * 100).toFixed(1)}%</span>
                </div>
                <div class="stat">
                    <span class="stat-title">Score</span>
                    <span class="stat-number">${account.raw_score || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-title">Sources</span>
                    <span class="stat-number">${account.num_sources || 0}</span>
                </div>
            </div>
        ` : ''}
        
        ${account.bio && account.bio.trim() !== '' ? `
            <div class="badges-section">
                <h4>Biographie</h4>
                <div class="account-bio">${account.bio}</div>
            </div>
        ` : `
            <div class="badges-section">
                <h4>Biographie</h4>
                <p style="color: #9ca3af; font-style: italic; margin: 10px 0;">Aucune biographie</p>
            </div>
        `}
        
        ${mentionsHTML}
        
        ${!isManual ? `
            <p style="margin-top: 15px; color: #6b7280; font-size: 0.9rem;">
                <strong>Sources de détection:</strong> ${(account.sources || []).join(', ')}
            </p>
        ` : '<span class="badge badge-manual">Compte ajouté manuellement</span>'}
    `;
}

// Verify username
async function verifyUsername(deputyId, username) {
    const confirmed = await showConfirm(
        `Confirmer que @${username} est le compte officiel TikTok de ce député ?`,
        'Vérifier le compte'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/api/deputies/${deputyId}/verify`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                verified_by_human: true,
                human_verified_username: username
            })
        });
        
        if (response.ok) {
            closeModal();
            await loadDeputies();
            await loadStats();
        }
    } catch (error) {
        console.error('Error verifying:', error);
        await showConfirm('Erreur lors de la vérification. Veuillez réessayer.', 'Erreur');
    }
}

// Unverify account
async function unverifyAccount(deputyId) {
    const confirmed = await showConfirm(
        'Êtes-vous sûr de vouloir annuler la vérification de ce compte ?',
        'Annuler la vérification'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/api/deputies/${deputyId}/verify`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                verified_by_human: false,
                human_verified_username: null,
                no_tiktok_account: false
            })
        });
        
        if (response.ok) {
            closeModal();
            await loadDeputies();
            await loadStats();
        }
    } catch (error) {
        console.error('Error unverifying:', error);
        await showConfirm('Erreur lors de l\'annulation. Veuillez réessayer.', 'Erreur');
    }
}

// Mark as no TikTok account
async function markAsNoAccount(deputyId) {
    const confirmed = await showConfirm(
        'Confirmer que ce député n\'a pas de compte TikTok officiel ?',
        'Aucun compte TikTok'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/api/deputies/${deputyId}/verify`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                verified_by_human: true,
                human_verified_username: null,
                no_tiktok_account: true
            })
        });
        
        if (response.ok) {
            closeModal();
            await loadDeputies();
            await loadStats();
        }
    } catch (error) {
        console.error('Error marking as no account:', error);
        await showConfirm('Erreur lors de la confirmation. Veuillez réessayer.', 'Erreur');
    }
}

// Unverify no account status
async function unverifyNoAccount(deputyId) {
    const confirmed = await showConfirm(
        'Êtes-vous sûr de vouloir annuler cette confirmation ?',
        'Annuler la confirmation'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/api/deputies/${deputyId}/verify`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                verified_by_human: false,
                human_verified_username: null,
                no_tiktok_account: false
            })
        });
        
        if (response.ok) {
            closeModal();
            await loadDeputies();
            await loadStats();
        }
    } catch (error) {
        console.error('Error unverifying no account:', error);
        await showConfirm('Erreur lors de l\'annulation. Veuillez réessayer.', 'Erreur');
    }
}

// Add manual account
async function addManualAccount(deputyId) {
    const input = document.getElementById('manualAccountInput');
    let value = input.value.trim();
    
    if (!value) {
        await showConfirm('Veuillez entrer une URL ou un nom d\'utilisateur TikTok', 'Champ vide');
        return;
    }
    
    // Convert to proper TikTok URL
    if (value.startsWith('@')) {
        value = `https://www.tiktok.com/${value}`;
    } else if (!value.startsWith('http')) {
        value = `https://www.tiktok.com/@${value}`;
    }
    
    try {
        const response = await fetch(`/api/deputies/${deputyId}/add-manual`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tiktok_url: value
            })
        });
        
        if (response.ok) {
            // Close modal and refresh the list
            closeModal();
            await loadDeputies();
            await loadStats();
        } else {
            await showConfirm('Erreur lors de l\'ajout du compte. Veuillez réessayer.', 'Erreur');
        }
    } catch (error) {
        console.error('Error adding manual account:', error);
        await showConfirm('Erreur lors de l\'ajout du compte. Veuillez réessayer.', 'Erreur');
    }
}

// Close modal
function closeModal() {
    document.getElementById('modal').style.display = 'none';
    currentDeputy = null;
    currentAccount = null;
}

// Export verified accounts to CSV
async function exportVerifiedAccounts() {
    try {
        const response = await fetch('/api/export/verified-accounts');
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'deputes_tiktok_verified.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            await showConfirm('Erreur lors de l\'export. Veuillez réessayer.', 'Erreur');
        }
    } catch (error) {
        console.error('Error exporting:', error);
        await showConfirm('Erreur lors de l\'export. Veuillez réessayer.', 'Erreur');
    }
}

// Search Google for deputy
function searchTikTok(deputyName) {
    const searchQuery = encodeURIComponent(`${deputyName} député tiktok`);
    window.open(`https://www.google.com/search?q=${searchQuery}`, '_blank');
}

// Search TikTok directly for deputy
function searchTikTokDirect(deputyName) {
    const searchQuery = encodeURIComponent(deputyName);
    window.open(`https://www.tiktok.com/search?q=${searchQuery}`, '_blank');
}

// Auto-refresh functionality
function startAutoRefresh() {
    // Refresh data every 30 seconds
    autoRefreshInterval = setInterval(async () => {
        await loadDeputies(true);  // Silent refresh
        await loadStats();
        updateLastRefreshTime();
    }, 30000); // 30 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

function updateLastRefreshTime() {
    const timeElement = document.getElementById('lastUpdateTime');
    if (timeElement) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        timeElement.textContent = `Dernière mise à jour: ${timeStr}`;
    }
}

// Manual refresh
async function manualRefresh() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<svg class="icon-small spinning"><use href="#icon-refresh"/></svg> Actualisation...';
    }
    
    await loadDeputies();
    await loadStats();
    
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<svg class="icon-small"><use href="#icon-refresh"/></svg> Actualiser';
    }
}

// Helper: Format numbers
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}
