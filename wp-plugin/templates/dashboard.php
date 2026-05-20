<div class="wrap zenseo-dashboard">
    <h1>⚡ ZenSEO AI Dashboard</h1>

    <div class="zenseo-grid">
        <!-- Stats Cards -->
        <div class="zenseo-card stats-card">
            <h3>📊 Content Scores</h3>
            <div class="stats-grid">
                <?php
                global $wpdb;
                $table = $wpdb->prefix . 'zenseo_tasks';
                $high = $wpdb->get_var("SELECT COUNT(*) FROM $table WHERE priority = 'high' AND status = 'pending'");
                $medium = $wpdb->get_var("SELECT COUNT(*) FROM $table WHERE priority = 'medium' AND status = 'pending'");
                $completed = $wpdb->get_var("SELECT COUNT(*) FROM $table WHERE status = 'completed'");
                
                $posts_table = $wpdb->prefix . 'posts';
                $avg_score = $wpdb->get_var("SELECT AVG(meta_value) FROM $wpdb->postmeta WHERE meta_key = '_zenseo_score' AND meta_value > 0");
                ?>
                <div class="stat">
                    <span class="stat-value"><?php echo round($avg_score ?: 0); ?></span>
                    <span class="stat-label">Avg Score</span>
                </div>
                <div class="stat high">
                    <span class="stat-value"><?php echo $high; ?></span>
                    <span class="stat-label">High Priority</span>
                </div>
                <div class="stat medium">
                    <span class="stat-value"><?php echo $medium; ?></span>
                    <span class="stat-label">Medium Priority</span>
                </div>
                <div class="stat completed">
                    <span class="stat-value"><?php echo $completed; ?></span>
                    <span class="stat-label">Completed</span>
                </div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="zenseo-card actions-card">
            <h3>🚀 Quick Actions</h3>
            <div class="action-buttons">
                <button class="button button-primary" onclick="zenseoShowModal('analyze')">🔍 Analyze URL</button>
                <button class="button button-secondary" onclick="zenseoShowModal('generate')">✍️ Generate Content</button>
                <button class="button" onclick="zenseoBulkAnalyze()">📊 Bulk Analyze</button>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <h2 class="nav-tab-wrapper">
        <a href="#posts" class="nav-tab nav-tab-active" onclick="zenseoSwitchTab('posts')">📝 Content</a>
        <a href="#tasks" class="nav-tab" onclick="zenseoSwitchTab('tasks')">📋 Tasks</a>
        <a href="#analyze" class="nav-tab" onclick="zenseoSwitchTab('analyze')">🔍 Analyze</a>
        <a href="#generate" class="nav-tab" onclick="zenseoSwitchTab('generate')">✍️ Generate</a>
    </h2>

    <!-- Posts Tab -->
    <div id="tab-posts" class="zenseo-tab-content">
        <table class="widefat striped">
            <thead>
                <tr>
                    <th>Post</th>
                    <th>Score</th>
                    <th>Issues</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="zenseo-posts-list">
                <tr><td colspan="4">Loading...</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Tasks Tab -->
    <div id="tab-tasks" class="zenseo-tab-content" style="display:none;">
        <div id="zenseo-tasks-list">
            <p>Loading tasks...</p>
        </div>
    </div>

    <!-- Analyze Tab -->
    <div id="tab-analyze" class="zenseo-tab-content" style="display:none;">
        <div class="zenseo-card">
            <h3>🔍 Analyze URL</h3>
            <p>Enter a URL to analyze its SEO performance.</p>
            <form id="zenseo-analyze-form">
                <input type="url" name="url" placeholder="https://example.com/page" style="width: 100%; max-width: 500px;" required>
                <input type="text" name="keyword" placeholder="Target keyword (optional)" style="width: 100%; max-width: 300px;">
                <button type="submit" class="button button-primary">Analyze</button>
            </form>
            <div id="zenseo-analyze-results" style="margin-top: 20px;"></div>
        </div>
    </div>

    <!-- Generate Tab -->
    <div id="tab-generate" class="zenseo-tab-content" style="display:none;">
        <div class="zenseo-card">
            <h3>✍️ Generate SEO Content</h3>
            <form id="zenseo-generate-form">
                <input type="text" name="topic" placeholder="Content topic" style="width: 100%; max-width: 500px;" required>
                <select name="type" style="width: 200px;">
                    <option value="blog">Blog Post</option>
                    <option value="product">Product Page</option>
                    <option value="landing">Landing Page</option>
                    <option value="service">Service Page</option>
                    <option value="faq">FAQ Page</option>
                </select>
                <button type="submit" class="button button-primary">Generate</button>
            </form>
            <div id="zenseo-generate-results" style="margin-top: 20px;"></div>
        </div>
    </div>
</div>

<style>
.zenseo-dashboard .zenseo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-bottom: 30px;
}
.zenseo-dashboard .zenseo-card {
    background: #fff;
    border: 1px solid #ddd;
    padding: 20px;
    border-radius: 8px;
}
.zenseo-dashboard .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    text-align: center;
}
.zenseo-dashboard .stat-value {
    display: block;
    font-size: 32px;
    font-weight: bold;
}
.zenseo-dashboard .stat.high .stat-value { color: #ef4444; }
.zenseo-dashboard .stat.medium .stat-value { color: #f59e0b; }
.zenseo-dashboard .stat.completed .stat-value { color: #10b981; }
.zenseo-dashboard .action-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}
.score-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    font-weight: bold;
}
.score-good { background: #d1fae5; color: #059669; }
.score-medium { background: #fef3c7; color: #d97706; }
.score-bad { background: #fee2e2; color: #dc2626; }
</style>

<script>
jQuery(document).ready(function($) {
    // Load posts
    zenseoLoadPosts();
    zenseoLoadTasks();

    // Analyze form
    $('#zenseo-analyze-form').on('submit', function(e) {
        e.preventDefault();
        var url = $(this).find('input[name="url"]').val();
        var keyword = $(this).find('input[name="keyword"]').val();
        
        $('#zenseo-analyze-results').html('<p>Analyzing...</p>');
        
        $.ajax({
            url: zenseoData.ajaxUrl,
            type: 'POST',
            data: {
                action: 'zenseo_analyze',
                nonce: zenseoData.nonce,
                url: url,
                keyword: keyword
            },
            success: function(response) {
                if (response.success) {
                    var data = response.data;
                    var html = '<div class="zenseo-card"><h3>Results for ' + url + '</h3>';
                    html += '<p><strong>Overall Score:</strong> <span class="score-badge ' + (data.overall_score >= 80 ? 'score-good' : data.overall_score >= 60 ? 'score-medium' : 'score-bad') + '">' + data.overall_score + '/100</span></p>';
                    
                    if (data.issues && data.issues.length > 0) {
                        html += '<h4>Issues:</h4><ul>';
                        data.issues.forEach(function(issue) {
                            html += '<li>' + issue + '</li>';
                        });
                        html += '</ul>';
                    }
                    
                    if (data.suggestions && data.suggestions.length > 0) {
                        html += '<h4>Suggestions:</h4><ul>';
                        data.suggestions.forEach(function(s) {
                            html += '<li>' + s + '</li>';
                        });
                        html += '</ul>';
                    }
                    
                    html += '</div>';
                    $('#zenseo-analyze-results').html(html);
                } else {
                    $('#zenseo-analyze-results').html('<p style="color:red;">Error: ' + response.data.message + '</p>');
                }
            }
        });
    });

    // Generate form
    $('#zenseo-generate-form').on('submit', function(e) {
        e.preventDefault();
        var topic = $(this).find('input[name="topic"]').val();
        var type = $(this).find('select[name="type"]').val();
        
        $('#zenseo-generate-results').html('<p>Generating content with AI...</p>');
        
        $.ajax({
            url: zenseoData.ajaxUrl,
            type: 'POST',
            data: {
                action: 'zenseo_generate_content',
                nonce: zenseoData.nonce,
                topic: topic,
                type: type
            },
            success: function(response) {
                if (response.success) {
                    var data = response.data;
                    var html = '<div class="zenseo-card"><h3>Generated Content</h3>';
                    html += '<h4>Title:</h4><p>' + data.title + '</p>';
                    html += '<h4>Meta Description:</h4><p>' + data.meta_description + '</p>';
                    html += '<h4>Content Preview:</h4><div style="max-height: 300px; overflow-y: auto;">' + data.content.substring(0, 2000) + '...</div>';
                    html += '<h4>Schema:</h4><pre style="background:#f5f5f5;padding:10px;overflow-x:auto;">' + data.schema + '</pre>';
                    html += '</div>';
                    $('#zenseo-generate-results').html(html);
                } else {
                    $('#zenseo-generate-results').html('<p style="color:red;">Error: ' + response.data.message + '</p>');
                }
            }
        });
    });
});

function zenseoSwitchTab(tab) {
    jQuery('.nav-tab').removeClass('nav-tab-active');
    jQuery(event.target).addClass('nav-tab-active');
    jQuery('.zenseo-tab-content').hide();
    jQuery('#tab-' + tab).show();
}

function zenseoLoadPosts() {
    jQuery.get(zenseoData.ajaxUrl + '?action=zenseo_get_posts&nonce=' + zenseoData.nonce, function(response) {
        if (response.posts) {
            var html = '';
            response.posts.forEach(function(post) {
                var scoreClass = post.score >= 80 ? 'score-good' : post.score >= 60 ? 'score-medium' : 'score-bad';
                var issueCount = post.analysis && post.analysis.issues ? post.analysis.issues.length : 0;
                
                html += '<tr>';
                html += '<td><a href="' + post.url + '" target="_blank">' + post.title + '</a></td>';
                html += '<td><span class="score-badge ' + scoreClass + '">' + post.score + '</span></td>';
                html += '<td>' + issueCount + '</td>';
                html += '<td><button class="button" onclick="zenseoAnalyzePost(' + post.id + ')">Re-analyze</button></td>';
                html += '</tr>';
            });
            jQuery('#zenseo-posts-list').html(html || '<tr><td colspan="4">No posts analyzed yet</td></tr>');
        }
    });
}

function zenseoLoadTasks() {
    jQuery.ajax({
        url: zenseoData.ajaxUrl,
        type: 'POST',
        data: { action: 'zenseo_get_tasks', nonce: zenseoData.nonce },
        success: function(response) {
            if (response) {
                var html = '<div class="zenseo-tasks">';
                response.forEach(function(task) {
                    var priorityClass = task.priority === 'high' ? 'task-high' : task.priority === 'medium' ? 'task-medium' : 'task-low';
                    html += '<div class="task-item ' + priorityClass + '">';
                    html += '<h4>' + task.title + '</h4>';
                    html += '<p>' + task.description + '</p>';
                    html += '<button class="button button-small" onclick="zenseoCompleteTask(' + task.id + ')">Complete</button>';
                    html += '</div>';
                });
                html += '</div>';
                jQuery('#zenseo-tasks-list').html(html || '<p>No pending tasks</p>');
            }
        }
    });
}

function zenseoAnalyzePost(postId) {
    jQuery.ajax({
        url: zenseoData.ajaxUrl,
        type: 'POST',
        data: { action: 'zenseo_optimize', nonce: zenseoData.nonce, post_id: postId },
        success: function() {
            zenseoLoadPosts();
            alert('Analysis complete!');
        }
    });
}

function zenseoCompleteTask(taskId) {
    jQuery.ajax({
        url: zenseoData.ajaxUrl,
        type: 'POST',
        data: { action: 'zenseo_complete_task', nonce: zenseoData.nonce, task_id: taskId },
        success: function() {
            zenseoLoadTasks();
        }
    });
}
</script>