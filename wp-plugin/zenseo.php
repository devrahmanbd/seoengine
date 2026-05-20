<?php
/**
 * Plugin Name: ZenSEO AI Engine
 * Plugin URI: https://zenseo.ai
 * Description: 100% AI-powered SEO engine - automates everything Yoast/RankMath does without human touch. Auto-generates content, optimizes meta tags, builds schemas, and provides actionable tasks.
 * Version: 1.0.0
 * Author: ZenSEO AI
 * Author URI: https://zenseo.ai
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: zenseo
 * Domain Path: /languages
 * Requires at least: 5.8
 * Requires PHP: 7.4
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('ZENSEO_VERSION', '1.0.0');
define('ZENSEO_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('ZENSEO_PLUGIN_URL', plugin_dir_url(__FILE__));
define('ZENSEO_PLUGIN_BASENAME', plugin_basename(__FILE__));

/**
 * Main Plugin Class
 */
class ZenSEO_Engine {

    /**
     * @var ZenSEO_Engine The single instance of the class
     */
    protected static $_instance = null;

    /**
     * Main ZenSEO_Engine Instance
     *
     * @return ZenSEO_Engine - Main instance
     */
    public static function instance() {
        if (is_null(self::$_instance)) {
            self::$_instance = new self();
        }
        return self::$_instance;
    }

    /**
     * Constructor
     */
    public function __construct() {
        $this->init_hooks();
        $this->includes();
    }

    /**
     * Initialize hooks
     */
    private function init_hooks() {
        // Activation/Deactivation
        register_activation_hook(__FILE__, array($this, 'activate'));
        register_deactivation_hook(__FILE__, array($this, 'deactivate'));

        // Init
        add_action('init', array($this, 'init'), 0);

        // Admin
        if (is_admin()) {
            add_action('admin_menu', array($this, 'add_admin_menu'));
            add_action('admin_enqueue_scripts', array($this, 'enqueue_admin_scripts'));
            add_action('wp_ajax_zenseo_analyze', array($this, 'ajax_analyze'));
            add_action('wp_ajax_zenseo_optimize', array($this, 'ajax_optimize'));
            add_action('wp_ajax_zenseo_generate_content', array($this, 'ajax_generate_content'));
            add_action('wp_ajax_zenseo_save_settings', array($this, 'ajax_save_settings'));
            add_action('wp_ajax_zenseo_get_tasks', array($this, 'ajax_get_tasks'));
            add_action('wp_ajax_zenseo_complete_task', array($this, 'ajax_complete_task'));
        }

        // REST API
        add_action('rest_api_init', array($this, 'register_rest_routes'));

        // Auto-analysis on save
        add_action('save_post', array($this, 'auto_analyze_on_save'), 20, 2);

        // Add meta boxes
        add_action('add_meta_boxes', array($this, 'add_meta_boxes'));
    }

    /**
     * Include required files
     */
    private function includes() {
        require_once ZENSEO_PLUGIN_DIR . 'includes/class-zenseo-analyzer.php';
        require_once ZENSEO_PLUGIN_DIR . 'includes/class-zenseo-ai.php';
        require_once ZENSEO_PLUGIN_DIR . 'includes/class-zenseo-schema.php';
        require_once ZENSEO_PLUGIN_DIR . 'includes/class-zenseo-keyword-research.php';
        require_once ZENSEO_PLUGIN_DIR . 'includes/class-zenseo-api.php';
    }

    /**
     * Plugin activation
     */
    public function activate() {
        // Create database tables
        $this->create_tables();

        // Set default options
        $this->set_default_options();

        // Flush rewrite rules
        flush_rewrite_rules();
    }

    /**
     * Plugin deactivation
     */
    public function deactivate() {
        flush_rewrite_rules();
    }

    /**
     * Initialize
     */
    public function init() {
        // Load text domain
        load_plugin_textdomain('zenseo', false, dirname(ZENSEO_PLUGIN_BASENAME) . '/languages');

        // Register custom post type for SEO reports
        $this->register_post_types();
    }

    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_menu_page(
            __('ZenSEO AI', 'zenseo'),
            __('ZenSEO AI', 'zenseo'),
            'manage_options',
            'zenseo-dashboard',
            array($this, 'render_dashboard'),
            'dashicons-chart-bar',
            99
        );

        add_submenu_page(
            'zenseo-dashboard',
            __('Dashboard', 'zenseo'),
            __('Dashboard', 'zenseo'),
            'manage_options',
            'zenseo-dashboard',
            array($this, 'render_dashboard')
        );

        add_submenu_page(
            'zenseo-dashboard',
            __('Settings', 'zenseo'),
            __('Settings', 'zenseo'),
            'manage_options',
            'zenseo-settings',
            array($this, 'render_settings')
        );

        add_submenu_page(
            'zenseo-dashboard',
            __('Keyword Research', 'zenseo'),
            __('Keywords', 'zenseo'),
            'manage_options',
            'zenseo-keywords',
            array($this, 'render_keywords')
        );
    }

    /**
     * Enqueue admin scripts
     */
    public function enqueue_admin_scripts($hook) {
        // Only on our pages
        if (strpos($hook, 'zenseo') === false) {
            return;
        }

        // CSS
        wp_enqueue_style('zenseo-admin', ZENSEO_PLUGIN_URL . 'assets/css/admin.css', array(), ZENSEO_VERSION);

        // JS
        wp_enqueue_script('zenseo-admin', ZENSEO_PLUGIN_URL . 'assets/js/admin.js', array('jquery'), ZENSEO_VERSION, true);

        // Localize
        wp_localize_script('zenseo-admin', 'zenseoData', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('zenseo_nonce'),
            'i18n' => array(
                'analyzing' => __('Analyzing...', 'zenseo'),
                'optimizing' => __('Optimizing...', 'zenseo'),
                'generating' => __('Generating...', 'zenseo'),
                'success' => __('Success!', 'zenseo'),
                'error' => __('Error', 'zenseo'),
            )
        ));
    }

    /**
     * Register REST routes
     */
    public function register_rest_routes() {
        $api = new ZenSEO_API();
        $api->register_routes();
    }

    /**
     * Add meta boxes
     */
    public function add_meta_boxes() {
        $post_types = get_post_types(array('public' => true), 'names');
        
        foreach ($post_types as $post_type) {
            add_meta_box(
                'zenseo_score',
                __('ZenSEO Score', 'zenseo'),
                array($this, 'render_meta_box'),
                $post_type,
                'side',
                'high'
            );
        }
    }

    /**
     * Render meta box
     */
    public function render_meta_box($post) {
        $score = get_post_meta($post->ID, '_zenseo_score', true);
        $analysis = get_post_meta($post->ID, '_zenseo_analysis', true);

        if (!$score) {
            echo '<p>' . __('No analysis yet. Click "Analyze" to run SEO analysis.', 'zenseo') . '</p>';
            echo '<button type="button" class="button button-primary" onclick="zenseoAnalyzePost(' . $post->ID . ')">' . __('Analyze Now', 'zenseo') . '</button>';
            return;
        }

        $color = $score >= 80 ? '#10b981' : ($score >= 60 ? '#f59e0b' : '#ef4444');
        
        echo '<div style="text-align: center; padding: 20px;">';
        echo '<div style="font-size: 48px; font-weight: bold; color: ' . $color . ';">' . $score . '</div>';
        echo '<div style="color: #666; margin-bottom: 15px;">/ 100</div>';
        
        if ($analysis) {
            $issues = isset($analysis['issues']) ? $analysis['issues'] : array();
            if (!empty($issues)) {
                echo '<ul style="text-align: left; font-size: 12px;">';
                foreach (array_slice($issues, 0, 3) as $issue) {
                    echo '<li style="color: #ef4444;">• ' . esc_html($issue) . '</li>';
                }
                echo '</ul>';
            }
        }
        
        echo '<button type="button" class="button" onclick="zenseoAnalyzePost(' . $post->ID . ')">' . __('Re-analyze', 'zenseo') . '</button>';
        echo '</div>';
    }

    /**
     * Auto analyze on save
     */
    public function auto_analyze_on_save($post_id, $post) {
        if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
            return;
        }

        if (!current_user_can('edit_post', $post_id)) {
            return;
        }

        // Skip if auto-analyze is enabled
        $settings = get_option('zenseo_settings', array());
        if (isset($settings['auto_analyze']) && $settings['auto_analyze']) {
            $analyzer = new ZenSEO_Analyzer();
            $analyzer->analyze_post($post_id);
        }
    }

    /**
     * Create database tables
     */
    private function create_tables() {
        global $wpdb;

        $charset_collate = $wpdb->get_charset_collate();

        // Tasks table
        $table_name = $wpdb->prefix . 'zenseo_tasks';
        $sql = "CREATE TABLE IF NOT EXISTS $table_name (
            id bigint(20) NOT NULL AUTO_INCREMENT,
            post_id bigint(20) DEFAULT 0,
            title varchar(255) NOT NULL,
            description text,
            category varchar(50) DEFAULT '',
            priority varchar(20) DEFAULT 'medium',
            status varchar(20) DEFAULT 'pending',
            instructions text,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            completed_at datetime DEFAULT NULL,
            PRIMARY KEY  (id),
            KEY post_id (post_id),
            KEY status (status)
        ) $charset_collate;";

        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql);

        // Keywords table
        $table_name = $wpdb->prefix . 'zenseo_keywords';
        $sql = "CREATE TABLE IF NOT EXISTS $table_name (
            id bigint(20) NOT NULL AUTO_INCREMENT,
            keyword varchar(255) NOT NULL,
            volume int(11) DEFAULT 0,
            difficulty int(11) DEFAULT 0,
            intent varchar(50) DEFAULT 'informational',
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY  (id),
            KEY keyword (keyword)
        ) $charset_collate;";

        dbDelta($sql);
    }

    /**
     * Set default options
     */
    private function set_default_options() {
        $defaults = array(
            'ai_provider' => 'openai',
            'openai_key' => '',
            'openrouter_key' => '',
            'anthropic_key' => '',
            'semrush_key' => '',
            'target_keyword' => '',
            'auto_analyze' => true,
            'content_type' => 'blog',
            'primary_language' => 'en',
            'country' => 'us',
        );

        if (!get_option('zenseo_settings')) {
            update_option('zenseo_settings', $defaults);
        }
    }

    /**
     * Register post types
     */
    private function register_post_types() {
        // Register SEO Reports post type
        register_post_type('zenseo_report', array(
            'labels' => array(
                'name' => __('SEO Reports', 'zenseo'),
                'singular_name' => __('Report', 'zenseo'),
            ),
            'public' => false,
            'show_ui' => false,
            'supports' => array('title', 'editor'),
            'menu_icon' => 'dashicons-chart-bar',
        ));
    }

    /**
     * Render dashboard
     */
    public function render_dashboard() {
        include ZENSEO_PLUGIN_DIR . 'templates/dashboard.php';
    }

    /**
     * Render settings
     */
    public function render_settings() {
        include ZENSEO_PLUGIN_DIR . 'templates/settings.php';
    }

    /**
     * Render keywords
     */
    public function render_keywords() {
        include ZENSEO_PLUGIN_DIR . 'templates/keywords.php';
    }

    /**
     * AJAX: Analyze URL
     */
    public function ajax_analyze() {
        check_ajax_referer('zenseo_nonce', 'nonce');

        $url = isset($_POST['url']) ? esc_url_raw($_POST['url']) : '';
        $keyword = isset($_POST['keyword']) ? sanitize_text_field($_POST['keyword']) : '';

        if (empty($url)) {
            wp_send_json_error(array('message' => 'URL is required'));
        }

        $analyzer = new ZenSEO_Analyzer();
        $result = $analyzer->analyze_url($url, $keyword);

        wp_send_json_success($result);
    }

    /**
     * AJAX: Optimize content
     */
    public function ajax_optimize() {
        check_ajax_referer('zenseo_nonce', 'nonce');

        $post_id = isset($_POST['post_id']) ? intval($_POST['post_id']) : 0;
        $keyword = isset($_POST['keyword']) ? sanitize_text_field($_POST['keyword']) : '';

        if (!$post_id) {
            wp_send_json_error(array('message' => 'Post ID is required'));
        }

        $analyzer = new ZenSEO_Analyzer();
        $result = $analyzer->optimize_post($post_id, $keyword);

        wp_send_json_success($result);
    }

    /**
     * AJAX: Generate content
     */
    public function ajax_generate_content() {
        check_ajax_referer('zenseo_nonce', 'nonce');

        $topic = isset($_POST['topic']) ? sanitize_text_field($_POST['topic']) : '';
        $type = isset($_POST['type']) ? sanitize_text_field($_POST['type']) : 'blog';

        if (empty($topic)) {
            wp_send_json_error(array('message' => 'Topic is required'));
        }

        $ai = new ZenSEO_AI();
        $result = $ai->generate_content($topic, $type);

        wp_send_json_success($result);
    }

    /**
     * AJAX: Save settings
     */
    public function ajax_save_settings() {
        check_ajax_referer('zenseo_nonce', 'nonce');

        $settings = isset($_POST['settings']) ? $_POST['settings'] : array();

        update_option('zenseo_settings', $settings);

        wp_send_json_success(array('message' => 'Settings saved'));
    }

    /**
     * AJAX: Get tasks
     */
    public function ajax_get_tasks() {
        check_ajax_referer('zenseo_nonce', 'nonce');

        global $wpdb;
        $table = $wpdb->prefix . 'zenseo_tasks';
        
        $tasks = $wpdb->get_results("SELECT * FROM $table ORDER BY priority DESC, created_at DESC LIMIT 50");

        wp_send_json_success($tasks);
    }

    /**
     * AJAX: Complete task
     */
    public function ajax_complete_task() {
        check_ajax_referer('zenseo_nonce', 'nonce');

        $task_id = isset($_POST['task_id']) ? intval($_POST['task_id']) : 0;

        if (!$task_id) {
            wp_send_json_error(array('message' => 'Task ID is required'));
        }

        global $wpdb;
        $table = $wpdb->prefix . 'zenseo_tasks';

        $wpdb->update(
            $table,
            array('status' => 'completed', 'completed_at' => current_time('mysql')),
            array('id' => $task_id)
        );

        wp_send_json_success(array('message' => 'Task completed'));
    }
}

/**
 * Returns the main instance of ZenSEO
 */
function ZenSEO() {
    return ZenSEO_Engine::instance();
}

// Initialize
ZenSEO();