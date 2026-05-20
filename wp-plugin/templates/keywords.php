<div class="wrap zenseo-keywords">
    <h1>🔑 Keyword Research</h1>

    <div class="zenseo-card">
        <h3>Research New Keywords</h3>
        <form id="zenseo-keyword-form">
            <input type="text" name="seed_keyword" placeholder="Enter a seed keyword" style="width: 300px;" required>
            <button type="submit" class="button button-primary">Research</button>
        </form>
        <div id="zenseo-keyword-results" style="margin-top: 20px;"></div>
    </div>

    <div class="zenseo-card" style="margin-top: 20px;">
        <h3>Saved Keywords</h3>
        <table class="widefat striped">
            <thead>
                <tr>
                    <th>Keyword</th>
                    <th>Volume</th>
                    <th>Difficulty</th>
                    <th>Intent</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="zenseo-saved-keywords">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</div>

<script>
jQuery(document).ready(function($) {
    $('#zenseo-keyword-form').on('submit', function(e) {
        e.preventDefault();
        var keyword = $(this).find('input[name="seed_keyword"]').val();
        
        $('#zenseo-keyword-results').html('<p>Researching...</p>');
        
        $.post(zenseoData.ajaxUrl + '?action=zenseo_research_keywords&nonce=' + zenseoData.nonce, 
            { keyword: keyword }, 
            function(response) {
                if (response && response.length > 0) {
                    var html = '<table class="widefat"><thead><tr><th>Keyword</th><th>Volume</th><th>Difficulty</th><th>Intent</th><th>Score</th></tr></thead><tbody>';
                    response.forEach(function(kw) {
                        html += '<tr>';
                        html += '<td>' + kw.keyword + '</td>';
                        html += '<td>' + kw.volume.toLocaleString() + '</td>';
                        html += '<td>' + kw.difficulty + '/100</td>';
                        html += '<td>' + kw.intent + '</td>';
                        html += '<td>' + kw.score + '</td>';
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                    $('#zenseo-keyword-results').html(html);
                } else {
                    $('#zenseo-keyword-results').html('<p>No keywords found. Try another seed.</p>');
                }
            }
        );
    });
});
</script>