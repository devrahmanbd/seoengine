<?php
/**
 * REST API Class
 */

class ZenSEO_API {

    /**
     * Register routes
     */
    public function register_routes() {
        register_rest_route('zenseo/v1', '/analyze', array(
            'methods' => 'POST',
            'callback' => array($this, 'analyze_url'),
            'permission_callback' => array($this, 'check_permission')
        ));

        register_rest_route('zenseo/v1', '/optimize', array(
            'methods' => 'POST',
            'callback' => array($this, 'optimize_post'),
            'permission_callback' => array($this, 'check_permission')
        ));

        register_rest_route('zenseo/v1', '/generate', array(
            'methods' => 'POST',
            'callback' => array($this, 'generate_content'),
            'permission_callback' => array($this, 'check_permission')
        ));

        register_rest_route('zenseo/v1', '/keywords', array(
            'methods' => 'POST',
            'callback' => array($this, 'get_keywords'),
            'permission_callback' => array($this, 'check_permission')
        ));

        register_rest_route('zenseo/v1', '/schema', array(
            'methods' => 'POST',
            'callback' => array($this, 'generate_schema'),
            'permission_callback' => array($this, 'check_permission')
        ));

        register_rest_route('zenseo/v1', '/tasks', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_tasks'),
            'permission_callback' => array($this, 'check_permission')
        ));

        register_rest_route('zenseo/v1', '/posts', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_posts'),
            'permission_callback' => array($this, 'check_permission')
        ));
    }

    /**
     * Check permission
     */
    public function check_permission() {
        return current_user_can('manage_options');
    }

    /**
     * Analyze URL
     */
    public function analyze_url($request) {
        $url = $request->get_param('url');
        $keyword = $request->get_param('keyword');

        if (empty($url)) {
            return new WP_Error('no_url', 'URL is required', array('status' => 400));
        }

        $analyzer = new ZenSEO_Analyzer();
        $result = $analyzer->analyze_url($url, $keyword);

        return rest_ensure_response($result);
    }

    /**
     * Optimize post
     */
    public function optimize_post($request) {
        $post_id = $request->get_param('post_id');
        $keyword = $request->get_param('keyword');

        if (empty($post_id)) {
            return new WP_Error('no_post', 'Post ID is required', array('status' => 400));
        }

        $analyzer = new ZenSEO_Analyzer();
        $result = $analyzer->optimize_post($post_id, $keyword);

        return rest_ensure_response($result);
    }

    /**
     * Generate content
     */
    public function generate_content($request) {
        $topic = $request->get_param('topic');
        $type = $request->get_param('type') ?: 'blog';

        if (empty($topic)) {
            return new WP_Error('no_topic', 'Topic is required', array('status' => 400));
        }

        $ai = new ZenSEO_AI();
        $result = $ai->generate_content($topic, $type);

        return rest_ensure_response($result);
    }

    /**
     * Get keywords
     */
    public function get_keywords($request) {
        $keyword = $request->get_param('keyword');
        $limit = $request->get_param('limit') ?: 20;

        if (empty($keyword)) {
            return new WP_Error('no_keyword', 'Keyword is required', array('status' => 400));
        }

        $research = new ZenSEO_Keyword_Research();
        $result = $research->get_suggestions($keyword, $limit);

        return rest_ensure_response($result);
    }

    /**
     * Generate schema
     */
    public function generate_schema($request) {
        $type = $request->get_param('type');
        $options = $request->get_param('options') ?: array();

        if (empty($type)) {
            return new WP_Error('no_type', 'Schema type is required', array('status' => 400));
        }

        $schema = new ZenSEO_Schema();
        $result = $schema->generate(array_merge(array('type' => $type), $options));

        return rest_ensure_response(array('schema' => $result));
    }

    /**
     * Get tasks
     */
    public function get_tasks($request) {
        global $wpdb;
        $table = $wpdb->prefix . 'zenseo_tasks';

        $post_id = $request->get_param('post_id');
        
        $where = $post_id ? $wpdb->prepare(" WHERE post_id = %d", $post_id) : " WHERE status != 'completed'";
        
        $tasks = $wpdb->get_results("SELECT * FROM $table $where ORDER BY priority DESC, created_at DESC LIMIT 50");

        return rest_ensure_response($tasks);
    }

    /**
     * Get posts with scores
     */
    public function get_posts($request) {
        $args = array(
            'post_type' => get_post_types(array('public' => true)),
            'posts_per_page' => $request->get_param('per_page') ?: 20,
            'paged' => $request->get_param('page') ?: 1,
            'post_status' => 'publish'
        );

        $query = new WP_Query($args);
        $posts = array();

        foreach ($query->posts as $post) {
            $score = get_post_meta($post->ID, '_zenseo_score', true);
            $analysis = get_post_meta($post->ID, '_zenseo_analysis', true);

            $posts[] = array(
                'id' => $post->ID,
                'title' => $post->post_title,
                'url' => get_permalink($post->ID),
                'score' => $score ?: 0,
                'analysis' => $analysis,
                'date' => $post->post_date
            );
        }

        return rest_ensure_response(array(
            'posts' => $posts,
            'total' => $query->found_posts,
            'pages' => $query->max_num_pages
        ));
    }
}