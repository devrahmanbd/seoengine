<div class="wrap zenseo-settings">
    <h1>⚡ ZenSEO Settings</h1>

    <form id="zenseo-settings-form">
        <!-- AI Mode Selection -->
        <div class="zenseo-card">
            <h2>🏗️ Architecture Mode</h2>
            <table class="form-table">
                <tr>
                    <th>Mode</th>
                    <td>
                        <label>
                            <input type="radio" name="ai_mode" value="internal" checked onchange="zenseoToggleMode()">
                            <strong>Internal (PHP)</strong> - Everything runs in WordPress
                        </label>
                        <br><br>
                        <label>
                            <input type="radio" name="ai_mode" value="external" onchange="zenseoToggleMode()">
                            <strong>External (Python/Node.js)</strong> - Uses external AI service (more powerful!)
                        </label>
                        <p class="description">External mode gives you full Python AI capabilities but requires a separate service.</p>
                    </td>
                </tr>
            </table>
        </div>

        <!-- Internal AI Provider -->
        <div class="zenseo-card" id="internal-settings">
            <h2>🤖 Internal AI (Direct API)</h2>
            <table class="form-table">
                <tr>
                    <th>AI Provider</th>
                    <td>
                        <select name="ai_provider" id="ai_provider">
                            <option value="openai">OpenAI (GPT-4)</option>
                            <option value="openrouter">OpenRouter (Multi-Provider)</option>
                            <option value="anthropic">Anthropic (Claude)</option>
                        </select>
                        <p class="description">Choose which AI service to use for content generation and optimization.</p>
                    </td>
                </tr>
                <tr>
                    <th>OpenAI API Key</th>
                    <td>
                        <input type="password" name="openai_key" class="regular-text" placeholder="sk-...">
                        <p class="description">Get your key from <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI Dashboard</a></p>
                    </td>
                </tr>
                <tr>
                    <th>OpenRouter API Key</th>
                    <td>
                        <input type="password" name="openrouter_key" class="regular-text" placeholder="sk-or-...">
                        <p class="description">Get your key from <a href="https://openrouter.ai/settings" target="_blank">OpenRouter</a></p>
                    </td>
                </tr>
                <tr>
                    <th>Anthropic API Key</th>
                    <td>
                        <input type="password" name="anthropic_key" class="regular-text" placeholder="sk-ant-...">
                        <p class="description">Get your key from <a href="https://console.anthropic.com/settings" target="_blank">Anthropic Console</a></p>
                    </td>
                </tr>
            </table>
        </div>

        <!-- Keyword Research -->
        <div class="zenseo-card">
            <h2>🔑 Keyword Research</h2>
            <table class="form-table">
                <tr>
                    <th>SEMrush API Key</th>
                    <td>
                        <input type="password" name="semrush_key" class="regular-text" placeholder="Optional">
                        <p class="description">Get from <a href="https://www.semrush.com/api/" target="_blank">SEMrush API</a> for accurate keyword data.</p>
                    </td>
                </tr>
                <tr>
                    <th>Default Target Keyword</th>
                    <td>
                        <input type="text" name="target_keyword" class="regular-text" placeholder="Your main keyword">
                        <p class="description">Used as default when analyzing posts without specific keyword.</p>
                    </td>
                </tr>
                <tr>
                    <th>Default Content Type</th>
                    <td>
                        <select name="content_type">
                            <option value="blog">Blog Post</option>
                            <option value="product">Product Page</option>
                            <option value="landing">Landing Page</option>
                            <option value="service">Service Page</option>
                            <option value="faq">FAQ Page</option>
                        </select>
                    </td>
                </tr>
            </table>
        </div>

        <!-- General Settings -->
        <div class="zenseo-card">
            <h2>⚙️ General Settings</h2>
            <table class="form-table">
                <tr>
                    <th>Auto-Analyze on Save</th>
                    <td>
                        <label>
                            <input type="checkbox" name="auto_analyze" value="1" checked>
                            Automatically analyze posts when saved
                        </label>
                    </td>
                </tr>
                <tr>
                    <th>Primary Language</th>
                    <td>
                        <select name="primary_language">
                            <option value="en">English</option>
                            <option value="es">Spanish</option>
                            <option value="fr">French</option>
                            <option value="de">German</option>
                            <option value="it">Italian</option>
                            <option value="pt">Portuguese</option>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th>Target Country</th>
                    <td>
                        <select name="country">
                            <option value="us">United States</option>
                            <option value="uk">United Kingdom</option>
                            <option value="ca">Canada</option>
                            <option value="au">Australia</option>
                            <option value="de">Germany</option>
                            <option value="fr">France</option>
                        </select>
                    </td>
                </tr>
            </table>
        </div>

        <!-- Webmaster Tools -->
        <div class="zenseo-card">
            <h2>🔧 Webmaster Tools Integration</h2>
            <table class="form-table">
                <tr>
                    <th>Google Search Console</th>
                    <td>
                        <p>Connect your site in <a href="https://search.google.com/search-console" target="_blank">Google Search Console</a> to see keyword rankings and indexing data.</p>
                    </td>
                </tr>
                <tr>
                    <th>Bing Webmaster</th>
                    <td>
                        <p>Add your site to <a href="https://www.bing.com/webmaster" target="_blank">Bing Webmaster Tools</a> for additional search visibility.</p>
                    </td>
                </tr>
                <tr>
                    <th>Google Analytics</th>
                    <td>
                        <p>Install <a href="https://wordpress.org/plugins/ga-analytics/" target="_blank">Google Analytics</a> plugin for traffic analysis.</p>
                    </td>
                </tr>
            </table>
        </div>

        <p class="submit">
            <button type="submit" class="button button-primary">Save Settings</button>
        </p>
    </form>
</div>

<script>
jQuery(document).ready(function($) {
    // Load current settings
    $.ajax({
        url: ajaxurl,
        type: 'POST',
        data: { action: 'zenseo_get_settings', nonce: '<?php echo wp_create_nonce('zenseo_nonce'); ?>' },
        success: function(response) {
            if (response.settings) {
                var settings = response.settings;
                $('#ai_provider').val(settings.ai_provider || 'openai');
                $('input[name="openai_key"]').val(settings.openai_key || '');
                $('input[name="openrouter_key"]').val(settings.openrouter_key || '');
                $('input[name="anthropic_key"]').val(settings.anthropic_key || '');
                $('input[name="semrush_key"]').val(settings.semrush_key || '');
                $('input[name="target_keyword"]').val(settings.target_keyword || '');
                $('select[name="content_type"]').val(settings.content_type || 'blog');
                $('input[name="auto_analyze"]').prop('checked', settings.auto_analyze !== false);
                $('select[name="primary_language"]').val(settings.primary_language || 'en');
                $('select[name="country"]').val(settings.country || 'us');
            }
        }
    });

    // Save settings
    $('#zenseo-settings-form').on('submit', function(e) {
        e.preventDefault();
        
        var settings = {
            ai_provider: $('#ai_provider').val(),
            openai_key: $('input[name="openai_key"]').val(),
            openrouter_key: $('input[name="openrouter_key"]').val(),
            anthropic_key: $('input[name="anthropic_key"]').val(),
            semrush_key: $('input[name="semrush_key"]').val(),
            target_keyword: $('input[name="target_keyword"]').val(),
            content_type: $('select[name="content_type"]').val(),
            auto_analyze: $('input[name="auto_analyze"]').is(':checked'),
            primary_language: $('select[name="primary_language"]').val(),
            country: $('select[name="country"]').val()
        };

        $.ajax({
            url: zenseoData.ajaxUrl,
            type: 'POST',
            data: {
                action: 'zenseo_save_settings',
                nonce: zenseoData.nonce,
                settings: settings
            },
            success: function() {
                alert('Settings saved successfully!');
            }
        });
    });

    // Toggle between internal/external mode
    window.zenseoToggleMode = function() {
        var mode = $('input[name="ai_mode"]:checked').val();
        if (mode === 'external') {
            $('#internal-settings').hide();
            $('#external-settings').show();
        } else {
            $('#internal-settings').show();
            $('#external-settings').hide();
        }
    };

    // Test external service
    window.zenseoTestExternal = function() {
        var url = $('input[name="external_service_url"]').val();
        if (!url) {
            alert('Please enter a service URL');
            return;
        }
        
        $('#test-result').html(' Testing...');
        
        $.get(url + '/health', function() {
            $('#test-result').html(' <span style="color:green">✓ Service connected!</span>');
        }).fail(function() {
            $('#test-result').html(' <span style="color:red">✗ Could not connect</span>');
        });
    };
});
</script>