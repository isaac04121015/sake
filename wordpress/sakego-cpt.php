<?php
/**
 * Sakego CPT Registration
 *
 * 把這段程式碼加入你的主題 functions.php,或建立一個外掛檔案。
 * 註冊「日本酒產品」自訂文章類型 + 「地區」「酒造」分類法。
 *
 * 重要:必須註冊以下 meta key 為 REST 可見,publish_to_wordpress.py 才能寫入。
 */

if (!defined('ABSPATH')) exit;

/**
 * 註冊 CPT: sake_product
 */
function sakego_register_sake_product_cpt() {
    register_post_type('sake_product', array(
        'labels' => array(
            'name'          => '日本酒產品',
            'singular_name' => '日本酒',
            'add_new'       => '新增酒款',
            'add_new_item'  => '新增酒款',
            'edit_item'     => '編輯酒款',
            'view_item'     => '檢視酒款',
            'search_items'  => '搜尋酒款',
            'menu_name'     => '日本酒',
        ),
        'public'              => true,
        'has_archive'         => true,
        'rewrite'             => array('slug' => 'sake', 'with_front' => false),
        'show_in_rest'        => true,  // 必須 true,REST API 才能寫入
        'rest_base'           => 'sake_product',
        'supports'            => array('title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'),
        'menu_icon'           => 'dashicons-beer',
        'menu_position'       => 6,
        'taxonomies'          => array('sake_region', 'sake_brewery'),
    ));
}
add_action('init', 'sakego_register_sake_product_cpt');

/**
 * 註冊分類法:地區 (sake_region) 與酒造 (sake_brewery)
 */
function sakego_register_sake_taxonomies() {
    register_taxonomy('sake_region', array('sake_product'), array(
        'labels' => array(
            'name'          => '產地',
            'singular_name' => '產地',
            'search_items'  => '搜尋產地',
            'all_items'     => '所有產地',
            'edit_item'     => '編輯產地',
            'add_new_item'  => '新增產地',
        ),
        'hierarchical'      => true,
        'public'            => true,
        'show_admin_column' => true,
        'show_in_rest'      => true,
        'rewrite'           => array('slug' => 'sake-region'),
    ));

    register_taxonomy('sake_brewery', array('sake_product'), array(
        'labels' => array(
            'name'          => '酒造',
            'singular_name' => '酒造',
            'search_items'  => '搜尋酒造',
            'all_items'     => '所有酒造',
            'edit_item'     => '編輯酒造',
            'add_new_item'  => '新增酒造',
        ),
        'hierarchical'      => false,
        'public'            => true,
        'show_admin_column' => true,
        'show_in_rest'      => true,
        'rewrite'           => array('slug' => 'sake-brewery'),
    ));
}
add_action('init', 'sakego_register_sake_taxonomies');

/**
 * 註冊 meta keys 為 REST 可寫入
 *
 * 沒有這段,publish_to_wordpress.py 寫入的 meta 會被 WP 忽略。
 */
function sakego_register_sake_post_meta() {
    $meta_keys = array(
        'sakenowa_brand_id'   => 'string',
        'sakenowa_brand_url'  => 'string',
        'sake_brewery_jp'     => 'string',
        'sake_brewery_id'     => 'string',
        'sake_name_jp'        => 'string',
        'sake_area_jp'        => 'string',
        'sake_type'           => 'string',
        'sake_rice_variety'   => 'string',
        'sake_seimaibuai'     => 'string',
        'sake_yeast'          => 'string',
        'sake_abv'            => 'string',
        'sake_smv'            => 'string',
        'sake_acidity'        => 'string',
    );

    foreach ($meta_keys as $key => $type) {
        register_post_meta('sake_product', $key, array(
            'type'         => $type,
            'single'       => true,
            'show_in_rest' => true,
            'auth_callback' => function() {
                return current_user_can('edit_posts');
            },
        ));
    }
}
add_action('init', 'sakego_register_sake_post_meta');

/**
 * 在 REST API 回傳結果中允許用 meta_key/meta_value 過濾
 *
 * publish_to_wordpress.py 的 find_existing_post() 需要這個來找冪等鍵。
 */
function sakego_allow_meta_query_for_sake_product($args, $request) {
    $meta_key = $request->get_param('meta_key');
    $meta_value = $request->get_param('meta_value');

    if ($meta_key && $meta_value) {
        $args['meta_query'] = array(
            array(
                'key'   => $meta_key,
                'value' => $meta_value,
            ),
        );
    }
    return $args;
}
add_filter('rest_sake_product_query', 'sakego_allow_meta_query_for_sake_product', 10, 2);
