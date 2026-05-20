/* ZenSEO Admin JS */

(function($) {
    'use strict';

    // Show modal
    window.zenseoShowModal = function(type) {
        $('.zenseo-modal').show();
    };

    // Close modal
    $('.zenseo-close').on('click', function() {
        $('.zenseo-modal').hide();
    });

    // Close on outside click
    $(window).on('click', function(e) {
        if (e.target.classList.contains('zenseo-modal')) {
            $('.zenseo-modal').hide();
        }
    });

    // Bulk analyze
    window.zenseoBulkAnalyze = function() {
        if (!confirm('Analyze all published posts? This may take a while.')) {
            return;
        }

        var posts = [];
        $('.zenseo-post-checkbox:checked').each(function() {
            posts.push($(this).val());
        });

        if (posts.length === 0) {
            alert('No posts selected');
            return;
        }

        var i = 0;
        function processNext() {
            if (i >= posts.length) {
                alert('Analysis complete!');
                return;
            }

            $.ajax({
                url: zenseoData.ajaxUrl,
                type: 'POST',
                data: {
                    action: 'zenseo_optimize',
                    nonce: zenseoData.nonce,
                    post_id: posts[i]
                },
                success: function() {
                    i++;
                    var percent = Math.round((i / posts.length) * 100);
                    $('.zenseo-progress-bar').css('width', percent + '%');
                    processNext();
                }
            });
        }

        $('.zenseo-progress').show();
        processNext();
    };

    // Analyze post from meta box
    window.zenseoAnalyzePost = function(postId) {
        $.ajax({
            url: zenseoData.ajaxUrl,
            type: 'POST',
            data: {
                action: 'zenseo_optimize',
                nonce: zenseoData.nonce,
                post_id: postId
            },
            success: function(response) {
                if (response.success && response.data.score_after) {
                    // Update meta box score
                    location.reload();
                }
            }
        });
    };

    // Initialize
    $(document).ready(function() {
        // Add bulk checkbox to post list
        if ($('#the-list').length) {
            $('#the-list tr').each(function() {
                var postId = $(this).attr('id');
                if (postId && postId.startsWith('post-')) {
                    postId = postId.replace('post-', '');
                    $(this).find('.title').prepend(
                        '<input type="checkbox" class="zenseo-post-checkbox" value="' + postId + '" style="margin-right:10px;">'
                    );
                }
            });
        }
    });

})(jQuery);