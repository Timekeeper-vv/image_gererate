from __future__ import annotations

from typing import Dict, List

from app.schemas import Category, CategoryInfo

CATEGORY_INFOS: List[CategoryInfo] = [
    CategoryInfo(
        code=Category.icecream,
        name="雪糕/冰品文创",
        required_fields=["quantity", "weight_g", "process", "packaging"],
        common_processes=["定制模具", "多色灌注", "冷链", "独立包装", "食品检测"],
        note="重点关注原料、克重、模具、冷链、损耗和保质期。",
    ),
    CategoryInfo(
        code=Category.chocolate,
        name="巧克力文创",
        required_fields=["quantity", "weight_g", "process", "packaging"],
        common_processes=["硅胶模具", "双色巧克力", "夹心", "礼盒", "食品检测"],
        note="重点关注可可脂含量、克重、模具摊销、包装和夏季温控。",
    ),
    CategoryInfo(
        code=Category.fridge_magnet,
        name="冰箱贴/徽章/钥匙扣",
        required_fields=["quantity", "material", "length_mm", "width_mm", "process"],
        common_processes=["锌合金压铸", "软胶", "亚克力", "滴胶", "UV", "电镀"],
        note="重点关注开模费、材质、上色、表面处理和数量阶梯。",
    ),
    CategoryInfo(
        code=Category.plush,
        name="毛绒玩具/抱枕/挂件",
        required_fields=["quantity", "length_mm", "height_mm", "process"],
        common_processes=["打版", "刺绣", "热转印", "吊牌", "安规检测"],
        note="重点关注面料、填充、尺寸、刺绣面积、缝制复杂度和体积物流。",
    ),
    CategoryInfo(
        code=Category.stationery,
        name="文具/纸品周边",
        required_fields=["quantity", "material", "colors", "process"],
        common_processes=["四色印刷", "专色", "烫金", "UV", "压纹", "装订"],
        note="重点关注纸张、页数、印刷色数、后道工艺和起订量。",
    ),
    CategoryInfo(
        code=Category.packaging,
        name="礼盒/手提袋/包装物料",
        required_fields=["quantity", "material", "length_mm", "width_mm", "height_mm", "process"],
        common_processes=["刀模", "覆膜", "烫金", "UV", "内托", "手工组装"],
        note="重点关注尺寸、纸张、印刷、表面工艺、内托和装箱体积。",
    ),
]


def category_map() -> Dict[str, CategoryInfo]:
    return {item.code.value: item for item in CATEGORY_INFOS}
