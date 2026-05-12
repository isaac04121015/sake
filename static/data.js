// Fixture data for the Sakego web UI kit.
// All names are real, well-known Japanese sake brands; specs taken from
// publicly-listed facts (米種, 精米步合, 都道府縣). Descriptive copy is
// new, written in the Sakego brand voice (see config/brand_voice.md).

window.SAKEGO_DATA = (function () {
  const regions = [
    {
      id: 'kanto', name: '關東', count: 2,
      heroBg: 'https://images.unsplash.com/photo-1579952516518-12c1d8f3a05a?w=1600&q=80'
    },
    {
      id: 'chubu', name: '中部', count: 2,
      heroBg: 'https://images.unsplash.com/photo-1535350356005-fd52b3b524fb?w=1600&q=80'
    },
    {
      id: 'kansai', name: '關西', count: 2,
      heroBg: 'https://images.unsplash.com/photo-1546874177-9e664107314e?w=1600&q=80'
    },
    { id: 'kyushu', name: '九州', count: 1 },
    { id: 'tohoku', name: '東北', count: 3 },
    { id: 'hokkaido', name: '北海道', count: 1 },
  ];

  const breweries = [
    {
      id: 'iso-jiman', region_id: 'chubu', area: '靜岡縣',
      name_jp: '磯自慢酒造', name_zhtw: '磯自慢酒造',
      founded: 1830, website: 'https://www.isojiman-sake.jp',
      heroBg: 'https://images.unsplash.com/photo-1546874177-9e664107314e?w=1600&q=80',
      theme: { primary: '#722F37', secondary: '#3a181c', label: 'JUNMAI', bg: 'linear-gradient(135deg, #2a1518 0%, #4a2228 100%)', tint: 'linear-gradient(135deg, #fdf6ec 0%, #f5e0d6 100%)' }
    },
    {
      id: 'dassai', region_id: 'chubu', area: '山口縣',
      name_jp: '旭酒造', name_zhtw: '旭酒造',
      founded: 1948, website: 'https://www.asahishuzo.ne.jp',
      heroBg: 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=1600&q=80',
      theme: { primary: '#1f3a5f', secondary: '#0f1d31', label: 'DAIGINJO', bg: 'linear-gradient(135deg, #0f1d31 0%, #1f3a5f 100%)', tint: 'linear-gradient(135deg, #fdf6ec 0%, #dde6f1 100%)' }
    },
    {
      id: 'kubota', region_id: 'tohoku', area: '新潟縣',
      name_jp: '朝日酒造', name_zhtw: '朝日酒造',
      founded: 1830, website: 'https://www.asahi-shuzo.co.jp',
      heroBg: 'https://images.unsplash.com/photo-1535350356005-fd52b3b524fb?w=1600&q=80',
      theme: { primary: '#2f5a3e', secondary: '#162a1d', label: 'JUNMAI GINJO', bg: 'linear-gradient(135deg, #162a1d 0%, #2f5a3e 100%)', tint: 'linear-gradient(135deg, #fdf6ec 0%, #dce8df 100%)' }
    },
    {
      id: 'kokuryu', region_id: 'chubu', area: '福井縣',
      name_jp: '黒龍酒造', name_zhtw: '黑龍酒造',
      founded: 1804, website: 'https://www.kokuryu.co.jp',
      heroBg: 'https://images.unsplash.com/photo-1579952516518-12c1d8f3a05a?w=1600&q=80',
      theme: { primary: '#1A1A1A', secondary: '#000', label: 'JUNMAI DAIGINJO', bg: 'linear-gradient(135deg, #000 0%, #1A1A1A 100%)', tint: 'linear-gradient(135deg, #fdf6ec 0%, #e6e2dc 100%)' }
    }
  ];

  const products = [
    {
      id: 'iso-jiman-jdg', brewery_id: 'iso-jiman',
      name_jp: '磯自慢 純米大吟釀 35', name_zhtw: '磯自慢 純米大吟釀 磨き三割五分',
      sake_type: '純米大吟釀', rice: '山田錦', rice_origin: '兵庫縣特A地區',
      seimaibuai: 35, yeast: '協會 9 號', abv: 16, smv: '+5', acidity: 1.2,
      stars: 5,
      awards: ['全國新酒鑑評會 金賞', 'IWC 純米大吟釀 Trophy', 'Kura Master Platinum'],
      flavor: { '華麗': 0.85, '芳醇': 0.7, '厚重': 0.35, '穩重': 0.4, '辛口': 0.6, '輕快': 0.7 },
      tags: ['華やか', 'フルーティ', 'ドライ'],
      description: '磯自慢扎根於靜岡燒津的港町,擁抱海風與南阿爾卑斯山的雪融水。本款選用兵庫山田錦,精米至 35%,以低溫長期發酵勾勒出細緻的吟釀香氣。風味雷達顯示華麗與輕快兼具,屬於現代派純米大吟釀的典型。',
      tasting: '建議冷藏至 8-10°C 飲用。入口先是哈密瓜與梨子的果香,中段轉為米的甘甜,尾韻乾淨俐落,幾乎不留澀感。',
      pairing: '搭配生魚片與握壽司最能凸顯果香層次;若是台式清蒸海魚淋少許醬油,清爽尾韻也能襯出魚肉的鮮甜。'
    },
    {
      id: 'iso-jiman-honjozo', brewery_id: 'iso-jiman',
      name_jp: '磯自慢 特別本醸造', name_zhtw: '磯自慢 特別本醸造',
      sake_type: '特別本醸造', rice: '山田錦', seimaibuai: 60, abv: 15.5,
      stars: 3,
      awards: ['靜岡縣清酒鑑評会 優秀賞'],
      flavor: { '華麗': 0.5, '芳醇': 0.55, '厚重': 0.45, '穩重': 0.6, '辛口': 0.75, '輕快': 0.55 },
      tags: ['辛口', '燗酒'],
      description: '日常飲用的標準款。50% 山田錦混合常規米,精米 60%,呈現磯自慢一貫的乾淨口感但更貼近餐桌。'
    },
    {
      id: 'dassai-23', brewery_id: 'dassai',
      name_jp: '獺祭 純米大吟醸 磨き二割三分', name_zhtw: '獺祭 二割三分',
      sake_type: '純米大吟醸', rice: '山田錦', rice_origin: '山口縣 / 兵庫縣',
      seimaibuai: 23, abv: 16, smv: '+4', acidity: 1.4,
      stars: 5,
      awards: ['IWC Champion Sake', 'Kura Master Platinum', '全國新酒鑑評會 金賞', 'Sake Selection Brussel Grand Gold'],
      flavor: { '華麗': 0.9, '芳醇': 0.6, '厚重': 0.25, '穩重': 0.35, '辛口': 0.55, '輕快': 0.85 },
      tags: ['華やか', 'フルーティ'],
      description: '旭酒造的代表作,將山田錦精米至 23%,只取酒米最核心的部分。香氣以白桃、洋梨為主軸,口感極為純淨。',
      pairing: '冷飲。適合生蠔、白肉魚薄造或起司拼盤。'
    },
    {
      id: 'dassai-45', brewery_id: 'dassai',
      name_jp: '獺祭 純米大吟醸 45', name_zhtw: '獺祭 純米大吟醸 45',
      sake_type: '純米大吟醸', rice: '山田錦', seimaibuai: 45, abv: 16,
      stars: 4,
      awards: ['Kura Master Gold', 'IWC Gold'],
      flavor: { '華麗': 0.75, '芳醇': 0.55, '厚重': 0.3, '穩重': 0.5, '辛口': 0.55, '輕快': 0.7 },
      tags: ['華やか'],
      description: '獺祭系列的入門款,風味輪廓接近二割三分但價格更友善,適合日常飲用。'
    },
    {
      id: 'kubota-manju', brewery_id: 'kubota',
      name_jp: '久保田 萬寿', name_zhtw: '久保田 萬壽',
      sake_type: '純米大吟釀', rice: '五百萬石', seimaibuai: 50, abv: 15,
      stars: 4,
      awards: ['全國新酒鑑評會 金賞', 'Japan Sake Awards 金賞'],
      flavor: { '華麗': 0.65, '芳醇': 0.75, '厚重': 0.5, '穩重': 0.7, '辛口': 0.65, '輕快': 0.55 },
      tags: ['芳醇', '穏やか'],
      description: '新潟代表性銘柄之一。使用當地五百萬石,風味端正,香氣含蓄,屬於傳統派的均衡型純米大吟釀。'
    },
    {
      id: 'kokuryu-nijiku', brewery_id: 'kokuryu',
      name_jp: '黒龍 二左衛門', name_zhtw: '黑龍 二左衛門',
      sake_type: '純米大吟釀', rice: '山田錦', seimaibuai: 35, abv: 16,
      stars: 5,
      awards: ['全國新酒鑑評會 金賞', 'Kura Master Platinum', 'IWC Gold'],
      flavor: { '華麗': 0.7, '芳醇': 0.8, '厚重': 0.55, '穩重': 0.6, '辛口': 0.5, '輕快': 0.45 },
      tags: ['芳醇', '濃醇'],
      description: '黑龍酒造的高階款,以兵庫山田錦精米至 35% 釀造,風味芳醇厚實,屬於福井派的代表。'
    }
  ];

  return { regions, breweries, products };
})();
