from __future__ import annotations

from typing import Any


LAYER_LABELS = {
    "core": "一级：持仓相关",
    "secular": "长期主线：1-5年跟踪",
    "watch": "二级：重点观察",
    "event": "三级：事件触发",
    "avoid": "降噪：默认回避",
}

LAYER_ORDER = {"core": 0, "secular": 1, "watch": 2, "event": 3, "avoid": 4}


DEFAULT_INDUSTRY_RADAR: list[dict[str, Any]] = [
    {
        "id": "ai_infra",
        "name": "AI基础设施链",
        "layer": "core",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["ai", "nvidia", "semiconductor", "chip", "data center", "算力", "人工智能", "半导体", "芯片", "数据中心"],
        "why": "和现有AI/成长仓高度相关，是每天必须看的主线。",
        "watch": "海外AI龙头、半导体指数、国内算力政策、成交量、AI仓位上限。",
        "verify": "至少等价格、订单、政策或相对强弱中两项确认。",
        "action": "默认先复核持仓重叠和上限，不因单日强势继续叠加进攻仓。",
        "instruments": ["011840", "588930", "512480", "588200"],
    },
    {
        "id": "ai_power_base",
        "name": "AI电力底座/算电协同",
        "layer": "secular",
        "theme_keys": ["ai_power_base", "power", "energy", "new_energy"],
        "horizon": "1-5年",
        "keywords": [
            "compute power and electricity",
            "green compute",
            "ai data center",
            "data center power",
            "800v hvdc",
            "liquid cooling",
            "算电协同",
            "绿色算力",
            "算力电力",
            "数据中心用电",
            "绿电",
            "风电",
            "电网",
            "变压器",
            "特高压",
            "储能",
            "虚拟电厂",
            "电力交易",
            "绿证",
            "液冷",
            "源网荷储",
            "AIDC",
        ],
        "why": "AI主线不能只看芯片和模型；长期约束会扩散到绿电、电网、储能、液冷和数据中心电源。",
        "watch": "绿电占比、数据中心项目、PPA/绿证、电网设备订单、储能招标、液冷/电源方案、风电相对光伏和板块相对沪深300强弱。",
        "verify": "至少等政策、订单、价格/相对强弱、成交量、利润兑现中两项确认；只讲故事不触发买入。",
        "action": "先允许2%-3%观察底仓；政策/订单/价格连续确认后才考虑升到5%-8%；不把它当成继续加AI进攻仓的理由。",
        "instruments": ["561560", "560390"],
    },
    {
        "id": "data_center_power_cooling",
        "name": "AIDC电源/液冷/800V",
        "layer": "secular",
        "theme_keys": ["ai_power_base", "ai"],
        "horizon": "1-5年",
        "keywords": [
            "800v hvdc",
            "liquid cooling",
            "power supply",
            "ups",
            "bbu",
            "cooling",
            "数据中心电源",
            "液冷",
            "800V",
            "HVDC",
            "UPS",
            "BBU",
            "服务器电源",
            "CDU",
            "换热",
        ],
        "why": "AI机房功率密度上升会先推电源架构和散热升级，适合做长期主线观察，不适合按单条新闻追高。",
        "watch": "大客户架构迁移、液冷渗透率、服务器电源订单、800V HVDC进度、毛利率和交付周期。",
        "verify": "看订单、客户导入、价格、交付周期和毛利率是否同步确认。",
        "action": "只进观察池；没有ETF化表达和价格确认前，不扩固定可买池。",
        "instruments": [],
    },
    {
        "id": "power_trading_vpp",
        "name": "电力交易/虚拟电厂/绿证",
        "layer": "secular",
        "theme_keys": ["ai_power_base", "power", "new_energy"],
        "horizon": "1-5年",
        "keywords": [
            "power trading",
            "virtual power plant",
            "green certificate",
            "ppa",
            "demand response",
            "电力交易",
            "虚拟电厂",
            "绿证",
            "绿电交易",
            "需求响应",
            "PPA",
            "零碳算力",
        ],
        "why": "算力负载和绿电波动需要交易、调度和凭证机制承接，可能成为长期利润分配入口。",
        "watch": "绿电溢价、PPA合同、绿证成交、需求响应政策、园区电价和地方政策试点。",
        "verify": "先看正式政策、交易量、合同和利润留存，不能只按概念炒作。",
        "action": "作为长期跟踪主题；没有上市公司利润兑现前，只提高关注，不生成买入。",
        "instruments": [],
    },
    {
        "id": "china_broad_core",
        "name": "A股宽基/中国宏观",
        "layer": "core",
        "theme_keys": ["china_macro"],
        "keywords": ["china", "yuan", "pboc", "stimulus", "pmi", "中国", "人民币", "央行", "政策", "消费", "沪深300", "上证"],
        "why": "决定稳底仓和月度新增资金的底盘。",
        "watch": "人民币、政策口径、A股成交、沪深300/上证相对创业板强弱。",
        "verify": "看官方政策、汇率、成交量和宽基价格是否同向。",
        "action": "回撤时优先考虑稳底仓，不把进攻仓当默认补仓方向。",
        "instruments": ["510310", "510210"],
    },
    {
        "id": "gold_real_rates",
        "name": "黄金/实际利率",
        "layer": "core",
        "theme_keys": ["gold"],
        "keywords": ["gold", "treasury", "yield", "dollar", "fed", "inflation", "黄金", "美债", "美元", "美联储", "实际利率", "通胀"],
        "why": "黄金是组合保险仓，不是收益主攻仓。",
        "watch": "黄金价格、美元指数、美债收益率、地缘风险和黄金仓位区间。",
        "verify": "看黄金上涨是否被美元/美债方向支持，仓位是否低于10%-15%保险区间。",
        "action": "低于区间才复核是否补保险仓，高于区间不追。",
        "instruments": ["000216", "518880"],
    },
    {
        "id": "semiconductor_materials",
        "name": "半导体材料/卡脖子链",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["wf6", "helium", "photoresist", "specialty gas", "precursor", "电子特气", "六氟化钨", "氦气", "光刻胶", "靶材", "前驱体"],
        "why": "小品种也可能卡住大产业，适合做左侧观察。",
        "watch": "不可替代性、认证周期、出口限制、长协、库存周数和交期。",
        "verify": "至少看到价格/交期/订单/毛利率/客户认证两项确认。",
        "action": "先放观察池；未验证前不因为题材稀缺追高。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "helium_supply_chain",
        "name": "氦气/电子特气",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["helium", "specialty gas", "noble gas", "氦气", "电子特气", "气源", "提纯", "半导体气体"],
        "why": "氦气更像半导体保供约束，先看气源、提纯和国产替代，不把扩产故事直接当盈利故事。",
        "watch": "气源可得性、电子级提纯、半导体客户认证、进口依赖和价格持续性。",
        "verify": "至少看到电子级价格、长协订单、客户认证或进口约束中两项确认。",
        "action": "只提升半导体材料观察优先级；AI仓位超线时仍不新增同类进攻仓。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "tungsten_hexafluoride",
        "name": "六氟化钨/前驱体",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["wf6", "tungsten hexafluoride", "precursor", "六氟化钨", "钨", "前驱体", "薄膜沉积", "cvd"],
        "why": "六氟化钨是小市场高卡点材料，重点不是市场规模，而是不可替代性、认证周期和涨价传导。",
        "watch": "钨资源约束、高纯产能、半导体沉积需求、出口规则和下游议价。",
        "verify": "先看价格/订单/出口/毛利率能否连续确认，不能只看稀缺叙事。",
        "action": "作为半导体材料子雷达；未出现价格和订单验证前只观察。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "photoresist_materials",
        "name": "光刻胶/靶材",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["photoresist", "target material", "mask", "光刻胶", "靶材", "掩膜版", "晶圆材料"],
        "why": "光刻胶和靶材更看认证和良率，国产替代周期长，不能把国产替代四个字直接等同于利润。",
        "watch": "客户认证节点、良率、国产替代订单、毛利率和资本开支节奏。",
        "verify": "确认客户导入和收入占比，而不是只确认新闻标题。",
        "action": "只进入材料候选观察，不默认扩可买池。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "advanced_packaging",
        "name": "先进封装/玻璃基板",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["advanced packaging", "coWoS", "hbm", "glass substrate", "先进封装", "玻璃基板", "hbm", "封装", "载板"],
        "why": "先进封装跟AI算力需求更直连，但要分清设备、材料、封装产能和真实订单。",
        "watch": "海外封装产能、HBM订单、载板/玻璃基板验证、设备交期和国内封测订单。",
        "verify": "看订单、产能利用率、价格和客户认证是否同步。",
        "action": "作为AI上游观察，若AI仓位已高，只用于解释持仓风险，不新增进攻仓。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "optical_interconnect",
        "name": "光通信/空心光纤/CPO",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": [
            "optical interconnect",
            "hollow core fiber",
            "co-packaged optics",
            "cpo",
            "ocs",
            "optical module",
            "silicon photonics",
            "光通信",
            "空心光纤",
            "CPO",
            "OCS",
            "光模块",
            "硅光",
            "高速互联",
            "数据中心互联",
        ],
        "why": "AI数据中心规模扩大后，瓶颈会从单卡算力扩散到集群互联、延迟、功耗和存储压力，光通信是AI基础设施的关键子线。",
        "watch": "空心光纤验证、CPO/OCS架构、光模块速率、硅光方案、交换机/光互联订单和海外云厂商资本开支。",
        "verify": "看客户导入、订单、速率升级、交付周期、毛利率和板块相对强弱是否同步确认。",
        "action": "只提升AI基础设施观察优先级；AI仓位或成长仓位超线时，不把光通信新闻当成新增进攻仓理由。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "energy_power",
        "name": "能源电力链",
        "layer": "watch",
        "theme_keys": ["energy"],
        "keywords": ["oil", "gas", "coal", "power", "grid", "wind power", "原油", "天然气", "煤炭", "电力", "电网", "风电", "绿电"],
        "why": "能源冲击通常先影响电力、煤炭、航运、通胀和防御资产。",
        "watch": "油气价格、煤价、电力ETF、电网订单、风电相对光伏强弱。",
        "verify": "看能源价格和电力/电网板块是否同步确认。",
        "action": "先看传导链，不把新能源当油价上涨的第一反应。",
        "instruments": ["561560", "560390"],
    },
    {
        "id": "wind_power_aidc",
        "name": "风电/算力绿电",
        "layer": "watch",
        "theme_keys": ["energy", "new_energy"],
        "keywords": ["wind power", "green power", "data center", "aidc", "风电", "绿电", "算力中心", "源网荷储", "西北算力"],
        "why": "算力中心的绿电约束会让风电、电网和储能分化，不能把风电和光伏混成一个逻辑。",
        "watch": "算力中心投产、绿电消纳比例、风电利用小时、电网接入和储能订单。",
        "verify": "看风电相对光伏强弱、电网/储能订单和地方政策是否一起确认。",
        "action": "只在价格和订单共振时升级电力链候选。",
        "instruments": ["561560", "560390"],
    },
    {
        "id": "grid_storage_power",
        "name": "电网/储能/火电调峰",
        "layer": "watch",
        "theme_keys": ["energy", "new_energy"],
        "keywords": ["grid", "storage", "thermal power", "电网", "储能", "火电", "调峰", "输配电", "特高压"],
        "why": "新能源消纳和算力用电最后要落到电网、储能和调峰能力，先看订单和利用率。",
        "watch": "电网投资、储能招标、火电容量电价、用电负荷和特高压建设。",
        "verify": "看订单、价格和政策落地，不靠一句源网荷储追高。",
        "action": "作为能源电力链的确认层，不直接替代宽基或防守仓。",
        "instruments": ["561560", "560390"],
    },
    {
        "id": "resource_metals",
        "name": "资源品/关键矿产",
        "layer": "watch",
        "theme_keys": ["gold", "energy"],
        "keywords": ["rare earth", "copper", "tungsten", "lithium", "critical mineral", "稀土", "铜", "钨", "锂", "关键矿产", "有色"],
        "why": "适合观察资源卡点和价格传导，不适合每天追涨。",
        "watch": "出口管制、库存、价格指数、海外供应扰动和下游议价能力。",
        "verify": "确认价格上涨能否传到企业利润，而不是只停留在商品波动。",
        "action": "只在价格和产业验证同步时升级候选。",
        "instruments": ["512400", "518880"],
    },
    {
        "id": "anti_involution_policy",
        "name": "政策/反内卷链",
        "layer": "watch",
        "theme_keys": ["china_macro", "new_energy"],
        "keywords": ["tariff", "export", "anti-involution", "overcapacity", "关税", "出口", "反内卷", "产能", "低价倾销", "涨价"],
        "why": "决定哪些行业能涨价，哪些只是承担保供或政策任务。",
        "watch": "反内卷文件、出口报价、PPI、行业协会口径、龙头毛利率。",
        "verify": "先确认国内能不能涨价，再确认利润能不能修复。",
        "action": "用作筛选器：政策压价行业先降权。",
        "instruments": [],
    },
    {
        "id": "hk_tech",
        "name": "港股科技/互联网",
        "layer": "watch",
        "theme_keys": ["ai", "china_macro"],
        "keywords": ["hong kong", "hang seng tech", "platform", "internet", "港股", "恒生科技", "平台经济", "互联网"],
        "why": "弹性大，但和AI/成长风险偏好相关，不能当防守仓。",
        "watch": "美元压力、南向资金、平台政策、AI应用侧和港股科技相对强弱。",
        "verify": "确认流动性和政策同时改善，再考虑候选优先级。",
        "action": "只做观察候选；AI仓位偏高时不主动叠加。",
        "instruments": ["513010", "513180"],
    },
    {
        "id": "dividend_defense",
        "name": "红利低波/防御",
        "layer": "watch",
        "theme_keys": ["china_macro", "gold"],
        "keywords": ["dividend", "low volatility", "utility", "bank", "红利", "低波", "公用事业", "银行", "防御"],
        "why": "当AI和成长仓偏高时，用来降低组合波动。",
        "watch": "长端利率、股息率吸引力、风险偏好、红利低波相对成长强弱。",
        "verify": "确认不是纯防守拥挤，而是组合需要降低波动。",
        "action": "新增资金防守候选，不承担进攻收益预期。",
        "instruments": ["512890", "515100"],
    },
    {
        "id": "shipping_routes",
        "name": "航运/通道风险",
        "layer": "event",
        "theme_keys": ["energy"],
        "keywords": ["shipping", "freight", "hormuz", "red sea", "suez", "航运", "油运", "霍尔木兹", "红海", "苏伊士", "运价"],
        "why": "只有通道风险出现时才需要抬高优先级。",
        "watch": "油运费率、BDI、绕航时间、保险费和港口吞吐。",
        "verify": "看运价和能源价格是否同步确认。",
        "action": "事件触发后再看能源/航运/保险链，不日常占用注意力。",
        "instruments": [],
    },
    {
        "id": "new_energy_cycle",
        "name": "新能源价格周期",
        "layer": "event",
        "theme_keys": ["new_energy"],
        "keywords": ["solar", "photovoltaic", "ev", "battery", "lithium", "光伏", "新能源车", "锂电", "锂价", "储能"],
        "why": "新能源要看产能出清和价格周期，不是油价上涨就直接买。",
        "watch": "锂价、光伏链价格、新能源车销量、补贴、龙头盈利修复。",
        "verify": "看价格和利润是否修复，而不是只看政策或情绪。",
        "action": "没有盈利修复前，只保留观察。",
        "instruments": ["159915"],
    },
    {
        "id": "sanctions_tariffs",
        "name": "制裁/关税/结算规则",
        "layer": "event",
        "theme_keys": ["china_macro", "energy"],
        "keywords": ["sanction", "tariff", "export ban", "currency", "swift", "制裁", "关税", "出口禁令", "结算", "美元", "人民币"],
        "why": "规则变化会改变供应链成本、汇率和谈判筹码。",
        "watch": "官方文件、生效日期、豁免条款、汇率、商品价格和替代供应。",
        "verify": "只按官方和主流媒体交叉验证，不按传闻推演。",
        "action": "先影响风险偏好和观察池，不直接生成交易动作。",
        "instruments": [],
    },
    {
        "id": "story_only",
        "name": "纯题材小作文",
        "layer": "avoid",
        "theme_keys": [],
        "keywords": ["rumor", "unconfirmed", "viral", "传闻", "小作文", "网传", "未经证实"],
        "why": "容易制造兴奋感，但不可验证。",
        "watch": "是否有官方源、主流媒体交叉验证、真实价格或订单确认。",
        "verify": "没有验证就不进入操作区。",
        "action": "默认忽略；只记录观察。",
        "instruments": [],
    },
    {
        "id": "crowded_right_side",
        "name": "高拥挤右侧追涨",
        "layer": "avoid",
        "theme_keys": [],
        "keywords": ["crowded", "leverage", "all time high", "拥挤", "杠杆", "新高", "右侧", "一致看好"],
        "why": "确定性越强，价格可能越不划算。",
        "watch": "成交放量、估值分位、融资杠杆、筹码结构和回撤纪律。",
        "verify": "确认赔率而不是只确认故事。",
        "action": "作为追高刹车，不作为买入理由。",
        "instruments": [],
    },
]


INDUSTRY_FACT_DETAILS: dict[str, dict[str, Any]] = {
    "ai_infra": {
        "逻辑": "AI基础设施先看资本开支、芯片供给、数据中心电力和订单兑现，不只看模型热度。",
        "确认": ["海外AI龙头指引上修", "半导体/算力价格同步走强", "数据中心电力约束被定价"],
        "否定": ["订单延后", "芯片供给缓解但价格不涨", "组合AI仓位已超纪律线"],
    },
    "ai_power_base": {
        "逻辑": "AI算力的长期瓶颈会从芯片扩散到电力底座，核心是绿电、电网、储能、液冷和数据中心电源能不能兑现订单和利润。",
        "确认": ["算电协同/绿色算力政策落地", "数据中心项目或PPA合同增加", "电网设备/储能/液冷订单确认", "电力链相对沪深300走强"],
        "否定": ["只有概念新闻没有订单", "板块成交不足或追高拥挤", "利润被地方、电网或客户分走", "继续和AI进攻仓高度同涨同跌"],
        "仓位纪律": ["首次只允许2%-3%观察底仓", "连续确认后才考虑5%-8%", "不因长期故事破坏AI仓位上限"],
    },
    "data_center_power_cooling": {
        "逻辑": "AI机房功率密度提高会推动电源架构、液冷和散热部件升级，真正价值来自客户导入和交付周期，不来自单条技术新闻。",
        "确认": ["800V HVDC或高压直流方案推进", "液冷渗透率提升", "服务器电源/BBU/UPS订单确认", "毛利率和交付周期改善"],
        "否定": ["仍停留在样品或概念", "订单没有放量", "价格竞争吃掉毛利", "没有可跟踪ETF或标的"],
    },
    "power_trading_vpp": {
        "逻辑": "算力负载要和绿电波动匹配，电力交易、虚拟电厂、绿证和PPA合同决定谁能拿到长期议价权。",
        "确认": ["绿电交易量提升", "PPA合同公布", "虚拟电厂/需求响应政策落地", "园区电价和利润留存可验证"],
        "否定": ["只有地方口号", "没有交易量或合同", "收益被补贴和电价机制吞掉", "上市公司利润表没有兑现"],
    },
    "china_broad_core": {
        "逻辑": "宽基是组合底盘，政策、流动性、人民币和成交量决定新增资金节奏。",
        "确认": ["人民币企稳", "成交量放大", "稳增长政策落地", "沪深300相对成长不弱"],
        "否定": ["政策只喊话不落地", "汇率继续承压", "成交缩量"],
    },
    "gold_real_rates": {
        "逻辑": "黄金是保险仓，核心看实际利率、美元、央行买盘和地缘风险。",
        "确认": ["黄金上涨同时美元或美债收益率不强", "央行买盘延续", "地缘风险升温"],
        "否定": ["实际利率快速上行", "黄金仓位已高于保险区间", "只靠单日避险情绪"],
    },
    "semiconductor_materials": {
        "逻辑": "半导体材料看不可替代性、认证周期、供应集中度和出口管制，小品种可能卡住大产业。",
        "确认": ["价格上涨", "交期拉长", "客户认证推进", "出口管制收紧", "库存周数下降"],
        "否定": ["只是题材传播", "价格没有确认", "下游库存充足", "没有订单或毛利率验证"],
    },
    "helium_supply_chain": {
        "逻辑": "氦气先看半导体保供和电子级提纯，不把普通工业气扩产直接等同于利润弹性。",
        "确认": ["电子级氦气价格连续上行", "半导体客户长协", "进口气源受限", "提纯产线达标"],
        "否定": ["只扩低纯度产能", "没有客户认证", "价格没有连续确认", "运输或气源成本吞噬利润"],
    },
    "tungsten_hexafluoride": {
        "逻辑": "六氟化钨看钨资源、高纯氟化能力、沉积工艺不可替代性和出口规则，小市场也可能有高议价。",
        "确认": ["WF6报价上调", "高纯产能紧张", "下游晶圆厂认证", "出口限制或长协涨价"],
        "否定": ["只讲稀缺没有价格", "新增产能快速释放", "客户认证未过", "毛利率没有改善"],
    },
    "photoresist_materials": {
        "逻辑": "光刻胶/靶材的核心是认证、良率和客户导入，国产替代节奏通常慢于题材传播。",
        "确认": ["客户认证通过", "收入占比提升", "良率改善", "订单和毛利率同步"],
        "否定": ["只有国产替代叙事", "验证周期拉长", "价格不涨", "收入占比过低"],
    },
    "advanced_packaging": {
        "逻辑": "先进封装要区分设备、材料、载板、封测产能和AI订单，先看瓶颈到底卡在哪里。",
        "确认": ["HBM/先进封装订单", "设备交期拉长", "产能利用率提升", "客户认证通过"],
        "否定": ["只跟随AI情绪", "订单未落地", "产能快速释放", "价格没有确认"],
    },
    "optical_interconnect": {
        "逻辑": "光通信互联的价值在于降低AI集群延迟、功耗和部分存储/缓存压力，核心看客户导入、速率升级和订单，不是只看技术词汇。",
        "确认": ["空心光纤或CPO/OCS客户验证", "光模块速率升级", "云厂商互联资本开支增加", "订单和毛利率同步改善"],
        "否定": ["只有技术展示没有量产", "客户导入不明确", "价格竞争压低毛利", "AI仓位纪律已经超线"],
    },
    "energy_power": {
        "逻辑": "能源电力链看油气煤价格、绿电消纳、算力用电和电网投资，风光不能混成一个逻辑。",
        "确认": ["油气煤价格上行", "电力/电网订单确认", "风电相对光伏走强", "算力绿电需求落地"],
        "否定": ["能源价格回落", "电力板块不跟", "政策只保供不让利润释放"],
    },
    "wind_power_aidc": {
        "逻辑": "风电相对光伏的差异在于出力曲线、区域资源和算力绿电消纳，最终还要看订单和利用小时。",
        "确认": ["AIDC绿电比例要求", "风电利用小时提升", "电网接入改善", "风电相对光伏走强"],
        "否定": ["只讲政策不看订单", "消纳受限", "风电价格不跟", "装机增长但利润不修复"],
    },
    "grid_storage_power": {
        "逻辑": "电网/储能/火电调峰是绿电和算力用电的承接层，重在投资计划和招标订单。",
        "确认": ["电网投资上修", "储能招标放量", "容量电价改善", "特高压建设加速"],
        "否定": ["招标价格继续内卷", "项目延期", "政策只保供不保利润"],
    },
    "resource_metals": {
        "逻辑": "资源品看供给集中、出口规则、库存和下游议价，商品上涨要能传到企业利润。",
        "确认": ["出口限制或供应扰动", "库存下降", "现货价格连续确认", "龙头毛利率改善"],
        "否定": ["期货单日波动", "下游无法接受涨价", "新增供给快速释放"],
    },
    "anti_involution_policy": {
        "逻辑": "反内卷的价值在于能否限制低价竞争并修复利润，不是所有政策口号都等于涨价。",
        "确认": ["行业协会或监管文件落地", "报价上调", "产能利用率改善", "毛利率修复"],
        "否定": ["产能仍继续扩张", "低价竞争未停", "海外需求不足"],
    },
    "hk_tech": {
        "逻辑": "港股科技看美元流动性、南向资金、平台政策和AI应用侧，弹性强但不是防守仓。",
        "确认": ["南向持续流入", "美元压力缓解", "平台政策改善", "应用侧收入兑现"],
        "否定": ["美元走强", "平台监管反复", "只涨估值不涨业绩"],
    },
    "dividend_defense": {
        "逻辑": "红利低波是组合稳定器，重点看股息率、利率和成长仓拥挤度。",
        "确认": ["长端利率下行", "股息率仍有吸引力", "成长波动升高", "现金流稳定"],
        "否定": ["红利过度拥挤", "利率上行", "只因短线避险追高"],
    },
    "shipping_routes": {
        "逻辑": "航运只在通道风险发生时抬高优先级，核心看运价、绕航、保险费和能源价格。",
        "确认": ["运价上行", "绕航时间增加", "保险费上升", "能源价格同步"],
        "否定": ["通道快速恢复", "运价不跟", "只有传闻没有航线数据"],
    },
    "new_energy_cycle": {
        "逻辑": "新能源看产能出清、价格链和利润修复，油价上涨不自动等于新能源上涨。",
        "确认": ["锂价/组件价格企稳", "库存下降", "龙头盈利修复", "订单改善"],
        "否定": ["产能继续过剩", "价格继续下跌", "政策保量不保利润"],
    },
    "sanctions_tariffs": {
        "逻辑": "制裁关税改变成本、供应链和议价权，必须看生效日期、豁免和替代供应。",
        "确认": ["官方文件确认", "报价变化", "汇率或商品价格响应", "替代供应不足"],
        "否定": ["只有口头威胁", "豁免范围很大", "价格没有响应"],
    },
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _fact_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_fact_values(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_fact_values(item))
        return result
    text = _text(value)
    return [text] if text else []


def _apply_fact_details(entry: dict[str, Any]) -> dict[str, Any]:
    row = dict(entry)
    entry_id = str(row.get("id") or row.get("name") or "")
    facts = dict(INDUSTRY_FACT_DETAILS.get(entry_id) or {})
    configured_facts = row.get("facts")
    if isinstance(configured_facts, dict):
        facts.update(configured_facts)
    if facts:
        row["facts"] = facts
        row.setdefault("fact_summary", _text(facts.get("逻辑")))
    return row


def _configured_entries(config: Any) -> tuple[bool, list[dict[str, Any]]]:
    if isinstance(config, dict):
        if config.get("enabled") is False:
            return True, []
        if isinstance(config.get("items"), list):
            return True, [dict(item) for item in config.get("items") or [] if isinstance(item, dict)]
        layers = config.get("layers")
        if isinstance(layers, dict):
            entries: list[dict[str, Any]] = []
            for layer, items in layers.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict):
                        row = dict(item)
                        row.setdefault("layer", layer)
                        entries.append(row)
            return True, entries
    if isinstance(config, list):
        return True, [dict(item) for item in config if isinstance(item, dict)]
    return False, []


def _cluster_text(cluster: Any) -> str:
    representative = getattr(cluster, "representative", None)
    parts = [
        getattr(cluster, "theme", ""),
        " ".join(getattr(cluster, "tags", []) or []),
        getattr(representative, "title", "") if representative else "",
        getattr(representative, "summary", "") if representative else "",
        getattr(representative, "content", "") if representative else "",
    ]
    for article in getattr(cluster, "articles", [])[:4]:
        parts.extend(
            [
                getattr(article, "title", ""),
                getattr(article, "summary", ""),
                getattr(article, "content", ""),
                getattr(article, "category", ""),
                getattr(article, "region", ""),
            ]
        )
    return " ".join(_text(part) for part in parts if _text(part)).casefold()


def _normalize_entries(config: Any) -> list[dict[str, Any]]:
    configured, custom_entries = _configured_entries(config)
    if configured and not custom_entries:
        return []

    entries = [_apply_fact_details(item) for item in DEFAULT_INDUSTRY_RADAR]
    index_by_key = {str(item.get("id") or item.get("name") or ""): idx for idx, item in enumerate(entries)}
    for custom in custom_entries:
        key = str(custom.get("id") or custom.get("name") or "")
        if key and key in index_by_key:
            merged = dict(entries[index_by_key[key]])
            merged.update(custom)
            entries[index_by_key[key]] = _apply_fact_details(merged)
        else:
            entries.append(_apply_fact_details(custom))
    return entries


def _keyword_hits(entry: dict[str, Any], cluster_texts: list[str]) -> list[str]:
    hits: list[str] = []
    for keyword in entry.get("keywords") or []:
        needle = str(keyword or "").casefold().strip()
        if not needle:
            continue
        if any(needle in text for text in cluster_texts):
            hits.append(str(keyword))
    return hits[:5]


def _theme_hit(entry: dict[str, Any], event_theme_keys: set[str], candidate_theme_keys: set[str]) -> bool:
    theme_keys = {str(item) for item in entry.get("theme_keys") or []}
    return bool(theme_keys & (event_theme_keys | candidate_theme_keys))


def _instrument_code_set(items: list[Any]) -> set[str]:
    codes: set[str] = set()
    for item in items or []:
        if isinstance(item, dict):
            code = str(item.get("code") or "").strip()
        else:
            code = str(item or "").strip()
        if code:
            codes.add(code)
    return codes


def _instrument_label(item: dict[str, Any]) -> str:
    name = str(item.get("name") or item.get("code") or "").strip()
    code = str(item.get("code") or "").strip()
    if name and code and name != code:
        return f"{name}({code})"
    return name or code


def _binding_refs(entry: dict[str, Any], portfolio: dict[str, Any], matched_candidates: list[dict[str, Any]]) -> tuple[list[str], list[str], str]:
    entry_codes = _instrument_code_set(entry.get("instruments") or [])
    candidate_links: list[str] = []
    candidate_codes: set[str] = set(entry_codes)
    for candidate in matched_candidates:
        for instrument in candidate.get("instruments") or []:
            if not isinstance(instrument, dict):
                continue
            code = str(instrument.get("code") or "").strip()
            label = _instrument_label(instrument)
            if code:
                candidate_codes.add(code)
            if label:
                candidate_links.append(label)

    holding_links: list[str] = []
    for holding in portfolio.get("holdings") or []:
        code = str(holding.get("code") or "").strip()
        if code and code in candidate_codes:
            holding_links.append(_instrument_label(holding))

    candidate_links = list(dict.fromkeys(candidate_links))[:4]
    holding_links = list(dict.fromkeys(holding_links))[:4]
    if holding_links and candidate_links:
        summary = "已持有：" + "、".join(holding_links) + "；候选：" + "、".join(candidate_links)
    elif holding_links:
        summary = "已持有：" + "、".join(holding_links)
    elif candidate_links:
        summary = "候选：" + "、".join(candidate_links)
    elif entry_codes:
        summary = "参考代码：" + "、".join(sorted(entry_codes)[:4])
    else:
        summary = "暂无直接绑定，先看行业确认"
    return holding_links, candidate_links, summary


def _component_score(text: str, keywords: tuple[str, ...]) -> int:
    lowered = text.casefold()
    hits = sum(1 for keyword in keywords if keyword in lowered)
    return min(5, hits * 2)


def _industry_score_card(
    entry: dict[str, Any],
    *,
    hits: list[str],
    matched_by_theme: bool,
    candidate_bonus: int,
    layer: str,
) -> dict[str, Any]:
    combined = " ".join(
        _text(value)
        for value in (
            entry.get("name"),
            entry.get("why"),
            entry.get("watch"),
            entry.get("verify"),
            entry.get("fact_summary"),
            " ".join(entry.get("keywords") or []),
            " ".join(hits),
            " ".join(_fact_values(entry.get("facts"))),
        )
    )
    policy_score = _component_score(
        combined,
        ("policy", "tariff", "sanction", "export", "regulation", "政策", "关税", "制裁", "出口", "管制", "反内卷"),
    )
    supply_score = _component_score(
        combined,
        ("supply", "shortage", "inventory", "capacity", "order", "供应", "库存", "产能", "订单", "交期", "卡脖子"),
    )
    price_score = min(5, int(candidate_bonus / 3) + (1 if matched_by_theme else 0))
    news_score = min(5, len(hits) * 2 + (2 if matched_by_theme else 0))
    hit_rate_score = 1 if layer != "avoid" else 0
    total = policy_score + supply_score + price_score + news_score + hit_rate_score
    if total >= 18:
        label = "强观察"
    elif total >= 12:
        label = "观察"
    elif layer == "avoid":
        label = "降噪"
    else:
        label = "积累"
    return {
        "policy": policy_score,
        "supply": supply_score,
        "price": price_score,
        "news": news_score,
        "hit_rate": hit_rate_score,
        "total": total,
        "label": label,
        "hit_rate_note": "等待事后验算样本",
    }


def _score_card_text(score_card: dict[str, Any] | None) -> str:
    card = score_card or {}
    return (
        f"{card.get('total', 0)}分/{card.get('label', '积累')}；"
        f"政{card.get('policy', 0)} 供{card.get('supply', 0)} "
        f"价{card.get('price', 0)} 闻{card.get('news', 0)} 命{card.get('hit_rate', 0)}"
    )


def _layer_of(entry: dict[str, Any]) -> str:
    layer = str(entry.get("layer") or "watch")
    return layer if layer in LAYER_LABELS else "watch"


def build_industry_radar(
    portfolio: dict[str, Any] | None,
    clusters: list[Any],
    event_impacts: list[dict[str, Any]],
    candidate_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    portfolio = portfolio or {}
    entries = _normalize_entries(portfolio.get("industry_radar"))
    if not entries:
        return {"enabled": False, "rows": [], "summary_lines": ["行业雷达未启用。"]}

    cluster_texts = [_cluster_text(cluster) for cluster in clusters]
    event_theme_keys = {str(key) for impact in event_impacts for key in impact.get("theme_keys", [])}
    candidate_theme_keys = {
        str(row.get("theme_key"))
        for row in candidate_scores
        if row.get("theme_key") and row.get("priority") in {"高", "中"}
    }
    candidate_by_key = {str(row.get("theme_key")): row for row in candidate_scores if row.get("theme_key")}

    rows: list[dict[str, Any]] = []
    for entry in entries:
        layer = _layer_of(entry)
        hits = _keyword_hits(entry, cluster_texts)
        matched_by_theme = _theme_hit(entry, event_theme_keys, candidate_theme_keys)
        matched_candidates = [
            candidate_by_key[key]
            for key in (entry.get("theme_keys") or [])
            if key in candidate_by_key
        ]
        holding_links, candidate_links, binding_summary = _binding_refs(entry, portfolio, matched_candidates)
        candidate_bonus = max((int(item.get("score") or 0) for item in matched_candidates), default=0)
        score = len(hits) * 2 + (3 if matched_by_theme else 0) + candidate_bonus
        if layer == "core":
            score += 3
        elif layer == "avoid":
            score -= 1

        score_card = _industry_score_card(
            entry,
            hits=hits,
            matched_by_theme=matched_by_theme,
            candidate_bonus=candidate_bonus,
            layer=layer,
        )

        if hits or matched_by_theme:
            status = "今日关注"
        elif layer == "core":
            status = "每日必看"
        elif layer == "secular":
            status = "长期必看"
        elif layer == "avoid":
            status = "降噪"
        else:
            status = "静默观察"

        rows.append(
            {
                "id": entry.get("id") or entry.get("name"),
                "name": entry.get("name") or "未命名行业",
                "layer": layer,
                "layer_label": LAYER_LABELS[layer],
                "status": status,
                "score": score,
                "score_card": score_card,
                "score_card_text": _score_card_text(score_card),
                "why": entry.get("why") or "",
                "horizon": entry.get("horizon") or "",
                "facts": entry.get("facts") or {},
                "fact_summary": entry.get("fact_summary") or "",
                "watch": entry.get("watch") or "",
                "verify": entry.get("verify") or "",
                "action": entry.get("action") or "",
                "instruments": list(entry.get("instruments") or []),
                "portfolio_links": holding_links,
                "candidate_links": candidate_links,
                "binding_summary": binding_summary,
                "hits": hits,
            }
        )

    rows.sort(key=lambda row: (LAYER_ORDER.get(row["layer"], 9), row["status"] != "今日关注", -int(row["score"])))
    layer_counts = {layer: sum(1 for row in rows if row.get("layer") == layer) for layer in LAYER_LABELS}
    active_rows = [row for row in rows if row.get("status") == "今日关注"]
    core_rows = [row for row in rows if row.get("layer") == "core"]
    secular_rows = [row for row in rows if row.get("layer") == "secular"]
    focus_pool = active_rows or (secular_rows + core_rows)
    focus_names = [row["name"] for row in focus_pool[:3]]
    summary_lines = [
        f"行业雷达共 {len(rows)} 条：持仓相关 {layer_counts.get('core', 0)}，长期主线 {layer_counts.get('secular', 0)}，重点观察 {layer_counts.get('watch', 0)}，事件触发 {layer_counts.get('event', 0)}，降噪 {layer_counts.get('avoid', 0)}。",
        "今天优先看：" + "、".join(focus_names) + "。" if focus_names else "今天没有行业雷达触发项。",
        "长期主线默认每日报警、每周决策；首次只允许小底仓，连续确认后才升级。",
        "可买池不随行业雷达自动扩张；雷达只决定看什么，不直接决定买什么。",
    ]
    return {
        "enabled": True,
        "summary_lines": summary_lines,
        "layer_counts": layer_counts,
        "active_count": len(active_rows),
        "rows": rows,
    }


def render_industry_radar_lines(radar: dict[str, Any]) -> list[str]:
    if not radar or not radar.get("enabled"):
        return ["- 行业雷达未启用。"]
    lines = list(radar.get("summary_lines") or [])
    rows = radar.get("rows") or []
    lines.extend(["", "| 层级 | 行业 | 周期 | 评分 | 状态 | 事实库 | 看什么 | 组合/候选绑定 | 验证条件 | 动作 |", "|---|---|---|---:|---|---|---|---|---|---|"])
    for row in rows:
        instruments = "、".join(row.get("instruments") or [])
        action = row.get("action") or ""
        if instruments:
            action = f"{action} 参考：{instruments}"
        lines.append(
            "| "
            f"{_text(row.get('layer_label'))} | "
            f"{_text(row.get('name'))} | "
            f"{_text(row.get('horizon'))} | "
            f"{_text(row.get('score_card_text'))} | "
            f"{_text(row.get('status'))} | "
            f"{_text(row.get('fact_summary'))} | "
            f"{_text(row.get('watch'))} | "
            f"{_text(row.get('binding_summary'))} | "
            f"{_text(row.get('verify'))} | "
            f"{_text(action)} |"
        )
    return lines
