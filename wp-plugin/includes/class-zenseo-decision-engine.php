/**
 * Architecture Decision Engine for ZenSEO
 * Determines whether to use Internal (PHP), External (Python/Node), or Hybrid approach
 */

class ZenSEO_Architecture_Decision {

    private $factors = [];

    public function __construct() {
        $this->init_factors();
    }

    private function init_factors() {
        $this->factors = [
            'ai_capability' => [
                'weight' => 0.25,
                'question' => 'How important is advanced AI/NLP?',
                'options' => [
                    'critical' => ['score' => 100, 'recommendation' => 'external'],
                    'important' => ['score' => 70, 'recommendation' => 'hybrid'],
                    'basic' => ['score' => 30, 'recommendation' => 'internal']
                ]
            ],
            'traffic_scale' => [
                'weight' => 0.20,
                'question' => 'Expected monthly site traffic?',
                'options' => [
                    'high' => ['score' => 90, 'recommendation' => 'external'],
                    'medium' => ['score' => 60, 'recommendation' => 'hybrid'],
                    'low' => ['score' => 30, 'recommendation' => 'internal']
                ]
            ],
            'budget' => [
                'weight' => 0.15,
                'question' => 'Monthly budget for hosting/services?',
                'options' => [
                    'free' => ['score' => 100, 'recommendation' => 'internal'],
                    'low' => ['score' => 60, 'recommendation' => 'hybrid'],
                    'medium' => ['score' => 40, 'recommendation' => 'external'],
                    'high' => ['score' => 20, 'recommendation' => 'external']
                ]
            ],
            'technical_skill' => [
                'weight' => 0.15,
                'question' => 'Team technical skill level?',
                'options' => [
                    'beginner' => ['score' => 100, 'recommendation' => 'internal'],
                    'intermediate' => ['score' => 60, 'recommendation' => 'hybrid'],
                    'expert' => ['score' => 30, 'recommendation' => 'external']
                ]
            ],
            'real_time' => [
                'weight' => 0.15,
                'question' => 'Need real-time analysis on save?',
                'options' => [
                    'critical' => ['score' => 90, 'recommendation' => 'hybrid'],
                    'nice_to_have' => ['score' => 50, 'recommendation' => 'external'],
                    'not_needed' => ['score' => 20, 'recommendation' => 'external']
                ]
            ],
            'distribution' => [
                'weight' => 0.10,
                'question' => 'How will you distribute the plugin?',
                'options' => [
                    'wordpress_org' => ['score' => 100, 'recommendation' => 'internal'],
                    'custom' => ['score' => 50, 'recommendation' => 'hybrid'],
                    'saas' => ['score' => 30, 'recommendation' => 'external']
                ]
            ]
        ];
    }

    public function make_decision($answers) {
        $scores = [
            'internal' => 0,
            'external' => 0,
            'hybrid' => 0
        ];

        $total_weight = 0;

        foreach ($answers as $factor => $option) {
            if (!isset($this->factors[$factor])) continue;

            $factor_data = $this->factors[$factor];
            $weight = $factor_data['weight'];
            $option_data = $factor_data['options'][$option] ?? null;

            if (!$option_data) continue;

            $total_weight += $weight;

            // Add weighted scores
            switch ($option_data['recommendation']) {
                case 'internal':
                    $scores['internal'] += $weight * (100 - $option_data['score']);
                    $scores['external'] += $weight * $option_data['score'];
                    break;
                case 'external':
                    $scores['external'] += $weight * (100 - $option_data['score']);
                    $scores['internal'] += $weight * $option_data['score'];
                    break;
                case 'hybrid':
                    $scores['hybrid'] += $weight * 80;
                    break;
            }
        }

        // Normalize
        if ($total_weight > 0) {
            foreach ($scores as $key => $score) {
                $scores[$key] = round(($score / $total_weight) * 100);
            }
        }

        // Determine winner
        arsort($scores);
        $winner = array_key_first($scores);

        return [
            'recommendation' => $winner,
            'scores' => $scores,
            'confidence' => max($scores),
            'reasoning' => $this->get_reasoning($winner, $scores, $answers)
        ];
    }

    private function get_reasoning($winner, $scores, $answers) {
        $reasons = [];

        if ($winner === 'internal') {
            $reasons[] = "✓ WordPress-native - no external dependencies";
            $reasons[] = "✓ Easy distribution via WordPress.org";
            $reasons[] = "✓ Real-time analysis on content save";
            $reasons[] = "✓ No hosting/maintenance for external service";
            $reasons[] = "✗ Limited AI capabilities (no Python libs)";
            $reasons[] = "✗ Slower for complex analysis";
        } elseif ($winner === 'external') {
            $reasons[] = "✓ Full power of Python AI/ML libraries";
            $reasons[] = "✓ Better NLP, semantic analysis";
            $reasons[] = "✓ More scalable for high traffic";
            $reasons[] = "✓ Can use pre-trained SEO models";
            $reasons[] = "✗ Requires external hosting";
            $reasons[] = "✗ Network latency for API calls";
            $reasons[] = "✗ More complex to maintain";
        } else {
            $reasons[] = "✓ Best of both worlds";
            $reasons[] = "✓ Real-time scoring in WP, AI in Python";
            $reasons[] = "✓ Scalable architecture";
            $reasons[] = "✓ Can start internal, migrate to external";
            $reasons[] = "✗ More complex setup";
            $reasons[] = "✗ Requires API key management";
        }

        return $reasons;
    }

    public function get_form_html() {
        $html = '<div class="zenseo-decision-engine">';
        $html .= '<h2>🏗️ Architecture Decision Guide</h2>';
        $html .= '<p>Answer these questions to determine the best architecture for your SEO engine:</p>';
        $html .= '<form id="zenseo-decision-form">';

        foreach ($this->factors as $key => $factor) {
            $html .= '<div class="decision-factor">';
            $html .= '<label>' . $factor['question'] . '</label>';
            $html .= '<select name="' . $key . '" required>';
            $html .= '<option value="">Select...</option>';

            foreach ($factor['options'] as $option => $data) {
                $label = ucfirst($option);
                $html .= '<option value="' . $option . '">' . $label . '</option>';
            }

            $html .= '</select>';
            $html .= '</div>';
        }

        $html .= '<button type="submit" class="button button-primary">Get Recommendation</button>';
        $html .= '</form>';
        $html .= '<div id="decision-result"></div>';
        $html .= '</div>';

        return $html;
    }
}

// Decision Logic Summary Table
$decision_matrix = [
    'small_blog' => [
        'ai_capability' => 'basic',
        'traffic_scale' => 'low',
        'budget' => 'free',
        'technical_skill' => 'beginner',
        'real_time' => 'nice_to_have',
        'distribution' => 'wordpress_org'
    ],
    'agency' => [
        'ai_capability' => 'important',
        'traffic_scale' => 'medium',
        'budget' => 'medium',
        'technical_skill' => 'intermediate',
        'real_time' => 'critical',
        'distribution' => 'custom'
    ],
    'saas_product' => [
        'ai_capability' => 'critical',
        'traffic_scale' => 'high',
        'budget' => 'high',
        'technical_skill' => 'expert',
        'real_time' => 'critical',
        'distribution' => 'saas'
    ]
];

// Test each scenario
echo "=== ARCHITECTURE RECOMMENDATIONS ===\n\n";

$engine = new ZenSEO_Architecture_Decision();

foreach ($decision_matrix as $scenario => $answers) {
    $result = $engine->make_decision($answers);
    echo strtoupper($scenario) . ": " . $result['recommendation'] . " (confidence: {$result['confidence']}%)\n";
}