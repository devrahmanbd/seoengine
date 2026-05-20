<?php
/**
 * Keyword Research Class
 */

class ZenSEO_Keyword_Research {

    /**
     * Settings
     */
    private function get_settings() {
        return get_option('zenseo_settings', array());
    }

    /**
     * Get keyword data (using SEMrush or fallback)
     */
    public function get_keyword_data($keyword, $database = 'us') {
        $settings = $this->get_settings();
        $api_key = $settings['semrush_key'] ?? '';

        if (!empty($api_key)) {
            return $this->get_from_semrush($keyword, $api_key, $database);
        }

        // Fallback - estimate based on keyword characteristics
        return $this->estimate_keyword_data($keyword);
    }

    /**
     * Get from SEMrush API
     */
    private function get_from_semrush($keyword, $api_key, $database) {
        // Make API request
        $url = "https://api.semrush.com/?type=phrase_all&key=$apiKey&phrase=" . urlencode($keyword) . "&database=$database";
        
        $response = wp_remote_get($url, array('timeout' => 30));

        if (is_wp_error($response)) {
            return $this->estimate_keyword_data($keyword);
        }

        $data = json_decode(wp_remote_retrieve_body($response), true);

        if (empty($data) || !isset($data[1])) {
            return $this->estimate_keyword_data($keyword);
        }

        $row = $data[1];
        
        return array(
            'keyword' => $keyword,
            'volume' => isset($row[2]) ? (int) str_replace(',', '', $row[2]) : 0,
            'cpc' => isset($row[3]) ? (float) $row[3] : 0,
            'competition' => isset($row[4]) ? (float) $row[4] : 0,
            'difficulty' => isset($row[5]) ? min(100, (int) str_replace(',', '', $row[5]) / 100000) : 50,
            'intent' => $this->determine_intent($keyword),
            'trends' => array_fill(0, 12, 0)
        );
    }

    /**
     * Estimate keyword data
     */
    private function estimate_keyword_data($keyword) {
        $lower = strtolower($keyword);
        
        // Estimate difficulty based on word count and common words
        $difficulty = 50;
        $words = explode(' ', $keyword);
        
        if (count($words) <= 2 && strlen($keyword) < 15) {
            $difficulty = 70; // Short keywords are harder
        } elseif (count($words) >= 4) {
            $difficulty = 30; // Long-tail is easier
        }

        // Common commercial words indicate higher volume
        $commercial = array('best', 'top', 'review', 'buy', 'price', 'cheap');
        foreach ($commercial as $word) {
            if (stripos($lower, $word) !== false) {
                $difficulty += 10;
            }
        }

        $intent = $this->determine_intent($keyword);

        // Estimate volume based on intent
        $volume = 0;
        switch ($intent) {
            case 'transactional':
                $volume = rand(1000, 10000);
                break;
            case 'commercial':
                $volume = rand(500, 5000);
                break;
            case 'informational':
                $volume = rand(100, 2000);
                break;
            default:
                $volume = rand(50, 500);
        }

        return array(
            'keyword' => $keyword,
            'volume' => $volume,
            'cpc' => rand(10, 500) / 100,
            'competition' => $difficulty / 100,
            'difficulty' => $difficulty,
            'intent' => $intent,
            'trends' => array_fill(0, 12, $volume)
        );
    }

    /**
     * Determine search intent
     */
    private function determine_intent($keyword) {
        $lower = strtolower($keyword);

        $transactional = array('buy', 'purchase', 'order', 'price', 'cost', 'shop', 'discount', 'deal', 'coupon', 'cheap', 'rent', 'hire');
        $commercial = array('best', 'top', 'review', 'compare', 'vs', 'alternatives', 'software', 'service', 'tool');
        $navigational = array('login', 'sign in', 'app', 'download', 'official', 'website');

        foreach ($transactional as $word) {
            if (stripos($lower, $word) !== false) return 'transactional';
        }
        foreach ($commercial as $word) {
            if (stripos($lower, $word) !== false) return 'commercial';
        }
        foreach ($navigational as $word) {
            if (stripos($lower, $word) !== false) return 'navigational';
        }

        return 'informational';
    }

    /**
     * Generate keyword suggestions
     */
    public function get_suggestions($seed_keyword, $limit = 20) {
        $suggestions = array();
        
        // Generate variations
        $prefixes = array('best', 'how to', 'what is', 'guide to', 'tips for', 'review', 'vs', 'top');
        $suffixes = array('2024', '2025', 'for beginners', 'examples', 'tutorial', 'pricing', 'free', 'near me');

        $words = explode(' ', $seed_keyword);

        // Prefix variations
        foreach ($prefixes as $prefix) {
            if (stripos($seed_keyword, $prefix) === false) {
                $suggestions[] = "$prefix $seed_keyword";
            }
        }

        // Suffix variations
        foreach ($suffixes as $suffix) {
            if (stripos($seed_keyword, $suffix) === false) {
                $suggestions[] = "$seed_keyword $suffix";
            }
        }

        // Word combinations
        if (count($words) > 1) {
            $suggestions[] = implode(' ', array_slice($words, 0, -1)); // Remove last word
            $suggestions[] = implode(' ', array_slice($words, 1)); // Remove first word
        }

        // Add question format
        $suggestions[] = "what is $seed_keyword";
        $suggestions[] = "how to $seed_keyword";
        $suggestions[] = "why $seed_keyword";

        // Get data for each
        $results = array();
        foreach (array_slice(array_unique($suggestions), 0, $limit) as $keyword) {
            $data = $this->get_keyword_data($keyword);
            $data['score'] = $this->calculate_keyword_score($data);
            $results[] = $data;
        }

        // Sort by score
        usort($results, function($a, $b) {
            return $b['score'] - $a['score'];
        });

        return $results;
    }

    /**
     * Calculate keyword score
     */
    private function calculate_keyword_score($data) {
        $score = 50;

        // Volume score
        if ($data['volume'] > 10000) $score += 20;
        elseif ($data['volume'] > 1000) $score += 10;
        elseif ($data['volume'] > 100) $score += 5;

        // Difficulty score (inverse)
        if ($data['difficulty'] < 30) $score += 15;
        elseif ($data['difficulty'] < 50) $score += 10;
        elseif ($data['difficulty'] > 70) $score -= 10;

        // Intent score
        if ($data['intent'] === 'transactional') $score += 10;
        elseif ($data['intent'] === 'commercial') $score += 5;

        return max(0, min(100, $score));
    }

    /**
     * Extract keywords from content
     */
    public function extract_from_content($content, $limit = 20) {
        // Remove HTML
        $content = strip_tags($content);
        $content = strtolower($content);

        // Remove common words
        $stop_words = array('the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'this', 'that', 'these', 'those', 'it', 'its');
        
        $words = preg_split('/[^a-z]+/', $content);
        $word_count = array();

        foreach ($words as $word) {
            if (strlen($word) > 3 && !in_array($word, $stop_words)) {
                $word_count[$word] = ($word_count[$word] ?? 0) + 1;
            }
        }

        // Sort by frequency
        arsort($word_count);

        // Get top keywords with data
        $keywords = array();
        foreach (array_slice(array_keys($word_count), 0, $limit) as $keyword) {
            $data = $this->get_keyword_data($keyword);
            $data['occurrences'] = $word_count[$keyword];
            $data['score'] = $this->calculate_keyword_score($data);
            $keywords[] = $data;
        }

        return $keywords;
    }

    /**
     * Cluster keywords
     */
    public function cluster_keywords($keywords) {
        $clusters = array();

        foreach ($keywords as $kw) {
            $added = false;
            
            foreach ($clusters as &$cluster) {
                // Check if keywords share words
                $words1 = explode(' ', $kw['keyword']);
                $words2 = explode(' ', $cluster['primary']);
                
                $overlap = array_intersect($words1, $words2);
                
                if (count($overlap) >= min(count($words1), count($words2)) * 0.5) {
                    $cluster['keywords'][] = $kw['keyword'];
                    $cluster['volume'] += $kw['volume'];
                    $added = true;
                    break;
                }
            }

            if (!$added) {
                $clusters[] = array(
                    'primary' => $kw['keyword'],
                    'keywords' => array($kw['keyword']),
                    'volume' => $kw['volume'],
                    'difficulty' => $kw['difficulty']
                );
            }
        }

        // Sort by volume
        usort($clusters, function($a, $b) {
            return $b['volume'] - $a['volume'];
        });

        return $clusters;
    }
}