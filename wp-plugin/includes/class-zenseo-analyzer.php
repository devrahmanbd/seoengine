<?php
/**
 * SEO Analyzer Class - Performs all Yoast/RankMath style analysis
 */

class ZenSEO_Analyzer {

    /**
     * Analyze a URL
     */
    public function analyze_url($url, $keyword = '') {
        $settings = get_option('zenseo_settings', array());
        $keyword = $keyword ?: ($settings['target_keyword'] ?? '');

        // Fetch content
        $response = wp_remote_get($url, array(
            'timeout' => 30,
            'user-agent' => 'Mozilla/5.0 (compatible; ZenSEO/1.0)'
        ));

        if (is_wp_error($response)) {
            return array('error' => $response->get_error_message());
        }

        $html = wp_remote_retrieve_body($response);
        return $this->analyze_html($html, $url, $keyword);
    }

    /**
     * Analyze HTML content
     */
    public function analyze_html($html, $url = '', $keyword = '') {
        libxml_use_internal_errors(true);
        $doc = new DOMDocument();
        @$doc->loadHTML($html);
        libxml_clear_errors();

        $xpath = new DOMXPath($doc);

        // Extract elements
        $title = $this->get_element_text($xpath, '//title');
        $meta_desc = $this->get_meta_content($xpath, 'description');
        $h1s = $xpath->query('//h1');
        $h2s = $xpath->query('//h2');
        $imgs = $xpath->query('//img');
        $links = $xpath->query('//a[@href]');
        $body = $xpath->query('//body')->item(0);
        $body_text = $body ? $body->textContent : '';

        // Analyze
        $analysis = array(
            'title' => $this->analyze_title($title, $keyword),
            'meta_description' => $this->analyze_meta_description($meta_desc, $keyword),
            'headings' => $this->analyze_headings($xpath, $keyword),
            'content' => $this->analyze_content($body_text, $keyword),
            'images' => $this->analyze_images($imgs, $keyword),
            'links' => $this->analyze_links($links, $url),
            'readability' => $this->analyze_readability($body_text),
            'schema' => $this->detect_schema($html),
        );

        // Calculate overall score
        $analysis['overall_score'] = $this->calculate_score($analysis);
        $analysis['issues'] = $this->get_issues($analysis);
        $analysis['suggestions'] = $this->get_suggestions($analysis);

        return $analysis;
    }

    /**
     * Analyze a WordPress post
     */
    public function analyze_post($post_id) {
        $post = get_post($post_id);
        if (!$post) {
            return array('error' => 'Post not found');
        }

        $settings = get_option('zenseo_settings', array());
        $keyword = get_post_meta($post_id, '_zenseo_target_keyword', true) ?: ($settings['target_keyword'] ?? '');

        $content = apply_filters('the_content', $post->post_content);
        $title = $post->post_title;
        $meta_desc = get_post_meta($post_id, '_yoast_wpseo_metadesc', true) ?: get_post_meta($post_id, '_rank_math_description', true) ?: '';

        // Analyze
        $analysis = $this->analyze_post_content($title, $meta_desc, $content, $keyword);
        $analysis['overall_score'] = $this->calculate_score($analysis);
        $analysis['issues'] = $this->get_issues($analysis);
        $analysis['suggestions'] = $this->get_suggestions($analysis);

        // Save
        update_post_meta($post_id, '_zenseo_score', $analysis['overall_score']);
        update_post_meta($post_id, '_zenseo_analysis', $analysis);

        // Generate tasks
        $this->generate_tasks($post_id, $analysis);

        return $analysis;
    }

    /**
     * Analyze post content
     */
    public function analyze_post_content($title, $meta_desc, $content, $keyword) {
        // Strip shortcodes and HTML
        $content = strip_shortcodes($content);
        $content = wp_strip_all_tags($content, true);
        
        // Get headings from content
        preg_match_all('/<h([1-6])[^>]*>(.*?)<\/h\1>/i', $content, $headings_matches);
        $headings = array();
        for ($i = 0; $i < count($headings_matches[0]); $i++) {
            $headings[] = array(
                'level' => intval($headings_matches[1][$i]),
                'text' => strip_tags($headings_matches[2][$i])
            );
        }

        // Get images
        preg_match_all('/<img[^>]+>/i', $content, $img_matches);
        $images = array();
        foreach ($img_matches[0] as $img) {
            preg_match('/src=["\']([^"\']+)["\']/i', $img, $src);
            preg_match('/alt=["\']([^"\']*)["\']/i', $img, $alt);
            $images[] = array(
                'src' => $src[1] ?? '',
                'alt' => $alt[1] ?? ''
            );
        }

        return array(
            'title' => $this->analyze_title($title, $keyword),
            'meta_description' => $this->analyze_meta_description($meta_desc, $keyword),
            'headings' => $this->analyze_headings_array($headings, $keyword),
            'content' => $this->analyze_content($content, $keyword),
            'images' => $this->analyze_images_array($images, $keyword),
            'links' => array('internal' => 0, 'external' => 0),
            'readability' => $this->analyze_readability($content),
            'schema' => $this->detect_schema($content),
        );
    }

    /**
     * Optimize a post
     */
    public function optimize_post($post_id, $keyword = '') {
        $post = get_post($post_id);
        if (!$post) {
            return array('error' => 'Post not found');
        }

        $settings = get_option('zenseo_settings', array());
        $keyword = $keyword ?: ($settings['target_keyword'] ?? '');

        $analysis = $this->analyze_post($post_id);
        $ai = new ZenSEO_AI();

        // Get optimized title
        $optimized_title = $ai->optimize_title($post->post_title, $keyword, $analysis['title']);

        // Get optimized meta
        $meta_desc = get_post_meta($post_id, '_yoast_wpseo_metadesc', true) ?: get_post_meta($post_id, '_rank_math_description', true) ?: '';
        $optimized_meta = $ai->optimize_meta_description($meta_desc, $keyword, $analysis['meta_description']);

        // Get improved content
        $content = apply_filters('the_content', $post->post_content);
        $improved_content = $ai->improve_content($content, $keyword, $analysis);

        return array(
            'original_title' => $post->post_title,
            'optimized_title' => $optimized_title,
            'original_meta' => $meta_desc,
            'optimized_meta' => $optimized_meta,
            'content_improvements' => $improved_content,
            'score_before' => $analysis['overall_score'],
            'score_after' => min(100, $analysis['overall_score'] + 25),
        );
    }

    /**
     * Analyze title tag
     */
    private function analyze_title($title, $keyword) {
        $score = 50;
        $issues = array();
        $suggestions = array();

        if (empty($title)) {
            $issues[] = 'Missing title tag';
            $score -= 30;
        } else {
            $length = strlen($title);
            
            if ($length < 30) {
                $issues[] = 'Title too short (under 30 characters)';
                $score -= 10;
            } elseif ($length > 60) {
                $issues[] = 'Title too long (over 60 characters)';
                $score -= 10;
            }

            if (!empty($keyword) && stripos($title, $keyword) !== false) {
                $score += 20;
                $suggestions[] = 'Great: Primary keyword in title';
            } elseif (!empty($keyword)) {
                $issues[] = 'Primary keyword not found in title';
                $score -= 15;
            }
        }

        return array(
            'score' => max(0, min(100, $score)),
            'raw' => $title,
            'length' => strlen($title),
            'issues' => $issues,
            'suggestions' => $suggestions
        );
    }

    /**
     * Analyze meta description
     */
    private function analyze_meta_description($meta_desc, $keyword) {
        $score = 50;
        $issues = array();
        $suggestions = array();

        if (empty($meta_desc)) {
            $issues[] = 'Missing meta description';
            $score -= 25;
        } else {
            $length = strlen($meta_desc);
            
            if ($length < 120) {
                $issues[] = 'Meta description too short (under 120 characters)';
                $score -= 10;
            } elseif ($length > 160) {
                $issues[] = 'Meta description too long (over 160 characters)';
                $score -= 10;
            }

            if (!empty($keyword) && stripos($meta_desc, $keyword) !== false) {
                $score += 20;
                $suggestions[] = 'Good: Primary keyword in meta description';
            }
        }

        return array(
            'score' => max(0, min(100, $score)),
            'raw' => $meta_desc,
            'length' => strlen($meta_desc),
            'issues' => $issues,
            'suggestions' => $suggestions
        );
    }

    /**
     * Analyze headings via XPath
     */
    private function analyze_headings($xpath, $keyword) {
        $headings = array();
        $h1s = $xpath->query('//h1');
        $h2s = $xpath->query('//h2');
        $h3s = $xpath->query('//h3');

        $has_h1 = $h1s->length > 0;
        $keyword_in_headings = false;

        foreach (array($h1s, $h2s, $h3s) as $level => $nodes) {
            foreach ($nodes as $node) {
                $text = $node->textContent;
                $has_keyword = !empty($keyword) && stripos($text, $keyword) !== false;
                if ($has_keyword) $keyword_in_headings = true;

                $headings[] = array(
                    'level' => $level + 1,
                    'text' => $text,
                    'has_keyword' => $has_keyword
                );
            }
        }

        $score = 50;
        if (!$has_h1) $score -= 15;
        if ($keyword_in_headings) $score += 20;

        return array(
            'score' => max(0, min(100, $score)),
            'has_h1' => $has_h1,
            'count' => count($headings),
            'keyword_in_headings' => $keyword_in_headings,
            'headings' => array_slice($headings, 0, 10)
        );
    }

    /**
     * Analyze headings from array
     */
    private function analyze_headings_array($headings, $keyword) {
        $has_h1 = false;
        $keyword_in_headings = false;

        foreach ($headings as $h) {
            if ($h['level'] == 1) $has_h1 = true;
            if (!empty($keyword) && stripos($h['text'], $keyword) !== false) {
                $keyword_in_headings = true;
            }
        }

        $score = 50;
        if (!$has_h1) $score -= 15;
        if ($keyword_in_headings) $score += 20;

        return array(
            'score' => max(0, min(100, $score)),
            'has_h1' => $has_h1,
            'count' => count($headings),
            'keyword_in_headings' => $keyword_in_headings,
            'headings' => array_slice($headings, 0, 10)
        );
    }

    /**
     * Analyze content
     */
    private function analyze_content($text, $keyword) {
        $words = str_word_count(strtolower($text), 0, 'àáâãäåæçèéêëìíîï');
        $word_count = $words ?: 1;

        $density = 0;
        if (!empty($keyword) && $word_count > 0) {
            $keyword_count = substr_count(strtolower($text), strtolower($keyword));
            $density = ($keyword_count / $word_count) * 100;
        }

        $score = 50;
        if ($word_count >= 300) $score += 20;
        elseif ($word_count >= 150) $score += 10;
        else $score -= 10;

        if ($density >= 1 && $density <= 2.5) $score += 20;
        elseif ($density > 2.5) $score -= 10;

        return array(
            'score' => max(0, min(100, $score)),
            'word_count' => $word_count,
            'keyword_density' => round($density, 2),
            'has_enough_content' => $word_count >= 300
        );
    }

    /**
     * Analyze images
     */
    private function analyze_images($imgs, $keyword) {
        $total = $imgs->length;
        $with_alt = 0;
        $with_keyword = 0;

        foreach ($imgs as $img) {
            $alt = $img->getAttribute('alt');
            if (!empty($alt)) {
                $with_alt++;
                if (!empty($keyword) && stripos($alt, $keyword) !== false) {
                    $with_keyword++;
                }
            }
        }

        $score = 60;
        if ($total > 0) {
            $score += ($with_alt / $total) * 20;
            if ($with_keyword > 0) $score += 10;
        } else {
            $score -= 20;
        }

        return array(
            'score' => max(0, min(100, $score)),
            'total' => $total,
            'with_alt' => $with_alt,
            'with_keyword' => $with_keyword
        );
    }

    /**
     * Analyze images from array
     */
    private function analyze_images_array($images, $keyword) {
        $total = count($images);
        $with_alt = 0;
        $with_keyword = 0;

        foreach ($images as $img) {
            if (!empty($img['alt'])) {
                $with_alt++;
                if (!empty($keyword) && stripos($img['alt'], $keyword) !== false) {
                    $with_keyword++;
                }
            }
        }

        $score = 60;
        if ($total > 0) {
            $score += ($with_alt / $total) * 20;
            if ($with_keyword > 0) $score += 10;
        } else {
            $score -= 20;
        }

        return array(
            'score' => max(0, min(100, $score)),
            'total' => $total,
            'with_alt' => $with_alt,
            'with_keyword' => $with_keyword
        );
    }

    /**
     * Analyze links
     */
    private function analyze_links($links, $base_url) {
        $internal = 0;
        $external = 0;

        foreach ($links as $link) {
            $href = $link->getAttribute('href');
            if (empty($href) || $href[0] === '#') continue;

            if (strpos($href, $base_url) === 0 || $href[0] === '/') {
                $internal++;
            } else {
                $external++;
            }
        }

        $score = 60;
        if ($internal >= 2) $score += 15;
        if ($external > 0) $score += 10;

        return array(
            'score' => max(0, min(100, $score)),
            'internal' => $internal,
            'external' => $external
        );
    }

    /**
     * Analyze readability
     */
    private function analyze_readability($text) {
        $sentences = preg_split('/[.!?]+/', $text, -1, PREG_SPLIT_NO_EMPTY);
        $sentence_count = count($sentences) ?: 1;

        $words = explode(' ', $text);
        $word_count = count($words) ?: 1;

        $syllables = $this->count_syllables($text);
        
        $avg_sentence_length = $word_count / $sentence_count;
        $flesch = 206.835 - (1.015 * $avg_sentence_length) - (84.6 * ($syllables / $word_count));
        $flesch_kincaid = (0.39 * $avg_sentence_length) + (11.8 * ($syllables / $word_count)) - 15.59;

        $score = 50;
        if ($flesch >= 60) $score += 20;
        elseif ($flesch >= 30) $score += 10;
        else $score -= 10;

        $grade = 'College';
        if ($flesch_kincaid <= 6) $grade = '6th Grade';
        elseif ($flesch_kincaid <= 8) $grade = '8th Grade';
        elseif ($flesch_kincaid <= 10) $grade = '10th Grade';
        elseif ($flesch_kincaid <= 12) $grade = '12th Grade';

        return array(
            'score' => max(0, min(100, $score)),
            'flesch_reading_ease' => round($flesch),
            'flesch_kincaid_grade' => round($flesch_kincaid),
            'grade' => $grade,
            'avg_sentence_length' => round($avg_sentence_length),
            'word_count' => $word_count
        );
    }

    /**
     * Count syllables
     */
    private function count_syllables($text) {
        $text = strtolower(preg_replace('/[^a-z]/', '', $text));
        $words = explode(' ', $text);
        $count = 0;

        foreach ($words as $word) {
            if (strlen($word) <= 3) {
                $count++;
                continue;
            }
            $word = preg_replace('/(?:[^laeiouy]es|ed|[^laeiouy]e)$/', '', $word);
            $word = preg_replace('/^y/', '', $word);
            $matches = preg_match_all('/[aeiouy]{1,2}/', $word);
            $count += $matches ?: 1;
        }

        return $count ?: 1;
    }

    /**
     * Detect schema markup
     */
    private function detect_schema($html) {
        $score = 30;
        $types = array();

        // JSON-LD
        if (preg_match('/<script[^>]*type=["\']application\/ld\+json["\'][^>]*>(.*?)<\/script>/is', $html, $matches)) {
            $score += 40;
            $json = json_decode($matches[1], true);
            if ($json && isset($json['@type'])) {
                $types[] = is_array($json['@type']) ? implode(', ', $json['@type']) : $json['@type'];
            }
        }

        // Microdata
        if (preg_match('/itemtype=["\']https?:\/\/schema\.org\/([^"\']+)["\']/i', $html, $matches)) {
            $score += 20;
            $types[] = $matches[1];
        }

        return array(
            'score' => max(0, min(100, $score)),
            'types' => array_unique($types),
            'has_schema' => $score > 50
        );
    }

    /**
     * Calculate overall score
     */
    private function calculate_score($analysis) {
        $weights = array(
            'title' => 15,
            'meta_description' => 10,
            'headings' => 10,
            'content' => 20,
            'images' => 10,
            'links' => 10,
            'readability' => 15,
            'schema' => 10
        );

        $total = 0;
        foreach ($weights as $key => $weight) {
            $score = isset($analysis[$key]['score']) ? $analysis[$key]['score'] : 0;
            $total += $score * ($weight / 100);
        }

        return round($total);
    }

    /**
     * Get issues
     */
    private function get_issues($analysis) {
        $issues = array();

        foreach ($analysis as $key => $data) {
            if (isset($data['issues'])) {
                foreach ($data['issues'] as $issue) {
                    $issues[] = "[" . ucfirst($key) . "] " . $issue;
                }
            }
        }

        return $issues;
    }

    /**
     * Get suggestions
     */
    private function get_suggestions($analysis) {
        $suggestions = array();

        if ($analysis['title']['score'] < 80) {
            $suggestions[] = 'Optimize your title tag - include primary keyword and keep it 50-60 characters';
        }
        if ($analysis['meta_description']['score'] < 80) {
            $suggestions[] = 'Rewrite meta description with primary keyword and compelling CTA (150-160 chars)';
        }
        if ($analysis['content']['word_count'] < 300) {
            $suggestions[] = 'Add more content - aim for at least 300 words for better rankings';
        }
        if ($analysis['readability']['flesch_reading_ease'] < 30) {
            $suggestions[] = 'Improve readability - use shorter sentences and simpler words';
        }
        if ($analysis['schema']['score'] < 50) {
            $suggestions[] = 'Add schema markup for better featured snippet chances';
        }
        if ($analysis['images']['with_alt'] < $analysis['images']['total']) {
            $suggestions[] = 'Add alt text to all images';
        }
        if ($analysis['links']['internal'] < 2) {
            $suggestions[] = 'Add more internal links to improve site structure';
        }

        return $suggestions;
    }

    /**
     * Generate tasks from analysis
     */
    private function generate_tasks($post_id, $analysis) {
        global $wpdb;
        $table = $wpdb->prefix . 'zenseo_tasks';

        // Clear old tasks for this post
        $wpdb->delete($table, array('post_id' => $post_id), array('%d'));

        // Create new tasks
        foreach ($analysis['issues'] as $issue) {
            $category = 'technical';
            $priority = 'medium';

            if (stripos($issue, 'title') !== false) {
                $category = 'content';
                $priority = 'high';
            } elseif (stripos($issue, 'meta') !== false) {
                $category = 'content';
                $priority = 'high';
            } elseif (stripos($issue, 'readability') !== false) {
                $category = 'content';
            } elseif (stripos($issue, 'schema') !== false) {
                $category = 'technical';
            }

            $wpdb->insert($table, array(
                'post_id' => $post_id,
                'title' => 'Fix: ' . substr($issue, 0, 50),
                'description' => $issue,
                'category' => $category,
                'priority' => $priority,
                'status' => 'pending',
                'instructions' => $this->get_task_instructions($issue)
            ));
        }
    }

    /**
     * Get task instructions
     */
    private function get_task_instructions($issue) {
        $instructions = array(
            'Missing title' => 'Add a descriptive title tag between 50-60 characters with your primary keyword.',
            'Title too short' => 'Expand your title to at least 30 characters while keeping it descriptive.',
            'Title too long' => 'Shorten your title to under 60 characters to avoid truncation in SERPs.',
            'Missing meta' => 'Write a compelling meta description between 150-160 characters.',
            'Meta too short' => 'Expand your meta description to at least 120 characters for better CTR.',
            'Meta too long' => 'Shorten your meta description to under 160 characters to avoid truncation.',
            'keyword not found in title' => 'Include your primary keyword in the title, preferably near the beginning.',
            'keyword not found in meta' => 'Add your primary keyword naturally into the meta description.',
            'Missing H1' => 'Add an H1 heading that includes your primary keyword.',
            'No content' => 'Add substantial content - aim for at least 300-500 words.',
            'readability' => 'Break up long paragraphs, use simpler words, and add subheadings.',
            'alt text' => 'Add descriptive alt text to all images, including primary keyword naturally.',
            'internal links' => 'Add 2-5 internal links to related content on your site.',
            'schema' => 'Add JSON-LD schema markup for your content type (Article, Product, FAQ, etc.).'
        );

        foreach ($instructions as $key => $instruction) {
            if (stripos($issue, $key) !== false) {
                return $instruction;
            }
        }

        return 'Review and fix this SEO issue to improve your ranking.';
    }

    /**
     * Helper: Get element text
     */
    private function get_element_text($xpath, $query) {
        $node = $xpath->query($query)->item(0);
        return $node ? trim($node->textContent) : '';
    }

    /**
     * Helper: Get meta content
     */
    private function get_meta_content($xpath, $name) {
        $nodes = $xpath->query("//meta[@name='$name']/@content");
        return $nodes->length > 0 ? $nodes->item(0)->nodeValue : '';
    }
}