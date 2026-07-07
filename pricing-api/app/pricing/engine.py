from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

from app.schemas import Category, CostItem, ProductSpec, QuoteMode, QuoteResult, RiskItem, TimelineItem


def rmb(value: float) -> float:
    return round(float(value), 2)


def contains(spec: ProductSpec, *keywords: str) -> bool:
    text = " ".join([spec.material or "", spec.packaging or "", spec.notes or "", *spec.process]).lower()
    return any(key.lower() in text for key in keywords)


def area_cm2(spec: ProductSpec, default: float = 25.0) -> float:
    if spec.length_mm and spec.width_mm:
        return max(spec.length_mm * spec.width_mm / 100.0, 1.0)
    return default


def volume_cm3(spec: ProductSpec, default: float = 100.0) -> float:
    if spec.length_mm and spec.width_mm and spec.height_mm:
        return max(spec.length_mm * spec.width_mm * spec.height_mm / 1000.0, 1.0)
    return default


def amortize(amount: float, quantity: int) -> float:
    return amount / max(quantity, 1)


def packaging_cost(spec: ProductSpec) -> float:
    if spec.packaging == "gift_box":
        return 4.8
    if spec.packaging == "custom":
        return 7.5
    return 1.2

def food_default_mold_fee(spec: ProductSpec, default_category: Category) -> float:
    mold_type = (spec.mold_type or "").lower()
    if spec.mold_fee is not None:
        return spec.mold_fee
    if mold_type in ["silicone", "硅胶"]:
        return 2200
    if mold_type in ["abs", "abs塑料", "plastic"]:
        return 6000
    if mold_type in ["metal", "金属"]:
        return 12000
    if mold_type in ["3d_print", "3d打印"]:
        return 1200
    if default_category == Category.chocolate:
        return 8000 if contains(spec, "双色", "异形", "嵌套", "logo", "Logo") else 4200
    return 9000 if contains(spec, "异形", "定制模具", "多色") else 6500


def food_mold_amortized_total(spec: ProductSpec, mold_fee: float) -> float:
    strategy = (spec.amortization_strategy or "order").lower()
    q = spec.quantity
    if strategy == "lifecycle" and spec.mold_life_units:
        return mold_fee / spec.mold_life_units * q
    if strategy == "hybrid":
        # 前5000件按本单摊销，超过部分视为后续复用，不再增加摊销。
        return mold_fee if q <= 5000 else mold_fee * 5000 / q
    return mold_fee


def food_packaging_unit(spec: ProductSpec) -> float:
    if any(v is not None for v in [spec.inner_packaging_cost, spec.single_packaging_cost, spec.outer_packaging_cost, spec.transport_packaging_cost]):
        return sum([
            spec.inner_packaging_cost or 0.0,
            spec.single_packaging_cost or 0.0,
            spec.outer_packaging_cost or 0.0,
            spec.transport_packaging_cost or 0.0,
        ])
    if spec.packaging == "gift_box":
        # 内包0.1 + 彩盒0.8 + 外盒2.0，来自食品模型示例。
        return 2.9
    if spec.packaging == "custom":
        return 3.8
    return 0.9


def food_process_unit(spec: ProductSpec, base_single: float = 0.5) -> float:
    process = (spec.color_process or "").lower()
    if not process:
        if contains(spec, "手绘"):
            process = "hand_painted"
        elif contains(spec, "多色", "嵌套"):
            process = "multi"
        elif contains(spec, "双色", "分层") or spec.colors == 2:
            process = "dual"
        else:
            process = "single"
    if process in ["single", "单色"]:
        unit = base_single
    elif process in ["dual", "双色"]:
        unit = base_single * 1.6
    elif process in ["multi", "多色"]:
        unit = base_single * (1 + max(spec.colors, 2) * 0.5)
    elif process in ["hand_painted", "手绘"]:
        unit = 2.0
    else:
        unit = base_single
    return unit * (spec.complexity_factor or (1.3 if contains(spec, "复杂", "浮雕", "嵌套", "异形") else 1.0))


def food_material_unit(spec: ProductSpec, default_price_per_kg: float, default_weight_g: float) -> tuple[float, float, float]:
    weight = spec.weight_g or default_weight_g
    price_per_kg = spec.raw_material_price_per_kg or default_price_per_kg
    main = price_per_kg * (weight / 1000.0)
    aux = spec.auxiliary_material_cost_per_unit or (0.5 if contains(spec, "坚果", "果粒", "夹心") else 0.0)
    loss = spec.loss_rate if spec.loss_rate is not None else (0.08 if contains(spec, "异形", "多色", "嵌套") else 0.05)
    return main, aux, loss


def food_common_cost_items(
    spec: ProductSpec,
    *,
    category: Category,
    default_price_per_kg: float,
    default_weight_g: float,
    base_process_fee: float,
    default_cold_chain: float,
    default_detection_fee: float,
) -> List[CostItem]:
    q = spec.quantity
    main_unit, aux_unit, loss_rate = food_material_unit(spec, default_price_per_kg, default_weight_g)
    material_unit_with_loss = (main_unit + aux_unit) * (1 + loss_rate)
    mold_fee = food_default_mold_fee(spec, category)
    mold_total = food_mold_amortized_total(spec, mold_fee)
    process_unit = food_process_unit(spec, base_process_fee)
    package_unit = food_packaging_unit(spec)
    cold_unit = spec.cold_chain_cost_per_unit if spec.cold_chain_cost_per_unit is not None else default_cold_chain
    detection_fee = spec.detection_fee if spec.detection_fee is not None else default_detection_fee
    certification_fee = spec.certification_fee or 0.0
    setup_fee = spec.setup_fee or (1800 if contains(spec, "开机", "专版", "版费") else 0.0)

    subtotal_before_profit_tax = (
        material_unit_with_loss * q
        + mold_total
        + process_unit * q
        + package_unit * q
        + cold_unit * q
        + detection_fee
        + certification_fee
        + setup_fee
    )
    management_rate = spec.management_profit_rate if spec.management_profit_rate is not None else 0.15
    management_profit = subtotal_before_profit_tax * management_rate
    tax_rate = spec.tax_rate if spec.tax_rate is not None else 0.13
    tax = (subtotal_before_profit_tax + management_profit) * tax_rate

    return [
        CostItem(name="原材料成本", amount=rmb(material_unit_with_loss * q), note=f"主料{main_unit:.2f}元/件 + 辅料{aux_unit:.2f}元/件，损耗率{loss_rate:.0%}"),
        CostItem(name="模具摊销费", amount=rmb(mold_total), note=f"模具费{mold_fee:.0f}元，摊销策略：{spec.amortization_strategy or 'order'}"),
        CostItem(name="工艺费", amount=rmb(process_unit * q), note=f"成型/注浆/装饰约{process_unit:.2f}元/件"),
        CostItem(name="包装费", amount=rmb(package_unit * q), note=f"内包+单体包装+外包装+运输包装约{package_unit:.2f}元/件"),
        CostItem(name="冷链/特殊存储费", amount=rmb(cold_unit * q), note=f"约{cold_unit:.2f}元/件"),
        CostItem(name="认证检测费", amount=rmb(detection_fee + certification_fee), note="批次检测/特殊认证按本单分摊"),
        CostItem(name="版费/开机费", amount=rmb(setup_fee), note="专版或小批量开机固定费用"),
        CostItem(name="管理利润", amount=rmb(management_profit), note=f"按以上成本 {management_rate:.0%} 计"),
        CostItem(name="税费", amount=rmb(tax), note=f"按成本+管理利润 {tax_rate:.0%} 计"),
    ]


def confidence(spec: ProductSpec) -> Tuple[str, str]:
    if spec.mode == QuoteMode.rough:
        return "概念粗估", "±25%-35%"
    if spec.mode == QuoteMode.sample:
        return "打样校准", "±8%-15%"
    missing = 0
    for attr in [spec.material, spec.length_mm, spec.width_mm, spec.weight_g]:
        if not attr:
            missing += 1
    if missing >= 2:
        return "结构化估算：参数不足", "±18%-28%"
    return "结构化估算", "±12%-18%"


def tier_prices(unit_cost: float, category: Category) -> Dict[str, float]:
    margin = {
        Category.icecream: 1.45,
        Category.chocolate: 1.55,
        Category.fridge_magnet: 1.75,
        Category.plush: 1.65,
        Category.stationery: 1.6,
        Category.packaging: 1.35,
    }[category]
    return {
        "500": rmb(unit_cost * margin * 1.18),
        "1000": rmb(unit_cost * margin * 1.0),
        "3000": rmb(unit_cost * margin * 0.88),
        "10000": rmb(unit_cost * margin * 0.76),
    }


def quote_icecream(spec: ProductSpec) -> Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]:
    q = spec.quantity
    items = food_common_cost_items(
        spec,
        category=Category.icecream,
        default_price_per_kg=42.0,
        default_weight_g=70.0,
        base_process_fee=0.55,
        default_cold_chain=spec.cold_chain_cost_per_unit if spec.cold_chain_cost_per_unit is not None else 1.1,
        default_detection_fee=spec.detection_fee if spec.detection_fee is not None else 1200.0,
    )
    timeline = [
        TimelineItem(step="配方/造型确认", days_min=3, days_max=6, risk="口味、结构和文化造型需同时确认"),
        TimelineItem(step="模具制作", days_min=7, days_max=15, risk="异形或多色结构可能返修"),
        TimelineItem(step="试产与口味确认", days_min=3, days_max=7, risk="需确认脱模、口感和稳定性"),
        TimelineItem(step="量产包装", days_min=4, days_max=max(6, math.ceil(q / 1500)), risk="数量越大，包装排产越关键"),
        TimelineItem(step="冷链发运", days_min=1, days_max=3, risk="-18℃冷链和终端冷柜需提前确认"),
    ]
    risks = [
        RiskItem(level="medium", message="雪糕对温控、配送半径和终端陈列条件敏感。", suggestion="报价前确认冷链、仓储和售卖周期。"),
    ]
    if contains(spec, "夏季", "户外", "高温"):
        risks.append(RiskItem(level="high", message="夏季/户外销售融化风险高，冷链费用可能超过预估。", suggestion="增加保温包装预算或调整上市时间。"))
    if contains(spec, "多色", "异形", "嵌套") or spec.colors >= 3:
        risks.append(RiskItem(level="medium", message="多色/异形雪糕会提高脱模损耗和工艺费。", suggestion="首版造型避免过细尖角，先做小批试产。"))
    assumptions = [
        "按食品类公式：原材料+模具摊销+包装+工艺+冷链/存储+认证检测+管理利润+税费。",
        "默认具备食品生产资质供应商承接，未包含终端冷柜采购费用。",
        "若需有机/清真等特殊认证，请填写 certification_fee。",
    ]
    return items, 3000, timeline, risks, assumptions


def quote_chocolate(spec: ProductSpec) -> Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]:
    q = spec.quantity
    items = food_common_cost_items(
        spec,
        category=Category.chocolate,
        default_price_per_kg=80.0 if contains(spec, "高端", "可可脂") else 58.0,
        default_weight_g=50.0,
        base_process_fee=0.5,
        default_cold_chain=spec.cold_chain_cost_per_unit if spec.cold_chain_cost_per_unit is not None else (0.8 if contains(spec, "夏季", "高温") else 0.2),
        default_detection_fee=spec.detection_fee if spec.detection_fee is not None else 1000.0,
    )
    timeline = [
        TimelineItem(step="设计与结构确认", days_min=2, days_max=5, risk="浮雕/嵌套结构需确认脱模可行性"),
        TimelineItem(step="模具制作", days_min=6, days_max=12, risk="双色或复杂Logo模具可能返修"),
        TimelineItem(step="调温试产/打样", days_min=3, days_max=6, risk="需确认光泽、口感和成型稳定性"),
        TimelineItem(step="量产包装", days_min=3, days_max=max(5, math.ceil(q / 2000)), risk="礼盒包装会拉长后道周期"),
    ]
    risks = [
        RiskItem(level="medium", message="复杂浮雕、Logo和吉祥物嵌套会提高脱模损耗。", suggestion="首版线条不要过细，减少尖角和深凹结构。"),
    ]
    if contains(spec, "夏季", "高温"):
        risks.append(RiskItem(level="high", message="巧克力夏季运输易融化，冷链或保温包装成本必须单列。", suggestion="填写 cold_chain_cost_per_unit，或改为秋冬上市。"))
    if contains(spec, "双色", "多色", "嵌套") or spec.colors >= 2:
        risks.append(RiskItem(level="medium", message="双色/多色需要多次注模和冷却，工艺费通常提高40%-200%。", suggestion="评估是否可通过包装视觉降低本体多色复杂度。"))
    assumptions = [
        "按食品类公式：原材料+模具摊销+包装+工艺+冷链/存储+认证检测+管理利润+税费。",
        "默认普通食品批次检测，未包含特殊进口原料溢价。",
        "包装默认按内包+彩盒+外盒+运输包装分层计算；可用字段覆盖。",
    ]
    return items, 1000, timeline, risks, assumptions

def nonstandard_default_mold_fee(spec: ProductSpec, category: Category) -> float:
    material = (spec.material or "").lower()
    if spec.mold_fee is not None:
        base = spec.mold_fee
    elif "锌" in material or "metal" in material:
        base = 12000
    elif "pvc" in material:
        base = 3500
    elif "亚克力" in material:
        base = 2500
    elif "abs" in material:
        base = 6500
    elif "毛绒" in material or category == Category.plush:
        base = 3800
    else:
        base = 2200
    return base * (spec.mold_complexity_factor or 1.0)


def nonstandard_packaging_unit(spec: ProductSpec) -> float:
    if any(v is not None for v in [spec.opp_bag_cost, spec.blister_card_cost, spec.instruction_card_cost]):
        return (spec.opp_bag_cost or 0.0) + (spec.blister_card_cost or 0.0) + (spec.instruction_card_cost or 0.0)
    if spec.packaging == "gift_box":
        return 2.5
    if spec.packaging == "custom":
        return 1.8
    if contains(spec, "吸塑", "挂卡"):
        return 0.48
    return 0.15


def quote_fridge_magnet(spec: ProductSpec) -> Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]:
    q = spec.quantity
    material = (spec.material or "锌合金").lower()
    area = area_cm2(spec, 20)

    mold_total = nonstandard_default_mold_fee(spec, Category.fridge_magnet)

    if spec.material_weight_kg is not None and spec.material_price_per_kg is not None:
        main_material_unit = spec.material_weight_kg * spec.material_price_per_kg
    else:
        if "锌" in material or "metal" in material:
            main_material_unit = 0.03 * (spec.material_price_per_kg or 35)
        elif "亚克力" in material:
            main_material_unit = 0.018 * (spec.material_price_per_kg or 45)
        elif "abs" in material:
            main_material_unit = 0.02 * (spec.material_price_per_kg or 28)
        else:
            main_material_unit = 0.018 * (spec.material_price_per_kg or 25)
    magnet_unit = spec.magnet_cost_per_unit if spec.magnet_cost_per_unit is not None else 0.15
    material_unit = main_material_unit + magnet_unit

    processing_setup = spec.processing_setup_fee if spec.processing_setup_fee is not None else (800 if ("锌" in material or "metal" in material) else 300)
    processing_unit = spec.processing_unit_fee if spec.processing_unit_fee is not None else (0.15 if ("锌" in material or "metal" in material) else 0.10)
    plating_unit = spec.plating_unit_fee if spec.plating_unit_fee is not None else (1.30 if contains(spec, "电镀", "古铜", "金色", "双色") else 0.35)
    uv_setup = spec.uv_setup_fee if spec.uv_setup_fee is not None else (300 if contains(spec, "UV", "uv", "印刷") else 0)
    uv_unit = spec.uv_unit_fee if spec.uv_unit_fee is not None else (0.20 if contains(spec, "UV", "uv", "印刷") else 0.0)
    assembly_unit = spec.assembly_unit_fee if spec.assembly_unit_fee is not None else (0.10 if contains(spec, "磁铁", "粘贴") or spec.category == Category.fridge_magnet else 0.25)
    packaging_unit = nonstandard_packaging_unit(spec)

    subtotal = (
        mold_total
        + material_unit * q
        + processing_setup + processing_unit * q
        + plating_unit * q
        + uv_setup + uv_unit * q
        + assembly_unit * q
        + packaging_unit * q
    )
    management_rate = spec.management_profit_rate if spec.management_profit_rate is not None else 0.25
    management_profit = subtotal * management_rate
    tax_rate = spec.tax_rate if spec.tax_rate is not None else 0.13
    tax = (subtotal + management_profit) * tax_rate

    items = [
        CostItem(name="模具费", amount=rmb(mold_total), note=f"按材质和复杂度计算，复杂度系数{spec.mold_complexity_factor or 1.0:g}"),
        CostItem(name="原材料", amount=rmb(material_unit * q), note=f"主体材料{main_material_unit:.2f}元/件 + 磁铁/配件{magnet_unit:.2f}元/件"),
        CostItem(name="注塑/压铸工艺", amount=rmb(processing_setup + processing_unit * q), note=f"固定费{processing_setup:.0f}元 + {processing_unit:.2f}元/件"),
        CostItem(name="表面处理费", amount=rmb(plating_unit * q), note=f"电镀/喷油/表面处理约{plating_unit:.2f}元/件"),
        CostItem(name="UV/印刷", amount=rmb(uv_setup + uv_unit * q), note=f"起版{uv_setup:.0f}元 + {uv_unit:.2f}元/件"),
        CostItem(name="组装费", amount=rmb(assembly_unit * q), note=f"约{assembly_unit:.2f}元/件"),
        CostItem(name="包装费", amount=rmb(packaging_unit * q), note=f"OPP/吸塑卡/说明卡约{packaging_unit:.2f}元/件"),
        CostItem(name="管理利润", amount=rmb(management_profit), note=f"按小计成本 {management_rate:.0%} 计"),
        CostItem(name="增值税", amount=rmb(tax), note=f"按成本+利润 {tax_rate:.0%} 计"),
    ]

    timeline = [
        TimelineItem(step="工程图/拆件", days_min=2, days_max=4, risk="复杂立体结构需确认拔模角"),
        TimelineItem(step="开模", days_min=7 if "锌" not in material else 15, days_max=14 if "锌" not in material else 25, risk="锌合金/复杂结构开模周期较长"),
        TimelineItem(step="打样确认", days_min=3, days_max=7, risk="电镀和UV颜色需实物确认"),
        TimelineItem(step="量产加工", days_min=5, days_max=max(8, math.ceil(q / 2500)), risk="多工艺叠加会拉长排产"),
        TimelineItem(step="组装包装", days_min=2, days_max=5),
    ]
    risks = []
    if spec.mold_complexity_factor and spec.mold_complexity_factor >= 2:
        risks.append(RiskItem(level="high", message="模具复杂度较高，开模费和返修概率会上升。", suggestion="先做3D结构评审或软模打样。"))
    if contains(spec, "电镀") and contains(spec, "UV", "uv"):
        risks.append(RiskItem(level="medium", message="电镀叠加UV印刷存在附着力和套准风险。", suggestion="大货前必须确认表面处理样。"))
    if spec.colors > 6:
        risks.append(RiskItem(level="medium", message="颜色较多会提高印刷或上色成本。", suggestion="合并相近色或改为局部重点上色。"))
    assumptions = [
        "按非标文创公式：模具费+原材料+工艺加工+组装+包装+表面处理+管理利润+税费。",
        "冰箱贴默认包含磁铁/配件成本；如有特殊磁铁请填写 magnet_cost_per_unit。",
        "当前为供应商询价前估算，最终价格需用实际工厂报价校准。",
    ]
    return items, 500, timeline, risks, assumptions

def quote_plush(spec: ProductSpec) -> Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]:
    q = spec.quantity
    height = spec.height_mm or spec.length_mm or 180
    size_factor = max(height / 180, 0.65)

    mold_total = nonstandard_default_mold_fee(spec, Category.plush)
    fabric_unit = (
        (spec.material_price_per_meter or 18) * (spec.fabric_usage_meter_per_unit or (0.18 * size_factor))
    )
    filling_unit = (
        (spec.filling_price_per_kg or 12) * (spec.filling_weight_kg or (0.08 * size_factor))
    )
    embroidery_unit = spec.uv_unit_fee if spec.uv_unit_fee is not None else (1.6 + max(spec.colors - 4, 0) * 0.35 if contains(spec, "刺绣") else 0.8)
    sewing_unit = spec.assembly_unit_fee if spec.assembly_unit_fee is not None else (1.8 * size_factor if contains(spec, "挂件") else 2.5 * size_factor)
    packaging_unit = nonstandard_packaging_unit(spec)
    testing_fee = spec.detection_fee if spec.detection_fee is not None else (3500 if contains(spec, "儿童", "安规", "出口") else 800)

    subtotal = mold_total + (fabric_unit + filling_unit + embroidery_unit + sewing_unit + packaging_unit) * q + testing_fee
    management_rate = spec.management_profit_rate if spec.management_profit_rate is not None else 0.25
    management_profit = subtotal * management_rate
    tax_rate = spec.tax_rate if spec.tax_rate is not None else 0.13
    tax = (subtotal + management_profit) * tax_rate

    items = [
        CostItem(name="打版/面料模", amount=rmb(mold_total), note=f"按毛绒面料模/打版费估算，复杂度系数{spec.mold_complexity_factor or 1.0:g}"),
        CostItem(name="短毛绒/面料", amount=rmb(fabric_unit * q), note=f"约{fabric_unit:.2f}元/件"),
        CostItem(name="PP棉/填充物", amount=rmb(filling_unit * q), note=f"约{filling_unit:.2f}元/件"),
        CostItem(name="刺绣/印花", amount=rmb(embroidery_unit * q), note=f"约{embroidery_unit:.2f}元/件"),
        CostItem(name="组装/手工缝制", amount=rmb(sewing_unit * q), note=f"约{sewing_unit:.2f}元/件"),
        CostItem(name="包装费", amount=rmb(packaging_unit * q), note=f"约{packaging_unit:.2f}元/件"),
        CostItem(name="检测费", amount=rmb(testing_fee), note="安规/质检预留"),
        CostItem(name="管理利润", amount=rmb(management_profit), note=f"按小计成本 {management_rate:.0%} 计"),
        CostItem(name="增值税", amount=rmb(tax), note=f"按成本+利润 {tax_rate:.0%} 计"),
    ]
    timeline = [
        TimelineItem(step="角色结构拆解/打版", days_min=5, days_max=15, risk="毛绒还原度依赖版型"),
        TimelineItem(step="首样制作", days_min=5, days_max=9, risk="通常需2-3轮改样"),
        TimelineItem(step="面辅料采购", days_min=4, days_max=10),
        TimelineItem(step="量产缝制", days_min=7, days_max=max(12, math.ceil(q / 800)), risk="手工缝制产能波动较大"),
        TimelineItem(step="质检包装", days_min=2, days_max=4),
    ]
    risks = [RiskItem(level="medium", message="毛绒产品打样还原度依赖版型，首次开发不宜压缩周期。", suggestion="预留 2-3 轮改样时间。")]
    if contains(spec, "刺绣") and spec.colors > 6:
        risks.append(RiskItem(level="high", message="复杂刺绣可能导致表情变形。", suggestion="减少小面积多色细节。"))
    if height > 300:
        risks.append(RiskItem(level="medium", message="尺寸较大，物流体积和填充成本会上升。", suggestion="同步测算装箱数和运费。"))
    assumptions = [
        "按非标文创公式：模具/打版+原材料+工艺加工+组装+包装+管理利润+税费。",
        "面料和填充物按默认用量估算，可用 material_price_per_meter、fabric_usage_meter_per_unit、filling_weight_kg 校准。",
        "儿童玩具或出口订单需单独确认安规检测。",
    ]
    return items, 500, timeline, risks, assumptions

def quote_stationery(spec: ProductSpec) -> Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]:
    q = spec.quantity
    area = area_cm2(spec, 150)
    paper = 0.012 * area
    print_fee = 0.55 + max(spec.colors - 4, 0) * 0.18
    binding = 0.8 if contains(spec, "装订", "本子") else 0.25
    finishing = 0.75 if contains(spec, "烫金", "uv", "UV", "压纹") else 0.18
    plate = 900 if contains(spec, "专色", "烫金", "压纹") else 350
    items = [
        CostItem(name="纸张/主体", amount=rmb(paper * q), note=f"展开面积约 {area:.1f}cm²"),
        CostItem(name="印刷", amount=rmb(print_fee * q), note=f"{spec.colors} 色"),
        CostItem(name="装订/后道", amount=rmb((binding + finishing) * q)),
        CostItem(name="包装", amount=rmb(packaging_cost(spec) * q)),
        CostItem(name="制版/刀模", amount=rmb(plate)),
        CostItem(name="损耗预留", amount=rmb((paper + print_fee) * 0.05 * q), note="默认 5%"),
    ]
    timeline = [
        TimelineItem(step="版式/刀模确认", days_min=1, days_max=3),
        TimelineItem(step="打样", days_min=2, days_max=5),
        TimelineItem(step="印刷与后道", days_min=4, days_max=max(6, math.ceil(q / 5000))),
        TimelineItem(step="包装入库", days_min=1, days_max=3),
    ]
    risks = []
    if contains(spec, "烫金", "压纹"):
        risks.append(RiskItem(level="medium", message="烫金/压纹对细线条和套准要求高。", suggestion="线宽建议不低于 0.3mm。"))
    assumptions = ["默认常规纸张，不含特种纸大幅溢价", "未包含版权图片授权费用"]
    return items, 1000, timeline, risks, assumptions


def quote_packaging(spec: ProductSpec) -> Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]:
    q = spec.quantity
    vol = volume_cm3(spec, 800)
    paper = 0.006 * vol
    print_fee = 1.1 + max(spec.colors - 4, 0) * 0.25
    finishing = 1.2 if contains(spec, "烫金", "uv", "UV", "覆膜") else 0.45
    inner = 2.2 if contains(spec, "内托", "eva", "EVA", "吸塑") else 0.4
    die = 1800 if vol < 1500 else 3200
    assembly = 1.1 if contains(spec, "手工", "礼盒") else 0.45
    items = [
        CostItem(name="纸张/板材", amount=rmb(paper * q), note=f"体积约 {vol:.0f}cm³"),
        CostItem(name="印刷", amount=rmb(print_fee * q)),
        CostItem(name="表面工艺", amount=rmb(finishing * q)),
        CostItem(name="内托/辅料", amount=rmb(inner * q)),
        CostItem(name="组装人工", amount=rmb(assembly * q)),
        CostItem(name="刀模/制版", amount=rmb(die)),
        CostItem(name="损耗预留", amount=rmb((paper + print_fee + finishing) * 0.06 * q), note="默认 6%"),
    ]
    timeline = [
        TimelineItem(step="结构设计/刀模", days_min=2, days_max=5),
        TimelineItem(step="打样", days_min=3, days_max=6),
        TimelineItem(step="印刷后道", days_min=5, days_max=max(7, math.ceil(q / 4000))),
        TimelineItem(step="组装发货", days_min=2, days_max=5),
    ]
    risks = [RiskItem(level="medium", message="包装尺寸会显著影响物流体积。", suggestion="打样前同步确认装箱数和运输方式。")]
    if contains(spec, "烫金") and spec.colors > 4:
        risks.append(RiskItem(level="medium", message="多色印刷叠加烫金会增加套准风险。", suggestion="关键图案避免跨折线。"))
    assumptions = ["默认国内常规包装纸材", "未包含大货仓储费用"]
    return items, 500, timeline, risks, assumptions


QUOTE_FUNCS: Dict[Category, Callable[[ProductSpec], Tuple[List[CostItem], int, List[TimelineItem], List[RiskItem], List[str]]]] = {
    Category.icecream: quote_icecream,
    Category.chocolate: quote_chocolate,
    Category.fridge_magnet: quote_fridge_magnet,
    Category.plush: quote_plush,
    Category.stationery: quote_stationery,
    Category.packaging: quote_packaging,
}


def quote_product(spec: ProductSpec) -> QuoteResult:
    items, moq, timeline, risks, assumptions = QUOTE_FUNCS[spec.category](spec)
    q = spec.quantity
    total_cost = sum(item.amount for item in items)
    unit_cost = total_cost / q
    tiers = tier_prices(unit_cost, spec.category)
    suggested = tiers["1000"] if q <= 1000 else rmb(unit_cost * 1.45)
    confidence_label, accuracy = confidence(spec)

    if spec.quantity < moq:
        risks.append(
            RiskItem(
                level="high",
                message=f"当前数量低于建议起订量 {moq}，单价会明显偏高。",
                suggestion="建议提高数量或选择现货/通用模具方案。",
            )
        )
    if spec.target_unit_price and unit_cost > spec.target_unit_price:
        risks.append(
            RiskItem(
                level="high",
                message="测算成本高于目标单价。",
                suggestion="减少工艺、提高数量或调整材质。",
            )
        )

    next_steps = [
        "补齐尺寸、材质、包装和数量，进入结构化报价。",
        "选择 2-3 家供应商询价，校准模具费和单件加工费。",
        "先做白样/色样确认，再冻结大货工艺。",
    ]
    if spec.category in [Category.icecream, Category.chocolate]:
        next_steps.append("确认食品生产资质、保质期、标签合规和物流温控方案。")

    return QuoteResult(
        category=spec.category,
        quantity=q,
        quote_mode=spec.mode,
        unit_cost=rmb(unit_cost),
        suggested_unit_price=suggested,
        total_cost=rmb(total_cost),
        gross_margin_reference="建议零售价通常按成本 x1.5-x2.5 评估，需结合渠道扣点调整。",
        moq=moq,
        confidence=confidence_label,
        accuracy_range=accuracy,
        breakdown=items,
        timeline=timeline,
        risks=risks,
        tier_prices=tiers,
        assumptions=assumptions,
        next_steps=next_steps,
    )
