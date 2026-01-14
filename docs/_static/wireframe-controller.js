/**
 * Wireframe Demo Controller - Enhanced Version
 * Reusable JavaScript for initializing and controlling wireframe demos
 * Supports all features from index.html including subtabs, viewer toolbar, etc.
 */

(function() {
    'use strict';
    
    // Store all wireframe instances
    window.WireframeInstances = window.WireframeInstances || {};
    
    /**
     * Initialize a wireframe demo with the given configuration
     * @param {string} containerId - The ID of the container element
     * @param {Object} config - Configuration object
     */
    window.initWireframeDemo = function(containerId, config) {
        // Wait for DOM to be ready
        function init() {
            var container = document.getElementById(containerId);
            if (!container) {
                console.error('Wireframe container not found:', containerId);
                return;
            }
            
            // Parse configuration with defaults
            var cfg = {
                disabledTabs: config.disabledTabs || [],
                legendEntries: config.legendEntries || [],
                sidebarId: config.sidebarId || '',
                sidebarContent: config.sidebarContent || '',
                sidebarTabs: config.sidebarTabs || null, // {tabs: [{title, content}], learnMore: [{text, target}]}
                viewerContent: config.viewerContent || '',
                showFooter: config.showFooter !== false,
                autoCycle: config.autoCycle || false,
                cycleSteps: config.cycleSteps || [],
                showViewerToolbar: config.showViewerToolbar !== false,
                showToolbarRight: config.showToolbarRight || false,
                toolbarSearchPlaceholder: config.toolbarSearchPlaceholder || 'Search documentation...',
                toolbarVersion: config.toolbarVersion || '',
                showMouseoverButton: config.showMouseoverButton || false,
                onMouseoverClick: config.onMouseoverClick || null,
                onFooterButtonClick: config.onFooterButtonClick || null
            };
            
            // Get elements
            var wireframeId = containerId.replace('wireframe-container-', '');
            var toolbar = document.getElementById('wireframe-toolbar-' + wireframeId);
            var sidebar = document.getElementById('wireframe-sidebar-' + wireframeId);
            var sidebarBody = document.getElementById('wireframe-sidebar-body-' + wireframeId);
            var sidebarContent = document.getElementById('wireframe-sidebar-content-' + wireframeId);
            var sidebarFooter = document.getElementById('wireframe-sidebar-footer-' + wireframeId);
            var viewerContent = document.getElementById('wireframe-viewer-content-' + wireframeId);
            var viewerToolbar = document.getElementById('wireframe-viewer-toolbar-' + wireframeId);
            var legend = document.getElementById('wireframe-legend-' + wireframeId);
            var cycleControl = document.getElementById('wireframe-cycle-control-' + wireframeId);
            
            // Icon SVG data
            var iconSvgs = {
                'play': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M8,5.14V19.14L19,12.14L8,5.14Z\" /></svg>')",
                'pause': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M14,19H18V5H14M6,19H10V5H6V19Z\" /></svg>')",
                'restart': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,4C14.1,4 16.1,4.8 17.6,6.3C20.7,9.4 20.7,14.5 17.6,17.6C15.8,19.5 13.3,20.2 10.9,19.9L11.4,17.9C13.1,18.1 14.9,17.5 16.2,16.2C18.5,13.9 18.5,10.1 16.2,7.7C15.1,6.6 13.5,6 12,6V10.6L7,5.6L12,0.6V4M6.3,17.6C3.7,15 3.3,11 5.1,7.9L6.6,9.4C5.5,11.6 5.9,14.4 7.8,16.2C8.3,16.7 8.9,17.1 9.6,17.4L9,19.4C8,19 7.1,18.4 6.3,17.6Z\" /></svg>')",
                'database-import': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M19,19V5H5V19H19M19,3A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5A2,2 0 0,1 3,19V5C3,3.89 3.9,3 5,3H19M11,7H13V11H17V13H13V17H11V13H7V11H11V7Z\" /></svg>')",
                'download': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z\" /></svg>')",
                'tune': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z\" /></svg>')",
                'information': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z\" /></svg>')",
                'wrench': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M8 13C6.14 13 4.59 14.28 4.14 16H2V18H4.14C4.59 19.72 6.14 21 8 21S11.41 19.72 11.86 18H22V16H11.86C11.41 14.28 9.86 13 8 13M8 19C6.9 19 6 18.1 6 17C6 15.9 6.9 15 8 15S10 15.9 10 17C10 18.1 9.1 19 8 19M19.86 6C19.41 4.28 17.86 3 16 3S12.59 4.28 12.14 6H2V8H12.14C12.59 9.72 14.14 11 16 11S19.41 9.72 19.86 8H22V6H19.86M16 9C14.9 9 14 8.1 14 7C14 5.9 14.9 5 16 5S18 5.9 18 7C18 8.1 17.1 9 16 9Z\" /></svg>')",
                'selection': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M2 2H8V4H4V8H2V2M2 16H4V20H8V22H2V16M16 2H22V8H20V4H16V2M20 16H22V22H16V20H20V16Z\" /></svg>')",
                'auto-fix': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M7.5,5.6L5,7L6.4,4.5L5,2L7.5,3.4L10,2L8.6,4.5L10,7L7.5,5.6M19.5,15.4L22,14L20.6,16.5L22,19L19.5,17.6L17,19L18.4,16.5L17,14L19.5,15.4M22,2L20.6,4.5L22,7L19.5,5.6L17,7L18.4,4.5L17,2L19.5,3.4L22,2M13.34,12.78L15.78,10.34L13.66,8.22L11.22,10.66L13.34,12.78M14.37,7.29L16.71,9.63C17.1,10 17.1,10.65 16.71,11.04L5.04,22.71C4.65,23.1 4,23.1 3.63,22.71L1.29,20.37C0.9,20 0.9,19.35 1.29,18.96L12.96,7.29C13.35,6.9 14,6.9 14.37,7.29Z\" /></svg>')",
                'bqplot:home': "url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"white\" d=\"M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z\" /></svg>')"
            };
            
            // Build toolbar
            var toolbarConfig = [
                {id: 'loaders', icon: 'database-import', title: 'Import Data'},
                {id: 'save', icon: 'download', title: 'Export'},
                {type: 'divider'},
                {id: 'settings', icon: 'tune', title: 'Plot Options'},
                {id: 'info', icon: 'information', title: 'Metadata'},
                {id: 'plugins', icon: 'wrench', title: 'Plugins'},
                {id: 'subsets', icon: 'selection', title: 'Subsets'}
            ];
            
            var toolbarHtml = '';
            toolbarConfig.forEach(function(item) {
                if (item.type === 'divider') {
                    toolbarHtml += '<div class="wireframe-toolbar-divider"></div>';
                } else {
                    var disabled = cfg.disabledTabs.indexOf(item.id) !== -1;
                    var disabledClass = disabled ? ' disabled' : '';
                    var dataSidebar = disabled ? '' : ' data-sidebar="' + item.id + '"';
                    toolbarHtml += '<div class="wireframe-toolbar-icon' + disabledClass + '"' + dataSidebar + ' data-icon="' + item.icon + '" title="' + item.title + '"></div>';
                }
            });
            
            // Add mouseover button if enabled
            if (cfg.showMouseoverButton) {
                toolbarHtml += '<div class="wireframe-toolbar-divider"></div>';
                toolbarHtml += '<div class="wireframe-toolbar-icon mouseover-button" data-icon="auto-fix" title="Mouseover Info"></div>';
            }
            
            toolbarHtml += '<div class="wireframe-toolbar-spacer"></div>';
            
            // Add toolbar right section if enabled
            if (cfg.showToolbarRight) {
                toolbarHtml += '<div class="wireframe-toolbar-right">' +
                    '<div class="wireframe-toolbar-search-row">' +
                    '<input type="text" class="wireframe-toolbar-search" placeholder="' + cfg.toolbarSearchPlaceholder + '" readonly />' +
                    '</div>' +
                    '<div class="wireframe-toolbar-version-row">' +
                    '<span class="wireframe-toolbar-version">' + cfg.toolbarVersion + '</span>' +
                    '</div>' +
                    '</div>';
            }
            
            toolbar.innerHTML = toolbarHtml;
            
            // Apply icon backgrounds to ALL toolbar icons (including disabled ones)
            var allIcons = toolbar.querySelectorAll('.wireframe-toolbar-icon[data-icon]');
            allIcons.forEach(function(icon) {
                var iconName = icon.dataset.icon;
                if (iconName && iconSvgs[iconName]) {
                    icon.style.backgroundImage = iconSvgs[iconName];
                }
            });
            
            // Get clickable icons for event handlers
            var icons = toolbar.querySelectorAll('.wireframe-toolbar-icon[data-sidebar]');
            
            // Build viewer toolbar if enabled
            if (cfg.showViewerToolbar) {
                var viewerToolbarHtml = '<div class="viewer-toolbar-spacer"></div>' +
                    '<div class="viewer-toolbar-icon" data-icon="bqplot:home" title="Home"></div>';
                viewerToolbar.innerHTML = viewerToolbarHtml;
                
                // Apply viewer toolbar icons
                var viewerIcons = viewerToolbar.querySelectorAll('.viewer-toolbar-icon[data-icon]');
                viewerIcons.forEach(function(icon) {
                    var iconName = icon.dataset.icon;
                    if (iconName && iconSvgs[iconName]) {
                        icon.style.backgroundImage = iconSvgs[iconName];
                    }
                });
            } else {
                viewerToolbar.style.display = 'none';
            }
            
            // Populate legend
            if (cfg.legendEntries.length > 0) {
                var colors = ['#007DA4', '#00B4E6', '#C75109', '#4CAF50', '#FFC107'];
                var legendHtml = '';
                cfg.legendEntries.forEach(function(entry, i) {
                    var color = colors[i % colors.length];
                    legendHtml += '<div class="legend-item">' +
                        '<svg class="legend-icon" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">' +
                        '<rect width="20" height="20" rx="3" fill="' + color + '"/>' +
                        '</svg>' +
                        '<span class="legend-text">' + entry + '</span>' +
                        '</div>';
                });
                legend.innerHTML = legendHtml;
            } else {
                legend.style.display = 'none';
            }
            
            // Show cycle control if auto-cycle enabled
            if (cfg.autoCycle && cfg.cycleSteps.length > 0) {
                cycleControl.style.display = 'flex';
                var cycleIconPlay = document.getElementById('wireframe-cycle-icon-play-' + wireframeId);
                var cycleIconPause = document.getElementById('wireframe-cycle-icon-pause-' + wireframeId);
                var cycleIconRestart = document.getElementById('wireframe-cycle-icon-restart-' + wireframeId);
                
                if (cycleIconPlay) cycleIconPlay.style.backgroundImage = iconSvgs['play'];
                if (cycleIconPause) cycleIconPause.style.backgroundImage = iconSvgs['pause'];
                if (cycleIconRestart) cycleIconRestart.style.backgroundImage = iconSvgs['restart'];
            }
            
            // Initialize interaction state
            var currentSidebar = null;
            var currentTabIndex = 0;
            var cycleIndex = 0;
            var cycleInterval = null;
            var cycleState = 'stopped'; // 'stopped', 'playing', 'paused'
            
            // Function to update sidebar content with tabs
            function updateSidebarContent(sidebarType, tabIndex) {
                if (!cfg.sidebarTabs || !cfg.sidebarTabs[sidebarType]) {
                    // Simple content without tabs
                    if (cfg.sidebarContent) {
                        sidebarContent.innerHTML = cfg.sidebarContent;
                    }
                    return;
                }
                
                var sidebarData = cfg.sidebarTabs[sidebarType];
                var tabs = sidebarData.tabs || [];
                var learnMore = sidebarData.learnMore || [];
                
                // Handle single-content sidebars (no tabs)
                if (tabs.length === 0) {
                    var content = sidebarData.content || '';
                    var apiSnippet = sidebarData.apiSnippet || '';
                    var contentHtml = '<div class="wireframe-sidebar-content">' + apiSnippet + content + '</div>';
                    
                    var footerHtml = '';
                    if (learnMore && learnMore.text && cfg.showFooter) {
                        footerHtml = '<div class="wireframe-sidebar-footer" style="display: block;">' +
                            '<button class="wireframe-sidebar-footer-button" data-scroll-target="' + learnMore.target + '">' +
                            learnMore.text +
                            '</button></div>';
                    }
                    
                    sidebarBody.innerHTML = contentHtml;
                    if (footerHtml) {
                        sidebarBody.insertAdjacentHTML('beforeend', footerHtml);
                        
                        // Attach footer button click handler
                        if (cfg.onFooterButtonClick) {
                            var footerButton = sidebarBody.querySelector('.wireframe-sidebar-footer-button');
                            if (footerButton) {
                                footerButton.addEventListener('click', function() {
                                    stopAutoCycle();
                                    var target = footerButton.getAttribute('data-scroll-target');
                                    cfg.onFooterButtonClick(target);
                                });
                            }
                        }
                    }
                    return;
                }
                
                // Ensure tabIndex is valid
                tabIndex = tabIndex || 0;
                if (tabIndex >= tabs.length) tabIndex = 0;
                
                // Build tabs HTML
                var tabsHtml = '<div class="wireframe-sidebar-tabs">';
                tabs.forEach(function(tab, i) {
                    var activeClass = i === tabIndex ? ' active' : '';
                    tabsHtml += '<div class="wireframe-sidebar-tab' + activeClass + '" data-tab-index="' + i + '">' + tab.title + '</div>';
                });
                tabsHtml += '</div>';
                
                // Build content HTML (include API snippet if present)
                var apiSnippet = tabs[tabIndex].apiSnippet || '';
                var contentHtml = '<div class="wireframe-sidebar-content">' + apiSnippet + tabs[tabIndex].content + '</div>';
                
                // Build footer HTML
                var footerHtml = '';
                if (learnMore[tabIndex] && cfg.showFooter) {
                    footerHtml = '<div class="wireframe-sidebar-footer" style="display: block;">' +
                        '<button class="wireframe-sidebar-footer-button" data-scroll-target="' + learnMore[tabIndex].target + '">' +
                        learnMore[tabIndex].text +
                        '</button></div>';
                }
                
                // Update sidebar body
                sidebarBody.innerHTML = tabsHtml + contentHtml;
                if (footerHtml) {
                    sidebarBody.insertAdjacentHTML('beforeend', footerHtml);
                }
                
                // Attach tab click handlers
                var tabElements = sidebarBody.querySelectorAll('.wireframe-sidebar-tab');
                tabElements.forEach(function(tabEl) {
                    tabEl.addEventListener('click', function() {
                        stopAutoCycle();
                        var newTabIndex = parseInt(tabEl.dataset.tabIndex);
                        updateSidebarContent(sidebarType, newTabIndex);
                        currentTabIndex = newTabIndex;
                    });
                });
                
                // Attach footer button click handler
                if (footerHtml && cfg.onFooterButtonClick) {
                    var footerButton = sidebarBody.querySelector('.wireframe-sidebar-footer-button');
                    if (footerButton) {
                        footerButton.addEventListener('click', function() {
                            stopAutoCycle();
                            var target = footerButton.getAttribute('data-scroll-target');
                            cfg.onFooterButtonClick(target);
                        });
                    }
                }
            }
            
            // Show initial sidebar if specified
            if (cfg.sidebarId) {
                sidebar.classList.add('visible');
                var initialIcon = container.querySelector('.wireframe-toolbar-icon[data-sidebar="' + cfg.sidebarId + '"]');
                if (initialIcon) {
                    initialIcon.classList.add('active');
                    currentSidebar = cfg.sidebarId;
                    updateSidebarContent(cfg.sidebarId, 0);
                }
            }
            
            // Icon click handlers
            icons.forEach(function(icon) {
                icon.addEventListener('click', function() {
                    stopAutoCycle();
                    var sidebarType = icon.getAttribute('data-sidebar');
                    if (!sidebarType) return;
                    
                    if (currentSidebar === sidebarType) {
                        sidebar.classList.remove('visible');
                        icon.classList.remove('active');
                        currentSidebar = null;
                    } else {
                        icons.forEach(function(i) { i.classList.remove('active'); });
                        sidebar.classList.add('visible');
                        icon.classList.add('active');
                        currentSidebar = sidebarType;
                        currentTabIndex = 0;
                        updateSidebarContent(sidebarType, 0);
                    }
                });
            });
            
            // Mouseover button click handler
            if (cfg.showMouseoverButton && cfg.onMouseoverClick) {
                var mouseoverButton = toolbar.querySelector('.mouseover-button');
                if (mouseoverButton) {
                    mouseoverButton.addEventListener('click', function() {
                        stopAutoCycle();
                        cfg.onMouseoverClick();
                    });
                }
            }
            
            // Execute a cycle step
            function executeCycleStep(step) {
                var parts = step.split(':');
                var action = parts[0];
                
                if (action === 'click') {
                    var tabName = parts[1];
                    var targetIcon = container.querySelector('.wireframe-toolbar-icon[data-sidebar="' + tabName + '"]');
                    if (targetIcon && !targetIcon.classList.contains('active')) {
                        targetIcon.click();
                    }
                } else if (action === 'select') {
                    var elementId = parts[1];
                    var optionIndex = parseInt(parts[2]) || 0;
                    var selectElement = document.getElementById(elementId);
                    if (selectElement && selectElement.tagName === 'SELECT') {
                        selectElement.selectedIndex = optionIndex % selectElement.options.length;
                    }
                } else if (action === 'tab') {
                    var tabId = parts[1];
                    var tabElement = container.querySelector('[data-tab="' + tabId + '"]');
                    if (tabElement) {
                        tabElement.click();
                    }
                }
            }
            
            // Auto-cycle functions
            function startAutoCycle() {
                cycleState = 'playing';
                var cycleIconPlay = document.getElementById('wireframe-cycle-icon-play-' + wireframeId);
                var cycleIconPause = document.getElementById('wireframe-cycle-icon-pause-' + wireframeId);
                var cycleIconRestart = document.getElementById('wireframe-cycle-icon-restart-' + wireframeId);
                
                if (cycleIconPlay) cycleIconPlay.classList.add('hidden');
                if (cycleIconPause) cycleIconPause.classList.remove('hidden');
                if (cycleIconRestart) cycleIconRestart.classList.add('hidden');
                
                cycleInterval = setInterval(function() {
                    if (cfg.cycleSteps.length > 0) {
                        executeCycleStep(cfg.cycleSteps[cycleIndex]);
                        cycleIndex = (cycleIndex + 1) % cfg.cycleSteps.length;
                    }
                }, 2500);
            }
            
            function stopAutoCycle() {
                if (cycleInterval) {
                    clearInterval(cycleInterval);
                    cycleInterval = null;
                }
                
                var cycleIconPlay = document.getElementById('wireframe-cycle-icon-play-' + wireframeId);
                var cycleIconPause = document.getElementById('wireframe-cycle-icon-pause-' + wireframeId);
                var cycleIconRestart = document.getElementById('wireframe-cycle-icon-restart-' + wireframeId);
                
                if (cycleState === 'playing') {
                    // Was playing, now paused
                    cycleState = 'paused';
                    if (cycleIconPlay) cycleIconPlay.classList.add('hidden');
                    if (cycleIconPause) cycleIconPause.classList.add('hidden');
                    if (cycleIconRestart) cycleIconRestart.classList.remove('hidden');
                } else {
                    // Was stopped or paused
                    cycleState = 'stopped';
                    if (cycleIconPlay) cycleIconPlay.classList.remove('hidden');
                    if (cycleIconPause) cycleIconPause.classList.add('hidden');
                    if (cycleIconRestart) cycleIconRestart.classList.add('hidden');
                }
            }
            
            function restartAutoCycle() {
                if (cycleInterval) {
                    clearInterval(cycleInterval);
                    cycleInterval = null;
                }
                cycleIndex = 0;
                cycleState = 'stopped';
                startAutoCycle();
            }
            
            // Cycle control button handler
            if (cycleControl) {
                cycleControl.addEventListener('click', function() {
                    if (cycleState === 'stopped') {
                        startAutoCycle();
                        cycleControl.setAttribute('data-flyout-text', 'Pause');
                    } else if (cycleState === 'playing') {
                        stopAutoCycle();
                        cycleControl.setAttribute('data-flyout-text', 'Restart');
                    } else if (cycleState === 'paused') {
                        restartAutoCycle();
                        cycleControl.setAttribute('data-flyout-text', 'Pause');
                    }
                });
            }
            
            // Click anywhere to pause
            container.addEventListener('click', function(e) {
                // Don't stop if clicking the cycle control itself
                if (e.target.closest('#wireframe-cycle-control-' + wireframeId)) {
                    return;
                }
                if (cycleState === 'playing') {
                    stopAutoCycle();
                    if (cycleControl) {
                        cycleControl.setAttribute('data-flyout-text', 'Restart');
                    }
                }
            });
            
            // Start auto-cycle if enabled
            if (cfg.autoCycle && cfg.cycleSteps.length > 0) {
                setTimeout(function() {
                    startAutoCycle();
                    if (cycleControl) {
                        cycleControl.setAttribute('data-flyout-text', 'Pause');
                    }
                }, 1000);
            }
            
            // Store instance for potential external access
            window.WireframeInstances[containerId] = {
                container: container,
                config: cfg,
                startAutoCycle: startAutoCycle,
                stopAutoCycle: stopAutoCycle,
                restartAutoCycle: restartAutoCycle
            };
        }
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    };
})();
