from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Category(str, Enum):
    icecream = "icecream"
    chocolate = "chocolate"
    fridge_magnet = "fridge_magnet"
    plush = "plush"
    stationery = "stationery"
    packaging = "packaging"


class QuoteMode(str, Enum):
    rough = "rough"          # 概念阶段，参数少，误差大
    structured = "structured" # 方案阶段，参数较完整
    sample = "sample"        # 打样阶段，接近供应商询价


class ProductSpec(BaseModel):
    category: Category = Field(..., description="报价品类")
    quantity: int = Field(..., gt=0, description="数量")
    mode: QuoteMode = Field(default=QuoteMode.structured, description="报价阶段")
    material: Optional[str] = Field(default=None, description="主要材质/原料")
    length_mm: Optional[float] = Field(default=None, gt=0, description="长度 mm")
    width_mm: Optional[float] = Field(default=None, gt=0, description="宽度 mm")
    height_mm: Optional[float] = Field(default=None, gt=0, description="高度/厚度 mm")
    weight_g: Optional[float] = Field(default=None, gt=0, description="单件克重 g")
    colors: int = Field(default=4, ge=1, le=12, description="颜色/印刷色数")
    process: List[str] = Field(default_factory=list, description="工艺，如 UV、烫金、刺绣、滴胶、冷链")
    packaging: str = Field(default="standard", description="包装：standard/gift_box/custom")
    target_unit_price: Optional[float] = Field(default=None, gt=0, description="目标单价")

    # 食品类精算字段：巧克力/雪糕优先使用这些字段；不填则走系统默认参考值。
    raw_material_price_per_kg: Optional[float] = Field(default=None, gt=0, description="主料单价，元/kg，如可可脂80")
    auxiliary_material_cost_per_unit: Optional[float] = Field(default=None, ge=0, description="辅料单件成本，如坚果/果粒/色素")
    loss_rate: Optional[float] = Field(default=None, ge=0, le=0.5, description="损耗率，如0.05")
    mold_type: Optional[str] = Field(default=None, description="模具类型：silicone/abs/metal/3d_print/custom")
    mold_fee: Optional[float] = Field(default=None, ge=0, description="模具总费用")
    mold_life_units: Optional[int] = Field(default=None, gt=0, description="模具预期寿命产量")
    amortization_strategy: Optional[str] = Field(default="order", description="模具摊销策略：order/lifecycle/hybrid")
    color_process: Optional[str] = Field(default=None, description="食品成型工艺：single/dual/multi/hand_painted")
    complexity_factor: Optional[float] = Field(default=None, gt=0, description="复杂系数，如1.3")
    inner_packaging_cost: Optional[float] = Field(default=None, ge=0, description="内包装单件成本")
    single_packaging_cost: Optional[float] = Field(default=None, ge=0, description="单体包装单件成本")
    outer_packaging_cost: Optional[float] = Field(default=None, ge=0, description="外盒彩盒/铁盒单件成本")
    transport_packaging_cost: Optional[float] = Field(default=None, ge=0, description="运输包装单件分摊")
    cold_chain_cost_per_unit: Optional[float] = Field(default=None, ge=0, description="冷链/特殊存储单件成本")
    certification_fee: Optional[float] = Field(default=None, ge=0, description="特殊认证费用")
    detection_fee: Optional[float] = Field(default=None, ge=0, description="批次检测费用")
    setup_fee: Optional[float] = Field(default=None, ge=0, description="版费/开机费")
    management_profit_rate: Optional[float] = Field(default=None, ge=0, le=1, description="管理利润率，如0.15")
    tax_rate: Optional[float] = Field(default=None, ge=0, le=0.3, description="税率，如0.13")

    # 非标文创精算字段：冰箱贴、徽章、毛绒等品类可用。
    material_price_per_kg: Optional[float] = Field(default=None, gt=0, description="材料单价，元/kg，如锌合金35")
    material_weight_kg: Optional[float] = Field(default=None, gt=0, description="单件材料重量，kg，如0.03")
    material_price_per_meter: Optional[float] = Field(default=None, gt=0, description="面料单价，元/米，毛绒类可用")
    fabric_usage_meter_per_unit: Optional[float] = Field(default=None, gt=0, description="单件面料用量，米/件")
    filling_price_per_kg: Optional[float] = Field(default=None, gt=0, description="填充物单价，元/kg")
    filling_weight_kg: Optional[float] = Field(default=None, gt=0, description="单件填充重量，kg")
    magnet_cost_per_unit: Optional[float] = Field(default=None, ge=0, description="磁铁/配件单件成本")
    mold_complexity_factor: Optional[float] = Field(default=None, gt=0, description="模具复杂度系数，如1.3/2.0")
    processing_setup_fee: Optional[float] = Field(default=None, ge=0, description="上机费/起版费/固定加工费")
    processing_unit_fee: Optional[float] = Field(default=None, ge=0, description="基础加工单件费，如压铸0.15")
    plating_unit_fee: Optional[float] = Field(default=None, ge=0, description="电镀/表面处理单件费")
    uv_setup_fee: Optional[float] = Field(default=None, ge=0, description="UV/印刷起版费")
    uv_unit_fee: Optional[float] = Field(default=None, ge=0, description="UV/印刷单件费")
    assembly_unit_fee: Optional[float] = Field(default=None, ge=0, description="组装单件费")
    opp_bag_cost: Optional[float] = Field(default=None, ge=0, description="OPP袋单件成本")
    blister_card_cost: Optional[float] = Field(default=None, ge=0, description="吸塑卡/挂卡单件成本")
    instruction_card_cost: Optional[float] = Field(default=None, ge=0, description="说明书/文化卡片单件成本")

    notes: Optional[str] = Field(default=None, description="补充说明")

    @model_validator(mode="after")
    def normalize_process(self) -> "ProductSpec":
        self.process = [str(item).strip() for item in self.process if str(item).strip()]
        return self


class CostItem(BaseModel):
    name: str
    amount: float
    note: str = ""


class TimelineItem(BaseModel):
    step: str
    days_min: int
    days_max: int
    risk: str = ""


class RiskItem(BaseModel):
    level: str = Field(description="low/medium/high")
    message: str
    suggestion: str = ""


class QuoteResult(BaseModel):
    category: Category
    quantity: int
    quote_mode: QuoteMode
    currency: str = "CNY"
    unit_cost: float
    suggested_unit_price: float
    total_cost: float
    gross_margin_reference: str
    moq: int
    confidence: str
    accuracy_range: str
    breakdown: List[CostItem]
    timeline: List[TimelineItem]
    risks: List[RiskItem]
    tier_prices: Dict[str, float]
    assumptions: List[str]
    next_steps: List[str]


class CategoryInfo(BaseModel):
    code: Category
    name: str
    required_fields: List[str]
    common_processes: List[str]
    note: str


class LeadQuoteRequest(BaseModel):
    product_name: str = "未命名产品"
    spec: ProductSpec
    customer: Optional[Dict[str, Any]] = None
