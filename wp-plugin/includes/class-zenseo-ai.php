<?php
/**
 * AI Content Generation & Optimization Class
 * Supports both Internal (PHP direct) and External (Python service) modes
 */

class ZenSEO_AI {

    /**
     * Settings
     */
    private function get_settings() {
        return get_option('zenseo_settings', array());
    }

    /**
     * Determine which mode to use based on settings
     */
    private function get_mode() {
        $settings = $this->get_settings();
        
        // If external service URL is configured, use external mode
        if (!empty($settings['external_service_url'])) {
            return 'external';
        }
        
        // If external mode selected but no URL, fallback to internal
        if (isset($settings['ai_mode']) && $settings['ai_mode'] === 'external') {
            // Check if external service is reachable
            if ($this->test_external_service($settings['external_service_url'] ?? '')) {
                return 'external';
            }
        }
        
        return 'internal';
    }

    /**
     * Test if external service is reachable
     */
    private function test_external_service($url) {
        $response = wp_remote_get($url . '/health', array(
            'timeout' => 5
        ));
        return !is_wp_error($response) && wp_remote_retrieve_response_code($response) === 200;
    }

    /**
     * Main AI call - routes to internal or external
     */
    private function call_ai($prompt, $max_tokens = 2000) {
        $mode = $this->get_mode();
        
        if ($mode === 'external') {
            return $this->call_external_service($prompt, $max_tokens);
        }
        
        // Internal mode - direct API calls
        $settings = $this->get_settings();
        $provider = $settings['ai_provider'] ?? 'openai';
        
        switch ($provider) {
            case 'openai':
                return $this->call_openai($prompt, $max_tokens, $settings['openai_key'] ?? '');
            case 'openrouter':
                return $this->call_openrouter($prompt, $max_tokens, $settings['openrouter_key'] ?? '');
            case 'anthropic':
                return $this->call_anthropic($prompt, $max_tokens, $settings['anthropic_key'] ?? '');
            default:
                return $this->call_openai($prompt, $max_tokens, $settings['openai_key'] ?? '');
        }
    }

    /**
     * Call external Python/Node.js service
     */
    private function call_external_service($prompt, $max_tokens = 2000) {
        $settings = $this->get_settings();
        $url = $settings['external_service_url'] . '/api/chat';
        
        $response = wp_remote_post($url, array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'Authorization' => 'Bearer ' . ($settings['external_api_key'] ?? '')
            ),
            'body' => json_encode(array(
                'prompt' => $prompt,
                'max_tokens' => $max_tokens,
                'model' => $settings['external_model'] ?? 'gpt-4'
            )),
            'timeout' => 60
        ));

        if (is_wp_error($response)) {
            // Fallback to internal on error
            return $this->call_ai($prompt, $max_tokens);
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        
        return $body['response'] ?? $body['content'] ?? $body['choices'][0]['message']['content'] ?? null;
    }

    /**
     * Full analysis via external service (for complex SEO analysis)
     */
    public function analyze_external($content, $keyword) {
        $settings = $this->get_settings();
        $url = $settings['external_service_url'] . '/api/analyze';
        
        $response = wp_remote_post($url, array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'Authorization' => 'Bearer ' . ($settings['external_api_key'] ?? '')
            ),
            'body' => json_encode(array(
                'content' => $content,
                'keyword' => $keyword,
                'url' => get_permalink()
            )),
            'timeout' => 90
        ));

        if (is_wp_error($response)) {
            return null;
        }

        return json_decode(wp_remote_retrieve_body($response), true);
    }

    /**
     * Bulk keyword research via external service
     */
    public function keyword_research_external($seed_keyword) {
        $settings = $this->get_settings();
        $url = $settings['external_service_url'] . '/api/keyword-research';
        
        $response = wp_remote_post($url, array(
            'headers' => array(
                'Content-Type' => 'application/json',
            ),
            'body' => json_encode(array(
                'keyword' => $seed_keyword,
                'limit' => 20
            )),
            'timeout' => 30
        ));

        if (is_wp_error($response)) {
            return null;
        }

        return json_decode(wp_remote_retrieve_body($response), true);
    }

    /**
     * Call OpenAI API
     */
    private function call_openai($prompt, $max_tokens, $api_key) {
        if (empty($api_key)) {
            return array('error' => 'OpenAI API key not configured');
        }

        $response = wp_remote_post('https://api.openai.com/v1/chat/completions', array(
            'headers' => array(
                'Authorization' => 'Bearer ' . $api_key,
                'Content-Type' => 'application/json',
            ),
            'body' => json_encode(array(
                'model' => 'gpt-4-turbo',
                'messages' => array(
                    array('role' => 'system', 'content' => 'You are ZenSEO, an expert SEO content optimizer and writer. Generate SEO-optimized content that ranks. Be concise, actionable, and follow SEO best practices.'),
                    array('role' => 'user', 'content' => $prompt)
                ),
                'temperature' => 0.7,
                'max_tokens' => $max_tokens,
            )),
            'timeout' => 60
        ));

        if (is_wp_error($response)) {
            return array('error' => $response->get_error_message());
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        
        if (isset($body['choices'][0]['message']['content'])) {
            return $body['choices'][0]['message']['content'];
        }

        return array('error' => 'No response from AI');
    }

    /**
     * Call OpenRouter API
     */
    private function call_openrouter($prompt, $max_tokens, $api_key) {
        if (empty($api_key)) {
            return array('error' => 'OpenRouter API key not configured');
        }

        $response = wp_remote_post('https://openrouter.ai/api/v1/chat/completions', array(
            'headers' => array(
                'Authorization' => 'Bearer ' . $api_key,
                'Content-Type' => 'application/json',
                'HTTP-Referer' => get_site_url(),
                'X-Title' => 'ZenSEO WordPress'
            ),
            'body' => json_encode(array(
                'model' => 'openai/gpt-4-turbo',
                'messages' => array(
                    array('role' => 'system', 'content' => 'You are ZenSEO, an expert SEO content optimizer and writer.'),
                    array('role' => 'user', 'content' => $prompt)
                ),
                'temperature' => 0.7,
                'max_tokens' => $max_tokens,
            )),
            'timeout' => 60
        ));

        if (is_wp_error($response)) {
            return array('error' => $response->get_error_message());
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        
        if (isset($body['choices'][0]['message']['content'])) {
            return $body['choices'][0]['message']['content'];
        }

        return array('error' => 'No response from OpenRouter');
    }

    /**
     * Call Anthropic API
     */
    private function call_anthropic($prompt, $max_tokens, $api_key) {
        if (empty($api_key)) {
            return array('error' => 'Anthropic API key not configured');
        }

        $response = wp_remote_post('https://api.anthropic.com/v1/messages', array(
            'headers' => array(
                'x-api-key' => $api_key,
                'anthropic-version' => '2023-06-01',
                'Content-Type' => 'application/json',
            ),
            'body' => json_encode(array(
                'model' => 'claude-3-opus-20240229',
                'messages' => array(
                    array('role' => 'user', 'content' => $prompt)
                ),
                'max_tokens' => $max_tokens,
                'temperature' => 0.7,
            )),
            'timeout' => 60
        ));

        if (is_wp_error($response)) {
            return array('error' => $response->get_error_message());
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        
        if (isset($body['content'][0]['text'])) {
            return $body['content'][0]['text'];
        }

        return array('error' => 'No response from Anthropic');
    }

    /**
     * Optimize title
     */
    public function optimize_title($title, $keyword, $analysis) {
        $prompt = "Optimize this title tag for SEO:\n\nCurrent title: $title\nPrimary keyword: $keyword\nCurrent score: {$analysis['score']}/100\n\nRequirements:\n- Include keyword naturally\n- Keep 50-60 characters\n- Make compelling for clicks\n\nRespond with ONLY the optimized title, nothing else.";

        $result = $this->call_ai($prompt, 100);
        
        if (is_array($result) && isset($result['error'])) {
            // Fallback
            if (!empty($keyword) && stripos($title, $keyword) === false) {
                return $keyword . ' - ' . $title;
            }
            return $title;
        }

        return trim($result);
    }

    /**
     * Optimize meta description
     */
    public function optimize_meta_description($meta, $keyword, $analysis) {
        $prompt = "Optimize this meta description for SEO:\n\nCurrent: $meta\nPrimary keyword: $keyword\nCurrent score: {$analysis['score']}/100\n\nRequirements:\n- Include keyword naturally\n- 150-160 characters\n- Include CTA\n\nRespond with ONLY the optimized meta description, nothing else.";

        $result = $this->call_ai($prompt, 200);
        
        if (is_array($result) && isset($result['error'])) {
            // Fallback
            if (!empty($keyword) && stripos($meta, $keyword) === false) {
                return substr($meta, 0, 130) . " Learn more about $keyword.";
            }
            return $meta;
        }

        return trim($result);
    }

    /**
     * Improve content
     */
    public function improve_content($content, $keyword, $analysis) {
        $prompt = "Improve this content for SEO. Current issues: " . implode(', ', $analysis['issues'] ?? array()) . "\n\nContent:\n" . substr($content, 0, 2000) . "\n\nPrimary keyword: $keyword\n\nTasks:\n1. Add keyword naturally throughout\n2. Improve readability (shorter sentences, bullet points)\n3. Add subheadings with keywords\n4. Keep original meaning and length\n\nRespond with improved content only.";

        $result = $this->call_ai($prompt, 3000);
        
        if (is_array($result) && isset($result['error'])) {
            return array('fallback' => true, 'message' => 'Could not optimize with AI. Try improving manually.');
        }

        return array(
            'improved_content' => $result,
            'changes' => 'Content optimized with AI improvements for SEO'
        );
    }

    /**
     * Generate new content
     */
    public function generate_content($topic, $type = 'blog') {
        $settings = $this->get_settings();
        $keyword = $settings['target_keyword'] ?? $topic;
        $lang = $settings['primary_language'] ?? 'en';

        $types = array(
            'blog' => "comprehensive blog post",
            'product' => "product page",
            'landing' => "landing page",
            'service' => "service page",
            'faq' => "FAQ page with Q&A"
        );

        $prompt = "Generate a fully SEO-optimized {$types[$type]} about \"$topic\".\n\nPrimary keyword: $keyword\nLanguage: $lang\n\nInclude:\n1. SEO title (50-60 chars)\n2. Meta description (150-160 chars)\n3. Compelling headline (H1)\n4. H2/H3 subheadings\n5. 800-1500 words of valuable content\n6. FAQ section if appropriate\n\nFormat as:\nTITLE: [title]\nMETA: [meta description]\nCONTENT: [full content with headings]\n\nMake it comprehensive, helpful, and naturally optimized for the keyword.";

        $result = $this->call_ai($prompt, 4000);
        
        if (is_array($result) && isset($result['error'])) {
            return $result;
        }

        // Parse response
        $title = '';
        $meta = '';
        $content = '';

        if (preg_match('/TITLE:\s*(.+?)(?=\nMETA:|$)/s', $result, $matches)) {
            $title = trim($matches[1]);
        }
        if (preg_match('/META:\s*(.+?)(?=\nCONTENT:|$)/s', $result, $matches)) {
            $meta = trim($matches[1]);
        }
        if (preg_match('/CONTENT:\s*(.+)/s', $result, $matches)) {
            $content = trim($matches[1]);
        }

        // Generate schema
        $schema_class = new ZenSEO_Schema();
        $schema = $schema_class->generate(array(
            'type' => $type === 'blog' ? 'Article' : 'WebPage',
            'name' => $title,
            'description' => $meta,
            'url' => get_site_url(),
        ));

        return array(
            'title' => $title ?: $topic,
            'meta_description' => $meta ?: "Learn about $topic - comprehensive guide",
            'content' => $content ?: $result,
            'schema' => $schema,
            'type' => $type
        );
    }

    /**
     * Generate meta tags for URL
     */
    public function generate_meta_tags($url) {
        // Fetch URL content
        $response = wp_remote_get($url, array('timeout' => 30));
        
        if (is_wp_error($response)) {
            return array('error' => 'Could not fetch URL');
        }

        $html = wp_remote_retrieve_body($response);
        
        // Extract title and content
        preg_match('/<title>([^<]+)<\/title>/i', $html, $title_match);
        preg_match('/<body[^>]*>(.*)<\/body>/is', $html, $body_match);
        
        $title = $title_match[1] ?? '';
        $content = strip_tags($body_match[1] ?? '');
        $content = substr($content, 0, 2000);

        $prompt = "Generate SEO meta tags for this page:\n\nTitle: $title\nContent preview: $content\n\nProvide:\n- Optimized title (50-60 chars)\n- Meta description (150-160 chars)\n- Primary keyword\n\nFormat:\nTITLE: [title]\nMETA: [description]\nKEYWORD: [keyword]";

        $result = $this->call_ai($prompt, 500);

        if (is_array($result) && isset($result['error'])) {
            return $result;
        }

        $response = array();
        if (preg_match('/TITLE:\s*(.+)/i', $result, $m)) $response['title'] = trim($m[1]);
        if (preg_match('/META:\s*(.+)/i', $result, $m)) $response['meta_description'] = trim($m[1]);
        if (preg_match('/KEYWORD:\s*(.+)/i', $result, $m)) $response['keyword'] = trim($m[1]);

        return $response;
    }

    /**
     * Improve readability
     */
    public function improve_readability($content) {
        $prompt = "Rewrite this content to be more readable (8th grade level). Keep the same meaning but use:\n- Shorter sentences (under 20 words)\n- Simpler words\n- Bullet points where appropriate\n- More paragraphs\n\nContent:\n$content\n\nRespond with improved content only.";

        $result = $this->call_ai($prompt, 3000);
        
        return $result ?: $content;
    }

    /**
     * Create content brief
     */
    public function create_brief($keyword, $competitor_urls = array()) {
        $prompt = "Create a comprehensive SEO content brief for keyword: $keyword\n\n";

        if (!empty($competitor_urls)) {
            $prompt .= "Analyze these top ranking pages:\n" . implode("\n", $competitor_urls) . "\n\n";
        }

        $prompt .= "Include:\n1. Target keyword and variations\n2. Recommended content structure\n3. Word count (1500-3000)\n4. Key sections to cover\n5. Questions to answer (PAA)\n6. Internal linking suggestions\n7. Schema type to implement\n\nFormat as actionable brief.";

        $result = $this->call_ai($prompt, 2000);
        
        return $result ?: "Could not generate brief. Try adding more details.";
    }
}