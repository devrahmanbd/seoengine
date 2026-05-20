<?php
/**
 * Schema Generator Class
 */

class ZenSEO_Schema {

    /**
     * Generate schema
     */
    public function generate($options) {
        $type = $options['type'] ?? 'Article';
        
        $schema = array(
            '@context' => 'https://schema.org',
            '@type' => $type
        );

        if (!empty($options['name'])) {
            $schema['name'] = $options['name'];
        }
        if (!empty($options['description'])) {
            $schema['description'] = $options['description'];
        }
        if (!empty($options['url'])) {
            $schema['url'] = $options['url'];
        }
        if (!empty($options['image'])) {
            $schema['image'] = $options['image'];
        }
        
        // Article specific
        if ($type === 'Article' || $type === 'BlogPosting') {
            $schema['headline'] = $options['name'] ?? '';
            $schema['articleSection'] = $options['category'] ?? 'SEO';
            $schema['author'] = array(
                '@type' => 'Organization',
                'name' => get_bloginfo('name')
            );
            $schema['publisher'] = array(
                '@type' => 'Organization',
                'name' => get_bloginfo('name'),
                'logo' => array(
                    '@type' => 'ImageObject',
                    'url' => get_site_icon_url()
                )
            );
            $schema['datePublished'] = $options['published'] ?? current_time('c');
            $schema['dateModified'] = $options['modified'] ?? current_time('c');
        }

        // Product specific
        if ($type === 'Product') {
            $schema['offers'] = array(
                '@type' => 'Offer',
                'price' => $options['price'] ?? '0',
                'priceCurrency' => $options['currency'] ?? 'USD',
                'availability' => $options['availability'] ?? 'https://schema.org/InStock'
            );
            if (!empty($options['brand'])) {
                $schema['brand'] = array('@type' => 'Brand', 'name' => $options['brand']);
            }
            if (!empty($options['sku'])) {
                $schema['sku'] = $options['sku'];
            }
            if (!empty($options['rating'])) {
                $schema['aggregateRating'] = array(
                    '@type' => 'AggregateRating',
                    'ratingValue' => $options['rating'],
                    'reviewCount' => $options['review_count'] ?? 0
                );
            }
        }

        // FAQ specific
        if ($type === 'FAQPage' && !empty($options['questions'])) {
            $schema['mainEntity'] = array();
            foreach ($options['questions'] as $q) {
                $schema['mainEntity'][] = array(
                    '@type' => 'Question',
                    'name' => $q['question'],
                    'acceptedAnswer' => array(
                        '@type' => 'Answer',
                        'text' => $q['answer']
                    )
                );
            }
        }

        // Local Business
        if ($type === 'LocalBusiness') {
            $schema['address'] = array(
                '@type' => 'PostalAddress',
                'streetAddress' => $options['street'] ?? '',
                'addressLocality' => $options['city'] ?? '',
                'addressRegion' => $options['region'] ?? '',
                'postalCode' => $options['postal'] ?? '',
                'addressCountry' => $options['country'] ?? 'US'
            );
            if (!empty($options['phone'])) {
                $schema['telephone'] = $options['phone'];
            }
            if (!empty($options['price_range'])) {
                $schema['priceRange'] = $options['price_range'];
            }
            if (!empty($options['hours'])) {
                $schema['openingHoursSpecification'] = $options['hours'];
            }
        }

        return json_encode($schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    }

    /**
     * Generate breadcrumbs
     */
    public function generate_breadcrumb($items) {
        $schema = array(
            '@context' => 'https://schema.org',
            '@type' => 'BreadcrumbList',
            'itemListElement' => array()
        );

        foreach ($items as $index => $item) {
            $schema['itemListElement'][] = array(
                '@type' => 'ListItem',
                'position' => $index + 1,
                'name' => $item['name'],
                'item' => $item['url']
            );
        }

        return json_encode($schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    }

    /**
     * Generate organization schema
     */
    public function generate_organization() {
        $schema = array(
            '@context' => 'https://schema.org',
            '@type' => 'Organization',
            'name' => get_bloginfo('name'),
            'url' => get_site_url(),
            'description' => get_bloginfo('description'),
            'logo' => get_site_icon_url(),
            'sameAs' => $this->get_social_links()
        );

        return json_encode($schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    }

    /**
     * Get social links
     */
    private function get_social_links() {
        $links = array();
        
        // Get from options
        $social = get_option('zenseo_social_links', array());
        
        if (!empty($social['facebook'])) $links[] = $social['facebook'];
        if (!empty($social['twitter'])) $links[] = $social['twitter'];
        if (!empty($social['linkedin'])) $links[] = $social['linkedin'];
        if (!empty($social['instagram'])) $links[] = $social['instagram'];
        if (!empty($social['youtube'])) $links[] = $social['youtube'];

        return $links;
    }

    /**
     * Auto-generate schema for post
     */
    public function auto_generate_for_post($post_id) {
        $post = get_post($post_id);
        
        $type = 'Article';
        if ($post->post_type === 'product') {
            $type = 'Product';
        } elseif ($post->post_type === 'page') {
            $type = 'WebPage';
        }

        // Check for FAQ
        $content = $post->post_content;
        if (preg_match('/<h[2-3][^>]*>.*?(?:question|faq).*?<\/h[2-3]>/i', $content)) {
            $type = 'FAQPage';
        }

        $options = array(
            'type' => $type,
            'name' => $post->post_title,
            'description' => get_post_meta($post_id, '_yoast_wpseo_metadesc', true) ?: get_post_meta($post_id, '_rank_math_description', true) ?: wp_trim_words($post->post_content, 30),
            'url' => get_permalink($post_id),
            'published' => get_the_date('c', $post_id),
            'modified' => get_the_modified_date('c', $post_id),
        );

        // Add featured image
        if (has_post_thumbnail($post_id)) {
            $image = wp_get_attachment_url(get_post_thumbnail_id($post_id));
            $options['image'] = $image;
        }

        // If FAQ, extract questions
        if ($type === 'FAQPage') {
            preg_match_all('/<h[2-3][^>]*>([^<]+)<\/h[2-3]>/i', $content, $headings);
            preg_match_all('/<h[2-3][^>]*>[^<]+<\/h[2-3]>\s*<p[^>]*>([^<]+)<\/p>/i', $content, $answers);
            
            $questions = array();
            foreach ($headings[1] as $i => $heading) {
                $questions[] = array(
                    'question' => trim($heading),
                    'answer' => isset($answers[1][$i]) ? trim($answers[1][$i]) : ''
                );
            }
            $options['questions'] = $questions;
        }

        return $this->generate($options);
    }
}